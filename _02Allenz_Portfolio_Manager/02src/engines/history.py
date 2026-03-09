"""
@Title: Time Machine Engine (Historical Holdings & Valuation)
@Description: 과거 모든 날짜의 종목별 평가금액과 '현금(Cash)'을 역산하여 완벽한 포트폴리오 스냅샷(Wide Format)을 복원합니다.
@Author: Allen & Gemini
"""

# 1. Imports
import sys
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
except ImportError:
    import io as local_io

# 2. Constants
MODULE_TAG = "[TimeMachine]"

# 3. Helper Functions
def _fetch_price_series(ticker: str, start_date: str, end_date: str) -> pd.Series:
    """특정 티커의 과거 수정 종가를 가져옵니다."""
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

# 4. Main Logic
def generate_timeline():
    print(f"🚀 {MODULE_TAG} 타임머신 데이터(Wide Format 역산 + 현금) 생성 시작...")

    # --- 1. 거래 내역 (Transaction) 처리 ---
    txn_file = config.PROCESSED_DIR / "00Transaction_History.csv"
    if not txn_file.exists():
        print(f"❌ {MODULE_TAG} 거래 내역 파일이 없습니다.")
        return

    df_txn = local_io.load_csv(txn_file)
    df_txn['일자'] = pd.to_datetime(df_txn['일자'])

    mask_stock = df_txn['구분'].str.contains('매수|매도', na=False) & df_txn['종목번호'].notna()
    df_stocks = df_txn[mask_stock].copy()

    if df_stocks.empty:
        print(f"⚠️ {MODULE_TAG} 주식 거래 내역이 없습니다.")
        return

    # ISIN -> Ticker 매핑
    df_stocks['Ticker'] = df_stocks['종목번호'].map(config.ISIN_TO_TICKER)
    df_stocks = df_stocks.dropna(subset=['Ticker'])

    # 매도는 수량을 음수로 변환
    mask_sell = df_stocks['구분'].str.contains('매도')
    df_stocks.loc[mask_sell, '수량'] = -df_stocks.loc[mask_sell, '수량']

    daily_change = df_stocks.groupby(['일자', 'Ticker'])['수량'].sum().reset_index()
    change_wide = daily_change.pivot(index='일자', columns='Ticker', values='수량').fillna(0)

    # --- 2. 현재 잔고 (Current Holdings) 앵커링 ---
    holdings_file = config.PROCESSED_DIR / "02Portfolio_Holdings.csv"
    current_holdings = {}

    if holdings_file.exists():
        df_holdings = local_io.load_csv(holdings_file)
        if not df_holdings.empty and '종목코드' in df_holdings.columns:
            df_holdings['Ticker'] = df_holdings['종목코드'].map(config.ISIN_TO_TICKER)
            for _, row in df_holdings.dropna(subset=['Ticker']).iterrows():
                current_holdings[row['Ticker']] = float(row.get('잔고수량', 0))

    # --- 3. 역산 (Reverse Engineering) 알고리즘 ---
    all_tickers = list(set(current_holdings.keys()) | set(df_stocks['Ticker'].unique()))

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

    # --- 4. 주가 및 환율 수집 & 주식 평가금액(Value) 계산 ---
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = today.strftime('%Y-%m-%d')

    print(f"ℹ️ 총 {len(all_tickers)}개 종목 주가 및 환율 수집 중... ({start_date_str} ~ {end_date_str})")

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

    # ⭐️ 주식 평가액 계산
    df_value_wide = pd.DataFrame(index=df_qty_wide.index)
    for ticker in all_tickers:
        fx_rate = fx_jpy if ticker.endswith('.T') else fx_usd
        df_value_wide[ticker] = df_qty_wide[ticker] * df_prices[ticker] * fx_rate

    # --- 5. ⭐️ 현금(Cash) 비중 역산 ⭐️ ---
    ledger_file = config.PROCESSED_DIR / "04Daily_Asset_Ledger.csv"
    if ledger_file.exists():
        df_ledger = local_io.load_csv(ledger_file)
        if 'Date' in df_ledger.columns and 'Calculated_Asset' in df_ledger.columns:
            df_ledger['Date'] = pd.to_datetime(df_ledger['Date']).dt.normalize()
            df_ledger = df_ledger.set_index('Date')

            # 매일매일의 '주식 평가액 총합' 계산
            total_stock_value = df_value_wide.sum(axis=1)

            # 04원장의 '총 자산(Calculated_Asset)'을 현재 타임라인 날짜와 매칭
            aligned_asset = df_ledger['Calculated_Asset'].reindex(df_value_wide.index).ffill().bfill()

            # 현금 = 총 자산 - 주식 평가액 총합
            cash_value = aligned_asset - total_stock_value

            # 신용/미수를 쓰지 않는 이상 현금은 0 이상이므로, 혹시 모를 환율 오차 방지를 위해 0으로 하한선 설정
            df_value_wide['Cash'] = cash_value.clip(lower=0)
            print(f"✅ {MODULE_TAG} 현금(Cash) 비중 동기화 완료")
        else:
            print(f"⚠️ {MODULE_TAG} 원장 파일에 필수 컬럼이 없어 현금을 계산할 수 없습니다.")
    else:
        print(f"⚠️ {MODULE_TAG} 04Daily_Asset_Ledger.csv 파일이 없어 현금을 계산할 수 없습니다.")

    # --- 6. 결과 단일 파일 저장 ---
    save_path = config.PROCESSED_DIR / "07Historical_Holdings.csv"
    local_io.save_csv(df_value_wide.reset_index(), save_path)

    print(f"✅ {MODULE_TAG} 타임머신 DB({save_path.name}) 최종 저장 완료")

def main():
    generate_timeline()

if __name__ == "__main__":
    main()