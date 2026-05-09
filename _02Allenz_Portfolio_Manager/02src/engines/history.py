"""
@Title: Time Machine Engine (Historical Holdings & Valuation)
@Description: 과거 모든 날짜의 종목별 평가금액과 '현금(Cash)'을 역산하여 완벽한 포트폴리오 스냅샷(Wide Format)을 복원하고, 신규 종목의 ISIN 매핑을 자동화합니다.
@Author: Allen & Gemini
@Date: 2026-03-26
"""

# 1. Imports
import sys
import json
import pandas as pd
import yfinance as yf
from pathlib import Path

# 상위 디렉토리(02src) 참조 설정
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config
try:
    from data_loaders import io as local_io
    from data_loaders.trade_log import build_unified_trade_log
except ImportError:
    import io as local_io
    from trade_log import build_unified_trade_log

# 2. Constants
MODULE_TAG = "[TimeMachine]"

# 3. Helper Functions
def _fetch_price_series(ticker: str, start_date: str, end_date: str) -> pd.Series:
    """
    특정 티커의 과거 수정 종가를 가져옵니다.

    Args:
        ticker (str): 조회할 종목 티커
        start_date (str): 조회 시작일 (YYYY-MM-DD)
        end_date (str): 조회 종료일 (YYYY-MM-DD)

    Returns:
        pd.Series: 날짜를 인덱스로 하는 종가 시리즈
    """
    try:
        stock = yf.Ticker(ticker)
        end_dt = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        hist = stock.history(start=start_date, end=end_dt)
        if hist.empty or 'Close' not in hist.columns:
            return pd.Series(dtype='float64')
        return hist['Close']
    except Exception as e:
        print(f"⚠️ {MODULE_TAG} {ticker} 가격 수집 에러: {e}")
        return pd.Series(dtype='float64')


def _update_isin_mapping(isin_list: set) -> dict:
    """
    누락된 ISIN을 찾아 yfinance로 검색 후 json 파일을 자동 업데이트합니다.
    한국 HTS 코드(예: A494670)를 자동으로 감지하여 KOSPI(.KS) 또는 KOSDAQ(.KQ) 티커로 변환합니다.

    Args:
        isin_list (set): 검사할 ISIN 코드들의 집합

    Returns:
        dict: 최신화된 ISIN -> Ticker 매핑 사전
    """
    json_path = config.ISIN_MAPPING_FILE

    # 1. 기존 매핑 파일 읽기
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    else:
        mapping = {}

    updated = False

    # 2. 누락된 ISIN 찾아서 Ticker 검색 및 변환
    for isin in isin_list:
        if pd.notna(isin) and str(isin).strip():
            clean_isin = str(isin).strip()

            if clean_isin not in mapping:
                print(f"🔍 {MODULE_TAG} 신규 코드 발견 [{clean_isin}] -> 변환 및 검색 중...")

                # [Rule 1] 한국 국내 주식/ETF 처리 (A + 숫자 6자리)
                if clean_isin.startswith('A') and len(clean_isin) == 7 and clean_isin[1:].isdigit():
                    kor_code = clean_isin[1:]
                    found_kor_ticker = None

                    # KOSPI(.KS)와 KOSDAQ(.KQ) 순차적 찌르기 테스트
                    for suffix in ['.KS', '.KQ']:
                        test_ticker = f"{kor_code}{suffix}"
                        try:
                            # 1일 치 데이터를 받아와서 실제로 존재하는 티커인지 검증
                            hist = yf.Ticker(test_ticker).history(period="1d")
                            if not hist.empty and 'Close' in hist.columns:
                                found_kor_ticker = test_ticker
                                break
                        except Exception:
                            continue

                    if found_kor_ticker:
                        mapping[clean_isin] = found_kor_ticker
                        updated = True
                        print(f"✅ {MODULE_TAG} 🇰🇷 한국 종목 매핑 완료: {clean_isin} -> {found_kor_ticker}")
                        continue  # 찾았으므로 다음 ISIN으로 넘어감

                # [Rule 2] 해외 주식 (일반 ISIN) 검색 로직
                try:
                    search = yf.Search(clean_isin, max_results=1)
                    if search.quotes:
                        ticker = search.quotes[0]['symbol']
                        mapping[clean_isin] = ticker
                        updated = True
                        print(f"✅ {MODULE_TAG} 🌎 해외 종목 매핑 완료: {clean_isin} -> {ticker}")
                    else:
                        print(f"⚠️ {MODULE_TAG} 검색 실패: {clean_isin} (수동 추가 필요)")
                except Exception as e:
                    print(f"❌ {MODULE_TAG} yfinance 검색 오류 ({clean_isin}): {e}")

    # 3. 변경사항이 있으면 json 파일 덮어쓰기
    if updated:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=4, ensure_ascii=False)
        print(f"💾 {MODULE_TAG} isin_mapping.json 파일이 성공적으로 업데이트되었습니다.")

    return mapping

# 4. Main Logic
def generate_timeline() -> None:
    """거래 내역과 현재 잔고를 기반으로 과거 포트폴리오 가치를 역산합니다."""
    print(f"🚀 {MODULE_TAG} 타임머신 데이터(Wide Format 역산 + 현금) 생성 시작...")

    # --- 1. 통합 거래 로그 (SSOT) 및 보유 종목 (Holdings) 로드 ---
    # 2610(해외주식) + 1750(한국 ETF) 통합 — 00Transaction_History 직접 파싱 제거
    trade_log = build_unified_trade_log()
    holdings_file = config.PROCESSED_DIR / "02Portfolio_Holdings.csv"

    if trade_log.empty:
        print(f"❌ {MODULE_TAG} 통합 거래 로그가 비어있습니다.")
        return

    df_holdings = pd.DataFrame()
    if holdings_file.exists():
        df_holdings = local_io.load_csv(holdings_file)

    # --- 2. 스마트 ISIN 자동 매핑 ---
    isins_from_trades = trade_log['isin'].dropna().astype(str).tolist()
    isins_from_holdings = (
        df_holdings['종목코드'].dropna().astype(str).tolist()
        if not df_holdings.empty and '종목코드' in df_holdings.columns
        else []
    )

    unique_isins = set(isins_from_trades + isins_from_holdings)
    latest_mapping = _update_isin_mapping(unique_isins)

    # 매핑 우선순위: latest_mapping(최신) > trade_log 내 ticker(2610 원본)
    trade_log['ticker'] = trade_log.apply(
        lambda r: latest_mapping.get(str(r['isin']), r['ticker']),
        axis=1
    )
    df_stocks = trade_log[trade_log['ticker'].str.strip() != ''].copy()

    if df_stocks.empty:
        print(f"⚠️ {MODULE_TAG} 매핑된 주식 거래 내역이 없습니다.")
        return

    # quantity는 SSOT에서 이미 signed(매도=음수). 별도 부호 변환 불필요.
    # ledger.py와 동일한 결제일 기준 정렬 (1750_kr NaT → trade date fallback).
    _df = df_stocks.copy()
    _df['effective_date'] = _df['settlement_date'].fillna(_df['date'])
    daily_change = _df.groupby(['effective_date', 'ticker'])['quantity'].sum().reset_index()
    daily_change = daily_change.rename(columns={'effective_date': 'date'})
    change_wide = daily_change.pivot(index='date', columns='ticker', values='quantity').fillna(0)

    # --- 3. 현재 잔고 (Current Holdings) 앵커링 ---
    current_holdings = {}
    if not df_holdings.empty and '종목코드' in df_holdings.columns:
        df_holdings['Ticker'] = df_holdings['종목코드'].astype(str).map(latest_mapping)
        for _, row in df_holdings.dropna(subset=['Ticker']).iterrows():
            current_holdings[row['Ticker']] = float(row.get('잔고수량', 0))

    # --- 4. 역산 (Reverse Engineering) 알고리즘 ---
    all_tickers = list(set(current_holdings.keys()) | set(df_stocks['ticker'].unique()))

    start_date = change_wide.index.min() if not change_wide.empty else (pd.Timestamp.today() - pd.Timedelta(days=30))
    today = pd.Timestamp.today().normalize()

    reversed_dates = pd.date_range(start=start_date, end=today, freq='D')[::-1]

    running_holdings = current_holdings.copy()
    history_qty = []

    for d in reversed_dates:
        row = {'Date': d}
        for t in all_tickers:
            row[t] = running_holdings.get(t, 0.0)
        history_qty.append(row)

        if d in change_wide.index:
            day_changes = change_wide.loc[d]
            for t, change in day_changes.items():
                if pd.notna(change) and change != 0:
                    running_holdings[t] = running_holdings.get(t, 0.0) - change

    df_qty_wide = pd.DataFrame(history_qty).set_index('Date').sort_index()

    # --- 5. 주가 및 환율 수집 & 주식 평가금액(Value) 계산 ---
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = today.strftime('%Y-%m-%d')

    print(f"ℹ️ {MODULE_TAG} 총 {len(all_tickers)}개 종목 주가 및 환율 수집 중... ({start_date_str} ~ {end_date_str})")

    # 주가 수집
    df_prices = pd.DataFrame(index=df_qty_wide.index)
    for ticker in all_tickers:
        series = _fetch_price_series(ticker, start_date_str, end_date_str)
        if not series.empty:
            series.index = pd.to_datetime(series.index).tz_localize(None)
            df_prices = df_prices.join(series.rename(ticker), how='left')
        else:
            df_prices[ticker] = 0.0
    df_prices = df_prices.ffill().bfill()

    # 환율 수집
    fx_usd_raw = _fetch_price_series("USDKRW=X", start_date_str, end_date_str)
    fx_usd_raw.index = pd.to_datetime(fx_usd_raw.index).tz_localize(None)
    fx_usd = pd.DataFrame(index=df_qty_wide.index).join(fx_usd_raw.rename('USD'), how='left').ffill().bfill()['USD']

    fx_jpy_raw = _fetch_price_series("JPYKRW=X", start_date_str, end_date_str)
    fx_jpy_raw.index = pd.to_datetime(fx_jpy_raw.index).tz_localize(None)
    fx_jpy = pd.DataFrame(index=df_qty_wide.index).join(fx_jpy_raw.rename('JPY'), how='left').ffill().bfill()['JPY']

    # ✅ 주식 평가액 계산 (수정: 한국 주식 환율 예외 처리 추가)
    df_value_wide = pd.DataFrame(index=df_qty_wide.index)
    for ticker in all_tickers:
        # 1. 환율 결정
        if ticker.endswith('.T'):
            fx_rate = fx_jpy  # 일본 주식: JPY/KRW 환율 적용
        elif ticker.endswith('.KS') or ticker.endswith('.KQ'):
            fx_rate = 1.0  # 한국 주식: 이미 원화이므로 환율 곱하지 않음 (1.0)
        else:
            fx_rate = fx_usd  # 그 외 (미국 등): USD/KRW 환율 적용

        # 2. 평가액 산출
        df_value_wide[ticker] = df_qty_wide[ticker] * df_prices[ticker] * fx_rate

    # --- 6. 현금(Cash) 비중 역산 ---
    ledger_file = config.PROCESSED_DIR / "04Daily_Asset_Ledger.csv"
    if ledger_file.exists():
        df_ledger = local_io.load_csv(ledger_file)
        if 'Date' in df_ledger.columns and 'Calculated_Asset' in df_ledger.columns:
            df_ledger['Date'] = pd.to_datetime(df_ledger['Date']).dt.normalize()
            df_ledger = df_ledger.set_index('Date')

            total_stock_value = df_value_wide.sum(axis=1)
            aligned_asset = df_ledger['Calculated_Asset'].reindex(df_value_wide.index).ffill().bfill()
            cash_value = aligned_asset - total_stock_value

            df_value_wide['Cash'] = cash_value.clip(lower=0)
            print(f"✅ {MODULE_TAG} 현금(Cash) 비중 동기화 완료")
        else:
            print(f"⚠️ {MODULE_TAG} 원장 파일에 필수 컬럼이 없어 현금을 계산할 수 없습니다.")
    else:
        print(f"⚠️ {MODULE_TAG} 04Daily_Asset_Ledger.csv 파일이 없어 현금을 계산할 수 없습니다.")

    # --- 7. 결과 단일 파일 저장 ---
    save_path = config.PROCESSED_DIR / "07Historical_Holdings.csv"
    local_io.save_csv(df_value_wide.reset_index(), save_path)

    print(f"✅ {MODULE_TAG} 타임머신 DB({save_path.name}) 최종 저장 완료")

def main() -> None:
    """모듈 실행 진입점"""
    generate_timeline()

if __name__ == "__main__":
    main()