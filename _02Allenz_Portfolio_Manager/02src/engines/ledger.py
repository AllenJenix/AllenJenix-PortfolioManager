"""
@Title: Asset Ledger Engine v2 (Bottom-Up Reconstruction)
@Description: 매매일 기준 거래내역(2610)과 yfinance 일별 종가를 결합하여
              일별 포트폴리오 자산을 Bottom-up으로 산출합니다.
              한국 ETF는 1750(장내 거래)에서 보완합니다.
@Author: Allen & Claude
@Date: 2026-05-09
"""

# 1. Imports
import sys
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config

try:
    from data_loaders import io as local_io
    from data_loaders.trade_log import build_unified_trade_log, build_daily_trade_cash_flows
except ImportError:
    import io as local_io
    from trade_log import build_unified_trade_log, build_daily_trade_cash_flows

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

# 2. Constants
MODULE_TAG = "[Ledger]"
_YF_CACHE_TTL_HOURS = 24


# 3. Main Logic

def _calculate_net_flow(df_tx: pd.DataFrame) -> pd.Series:
    """
    진정한 외부 자금 흐름 집계 (TWR 기준).

    포함: 은행이체입금/출금, 계좌대체입금/출금
    제외: 환전, RP, 주식 결제, 가환전 등 내부 이동 전액

    Args:
        df_tx (pd.DataFrame): 00Transaction_History.csv

    Returns:
        pd.Series: 날짜별 순외부자금흐름 (KRW)
    """
    if df_tx.empty:
        return pd.Series(dtype=float)

    df = df_tx.copy()

    if '일자' in df.columns:
        df['Date'] = pd.to_datetime(df['일자'], errors='coerce')
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        print(f"⚠️ {MODULE_TAG} 거래내역 날짜 컬럼 없음")
        return pd.Series(dtype=float)

    col_type = '구분' if '구분' in df.columns else 'Type'
    col_amount = '변동금액' if '변동금액' in df.columns else '거래대금'

    df['Amount_Clean'] = pd.to_numeric(
        df[col_amount].astype(str).str.replace(',', ''), errors='coerce'
    ).fillna(0)

    def _classify_flow(row) -> float:
        t = str(row.get(col_type, ''))
        amt = float(row['Amount_Clean'])
        if '은행이체입금' in t or '계좌대체입금' in t:
            return amt
        if '은행이체출금' in t or '계좌대체출금' in t:
            return -abs(amt)
        return 0.0

    df['NetFlow'] = df.apply(_classify_flow, axis=1)
    df = df.dropna(subset=['Date'])
    return df.groupby('Date')['NetFlow'].sum()


def _build_daily_holdings(
    trade_log: pd.DataFrame,
    date_range: pd.DatetimeIndex
) -> pd.DataFrame:
    """
    일별 누적 보유 수량 매트릭스 생성.

    Args:
        trade_log (pd.DataFrame): 통합 거래 로그 (date, isin, quantity)
        date_range (pd.DatetimeIndex): 분석 기간 전체 날짜 배열

    Returns:
        pd.DataFrame: index=date, columns=isin, values=shares_held (≥0)
    """
    if trade_log.empty:
        return pd.DataFrame(index=date_range)

    isins = trade_log['isin'].unique()
    holdings = pd.DataFrame(0.0, index=date_range, columns=isins)

    for isin, grp in trade_log.groupby('isin'):
        # 결제일 기준 통일 (T+0/T+2 phantom drawdown 제거).
        # 1750_kr 거래는 settlement_date가 NaT이므로 trade date로 fallback.
        effective_date = grp['settlement_date'].fillna(grp['date'])
        qty_changes = grp.groupby(effective_date)['quantity'].sum()
        qty_changes = qty_changes.reindex(date_range, fill_value=0.0)
        # 음수 클램핑: 데이터 오류(미추적 포지션)로 인한 음수 방지
        holdings[isin] = qty_changes.cumsum().clip(lower=0)

    return holdings


def _fetch_yf_prices(tickers: list, start: str, end: str) -> pd.DataFrame:
    """
    yfinance 수정종가 조회 (CACHE_DIR/yf_prices.pkl, 24h TTL).

    Args:
        tickers (list): yfinance 티커 목록
        start   (str) : 조회 시작일 'YYYY-MM-DD'
        end     (str) : 조회 종료일 'YYYY-MM-DD'

    Returns:
        pd.DataFrame: index=Date, columns=ticker, values=adj_close
    """
    if not _YF_AVAILABLE:
        print(f"⚠️ {MODULE_TAG} yfinance 미설치. pip install yfinance")
        return pd.DataFrame()

    cache_file = config.CACHE_DIR / "yf_prices.pkl"
    cache: dict = {}
    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                cache = pickle.load(f)
        except Exception:
            cache = {}

    frames = []
    now = datetime.now()
    needs_start = pd.Timestamp(start)
    needs_end = pd.Timestamp(end)

    for ticker in tickers:
        entry = cache.get(ticker, {})
        df_cached: pd.DataFrame = entry.get('data', pd.DataFrame())
        cached_at: datetime = entry.get('cached_at', datetime.min)
        cache_fresh = (now - cached_at).total_seconds() < _YF_CACHE_TTL_HOURS * 3600

        # 캐시 유효성 확인 (TTL + 날짜 커버리지)
        if (not df_cached.empty and cache_fresh and
                pd.Timestamp(df_cached.index.min()) <= needs_start and
                pd.Timestamp(df_cached.index.max()) >= needs_end - timedelta(days=5)):
            frames.append(df_cached.rename(columns={'Close': ticker}))
            continue

        try:
            raw = yf.download(ticker, start=start, end=end,
                              auto_adjust=True, progress=False)
            if raw.empty:
                print(f"⚠️ {MODULE_TAG} 데이터 없음: {ticker}")
                continue
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            df_p = raw[['Close']].copy()
            df_p.index = pd.to_datetime(df_p.index)
            cache[ticker] = {'data': df_p, 'cached_at': now}
            frames.append(df_p.rename(columns={'Close': ticker}))
            print(f"  ✓ {ticker}: {len(df_p)}일")
        except Exception as e:
            print(f"⚠️ {MODULE_TAG} yfinance 오류 ({ticker}): {e}")

    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f)
    except Exception:
        pass

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, axis=1)
    result.index = pd.to_datetime(result.index)
    return result.sort_index()


def _resolve_tickers(
    holdings: pd.DataFrame,
    trade_log: pd.DataFrame
) -> tuple[dict, dict]:
    """
    ISIN별 yfinance 티커와 통화 결정.

    규칙:
      - USD 거래 → 2610 티커 그대로 사용 (US, IL, CH 등 모두 포함)
      - JPY 거래 → 2610 티커 + '.T' (도쿄거래소)
      - KRW 거래 → isin_mapping.json 의 '.KS' 티커 (한국 ETF)

    Args:
        holdings (pd.DataFrame): 일별 보유 수량 매트릭스
        trade_log (pd.DataFrame): 통합 거래 로그

    Returns:
        tuple[dict, dict]: (isin_to_ticker, isin_to_currency)
    """
    isin_to_ticker: dict = {}
    isin_to_currency: dict = {}

    # 거래 로그에서 ISIN별 통화/티커 추출
    currency_map = trade_log.groupby('isin')['currency'].first().to_dict()
    ticker_map = trade_log.groupby('isin')['ticker'].first().to_dict()

    for isin in holdings.columns:
        currency = currency_map.get(isin, 'USD')
        isin_to_currency[isin] = currency

        base_ticker = ticker_map.get(isin, config.ISIN_TO_TICKER.get(isin, ''))

        if currency == 'KRW':
            # 한국 ETF: isin_mapping 의 '.KS' 티커 사용
            isin_to_ticker[isin] = config.ISIN_TO_TICKER.get(isin, base_ticker)
        elif currency == 'JPY':
            # 일본 주식: '.T' 접미사 추가
            isin_to_ticker[isin] = base_ticker if base_ticker.endswith('.T') else base_ticker + '.T'
        else:
            # USD: isin_mapping 키 존재 시 해당 값 우선 적용 (BRK.B→BRK-B, 빈 문자열=가격 조회 생략)
            # 키 없으면 2610 티커 fallback
            if isin in config.ISIN_TO_TICKER:
                isin_to_ticker[isin] = config.ISIN_TO_TICKER[isin]
            else:
                isin_to_ticker[isin] = base_ticker

    return isin_to_ticker, isin_to_currency


def _compute_equity_krw(
    holdings: pd.DataFrame,
    prices: pd.DataFrame,
    isin_to_ticker: dict,
    isin_to_currency: dict,
    fx_usd_krw: pd.Series,
    fx_jpy_krw: pd.Series
) -> pd.Series:
    """
    일별 주식 평가금액 합계 (KRW).

    Args:
        holdings      (pd.DataFrame): index=date, columns=isin, values=수량
        prices        (pd.DataFrame): index=date, columns=ticker, values=종가
        isin_to_ticker (dict)       : {isin: yf_ticker}
        isin_to_currency (dict)     : {isin: 'USD'|'JPY'|'KRW'}
        fx_usd_krw    (pd.Series)   : USD/KRW 환율 (원/달러)
        fx_jpy_krw    (pd.Series)   : JPY/KRW 환율 (원/엔)

    Returns:
        pd.Series: 날짜별 주식 평가금액 합계 (KRW)
    """
    equity = pd.Series(0.0, index=holdings.index)

    for isin in holdings.columns:
        qty = holdings[isin]
        if qty.abs().max() == 0:
            continue

        ticker = isin_to_ticker.get(isin, '')
        if not ticker:
            # isin_mapping에서 의도적으로 빈 문자열로 설정된 ISIN (예: 역분할 가격 오류)
            continue
        if ticker not in prices.columns:
            print(f"⚠️ {MODULE_TAG} 가격 조회 실패: {isin} → '{ticker}'")
            continue

        price = prices[ticker].reindex(holdings.index).ffill().bfill()
        currency = isin_to_currency.get(isin, 'USD')

        if currency == 'KRW':
            fx = pd.Series(1.0, index=holdings.index)
        elif currency == 'JPY':
            fx = fx_jpy_krw.reindex(holdings.index).ffill().bfill()
            if fx.isna().all():
                print(f"⚠️ {MODULE_TAG} JPY/KRW 환율 없음 — {isin} 제외")
                continue
        else:
            # USD (기본)
            fx = fx_usd_krw.reindex(holdings.index).ffill().bfill()

        equity += qty * price * fx

    return equity


def create_daily_ledger(business_days_only: bool = False) -> pd.DataFrame:
    """
    일별 자산 원장 생성 (Bottom-Up v2).

    알고리즘:
      1. 통합 거래 로그 구성 (2610 primary + 1750 한국 ETF supplement)
      2. 일별 보유 수량 산출
      3. yfinance 가격 조회 (캐싱)
      4. Equity_Value = 수량 × 가격 × FX환율 (KRW 합산)
      5. Cash 보정: 각 앵커 구간별로
         - cash_start = Anchor_prev - Equity_prev  (정확)
         - cash_end   = Anchor_curr - Equity_curr  (정확)
         - 외부자금흐름(은행이체) + 거래현금흐름(결제일 기준 settlement_amount) 정확 반영
         - 잔차(FX·배당 등)만 일별 균등 배분 (BUG-03 수정)
      6. Calculated_Asset = Equity + Cash
         (앵커 날짜에서는 HTS 값으로 고정)

    Args:
        business_days_only (bool): True이면 주말 행 제거

    Returns:
        pd.DataFrame: 04Daily_Asset_Ledger.csv 스키마 호환
    """
    print(f"🚀 {MODULE_TAG} 일별 자산 원장 생성 시작 (Bottom-Up v2)...")

    # Step 1: HTS 앵커 로드
    df_anchor = local_io.load_csv(config.PROCESSED_DIR / config.PROCESSED_FILES['asset'])
    if df_anchor.empty:
        print(f"❌ {MODULE_TAG} 자산현황 파일 없음")
        return pd.DataFrame()

    col_date_a = '조회일자' if '조회일자' in df_anchor.columns else 'Date'
    col_nav = '순자산' if '순자산' in df_anchor.columns else 'Net_Asset'

    df_anchor['Date'] = pd.to_datetime(df_anchor[col_date_a], format='mixed', errors='coerce')
    df_anchor['NAV'] = pd.to_numeric(
        df_anchor[col_nav].astype(str).str.replace(',', ''), errors='coerce')
    df_anchor = df_anchor.dropna(subset=['Date', 'NAV']).sort_values('Date')
    anchors = df_anchor.set_index('Date')['NAV']

    # Step 2: 외부 자금 흐름
    df_tx = local_io.load_csv(config.PROCESSED_DIR / config.PROCESSED_FILES['transaction'])
    daily_flow = _calculate_net_flow(df_tx)

    # Step 3: 통합 거래 로그 & 일별 보유 수량 (SSOT: data_loaders/trade_log.py)
    trade_log = build_unified_trade_log()

    start_date = anchors.index.min()
    end_date = max(anchors.index.max(), pd.Timestamp.today())
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    holdings = _build_daily_holdings(trade_log, date_range)
    print(f"ℹ️ {MODULE_TAG} Holdings: {len(holdings.columns)} ISINs, {len(date_range)}일")

    # Step 4: 티커/통화 매핑
    isin_to_ticker, isin_to_currency = _resolve_tickers(holdings, trade_log)

    # Step 5: yfinance 가격 조회
    equity_tickers = [t for t in isin_to_ticker.values() if t]
    # KRW=X → USD/KRW, JPY=X → JPY/USD (JPY/KRW 계산용)
    all_tickers = sorted(set(equity_tickers + ['KRW=X', 'JPY=X']))

    yf_start = (start_date - timedelta(days=5)).strftime('%Y-%m-%d')
    yf_end = (end_date + timedelta(days=2)).strftime('%Y-%m-%d')

    print(f"ℹ️ {MODULE_TAG} yfinance 조회 ({len(equity_tickers)} equity + 2 FX tickers)...")
    prices_all = _fetch_yf_prices(all_tickers, yf_start, yf_end)

    # Step 6: FX 환율 계산
    fx_usd_krw = pd.Series(dtype=float)
    fx_jpy_krw = pd.Series(dtype=float)

    if not prices_all.empty:
        if 'KRW=X' in prices_all.columns:
            fx_usd_krw = prices_all['KRW=X']
        # JPY/KRW = (KRW/USD) / (JPY/USD)
        if 'JPY=X' in prices_all.columns and not fx_usd_krw.empty:
            fx_jpy_krw = fx_usd_krw / prices_all['JPY=X']

    # Step 7: 일별 주식 평가금액 (KRW)
    equity_krw = _compute_equity_krw(
        holdings, prices_all,
        isin_to_ticker, isin_to_currency,
        fx_usd_krw, fx_jpy_krw
    )
    equity_krw = equity_krw.reindex(date_range).ffill().fillna(0)

    # Step 8: Cash 보정 (앵커 구간별) — BUG-03 수정
    #
    # [앵커 구간 내 로직]
    #   cash_start          = Anchor_prev - Equity_prev  (정확값)
    #   cash_end_target     = Anchor_curr - Equity_curr  (정확값)
    #   total_ext_flows     = 구간 내 은행이체 흐름 합계
    #   total_trade_flows   = 구간 내 결제일 기준 거래 현금 흐름 합계 (2610)
    #   unexplained         = (cash_end_target - cash_start)
    #                         - total_ext_flows - total_trade_flows
    #                         (FX 변동, 배당, 이자 등 순수 잔차만 남음)
    #   일별 cash[t] = cash[t-1] + ext_flow[t] + trade_flow[t] + unexplained/n
    #
    trade_cash_flows = build_daily_trade_cash_flows(trade_log)

    anchor_dates = sorted(anchors.index)
    cash_series = pd.Series(np.nan, index=date_range, dtype=float)
    calc_asset = pd.Series(np.nan, index=date_range, dtype=float)

    # 첫 앵커 이전 구간: 첫 앵커 값 역방향 flat 처리
    first_anchor = anchor_dates[0]
    pre_mask = date_range < first_anchor
    if pre_mask.any():
        initial_cash = anchors[first_anchor] - equity_krw.get(first_anchor, 0)
        cash_series[pre_mask] = initial_cash
        calc_asset[pre_mask] = equity_krw[pre_mask] + initial_cash

    # 첫 앵커 날짜 설정
    cash_series[first_anchor] = anchors[first_anchor] - equity_krw.get(first_anchor, 0)
    calc_asset[first_anchor] = float(anchors[first_anchor])

    prev_anchor = first_anchor

    for curr_anchor in anchor_dates[1:]:
        period_mask = (date_range > prev_anchor) & (date_range <= curr_anchor)
        period_days = date_range[period_mask]
        n = len(period_days)

        if n == 0:
            prev_anchor = curr_anchor
            continue

        cash_start = float(cash_series[prev_anchor])
        cash_end_target = float(anchors[curr_anchor]) - float(equity_krw.get(curr_anchor, 0))

        period_ext_flows = daily_flow.reindex(period_days).fillna(0)
        period_trade_flows = trade_cash_flows.reindex(period_days).fillna(0)
        total_known_flows = period_ext_flows.sum() + period_trade_flows.sum()
        unexplained = (cash_end_target - cash_start) - total_known_flows
        daily_unexplained = unexplained / n

        running_cash = cash_start
        for day in period_days:
            ext_flow = float(daily_flow.get(day, 0))
            trade_flow = float(trade_cash_flows.get(day, 0.0))
            running_cash += ext_flow + trade_flow + daily_unexplained
            cash_series[day] = running_cash
            calc_asset[day] = float(equity_krw.get(day, 0)) + running_cash

        # 앵커 날짜: HTS 정확값으로 고정
        cash_series[curr_anchor] = cash_end_target
        calc_asset[curr_anchor] = float(anchors[curr_anchor])
        prev_anchor = curr_anchor

    # 마지막 앵커 이후 구간: 외부자금흐름 + 거래 현금흐름 반영
    last_anchor = anchor_dates[-1]
    if last_anchor < date_range[-1]:
        running_cash = float(cash_series[last_anchor])
        for day in date_range[date_range > last_anchor]:
            ext_flow = float(daily_flow.get(day, 0))
            trade_flow = float(trade_cash_flows.get(day, 0.0))
            running_cash += ext_flow + trade_flow
            cash_series[day] = running_cash
            calc_asset[day] = float(equity_krw.get(day, 0)) + running_cash

    # Step 9: 원장 DataFrame 조립
    ledger = pd.DataFrame(index=date_range)
    ledger.index.name = 'Date'
    ledger['Anchor_Asset'] = anchors.reindex(date_range)
    ledger['External_Flow'] = daily_flow.reindex(date_range).fillna(0)
    ledger['Equity_Value'] = equity_krw.round(0)
    ledger['Calculated_Asset'] = calc_asset.round(0)

    # Step 10: 주말 필터 (선택)
    if business_days_only:
        n_before = len(ledger)
        ledger = ledger[ledger.index.dayofweek < 5]
        print(f"ℹ️ {MODULE_TAG} 주말 {n_before - len(ledger)}행 제거 → {len(ledger)}행")

    # Step 11: 저장
    ledger = ledger.reset_index()
    local_io.save_csv(ledger, config.PROCESSED_DIR / config.PROCESSED_FILES['ledger'])
    print(f"✅ {MODULE_TAG} 일별 자산 원장 저장 완료 ({len(ledger)}행)")
    return ledger


def generate_integrated_portfolio(ledger_df: pd.DataFrame) -> pd.DataFrame:
    """
    현금 통합 포트폴리오 생성 (보유종목 + 산출 현금).

    Args:
        ledger_df (pd.DataFrame): create_daily_ledger() 반환값

    Returns:
        pd.DataFrame: 03Full_Portfolio.csv 스키마 호환
    """
    print(f"🚀 {MODULE_TAG} 현금 통합 포트폴리오 생성 시작...")

    path_holdings = config.PROCESSED_DIR / config.PROCESSED_FILES['holdings']
    if not path_holdings.exists():
        return pd.DataFrame()

    df_holdings = local_io.load_csv(path_holdings)
    if ledger_df.empty:
        return df_holdings

    latest_total = ledger_df.iloc[-1]['Calculated_Asset']
    col_eval = '평가금액'

    if col_eval not in df_holdings.columns:
        print(f"⚠️ {MODULE_TAG} '{col_eval}' 컬럼 없음")
        return df_holdings

    stock_sum = pd.to_numeric(
        df_holdings[col_eval].astype(str).str.replace(',', ''), errors='coerce'
    ).sum()

    cash_amount = latest_total - stock_sum

    cash_data = {
        '종목명': '현금 및 예수금 (KRW/USD)',
        '종목코드': 'CASH',
        '잔고수량': 1.0,
        col_eval: float(cash_amount),
        '매입금액': float(cash_amount),
        '현재가': float(cash_amount),
        '구분': '현금',
        '보유비중': 0.0
    }

    df_full = pd.concat([df_holdings, pd.DataFrame([cash_data])], ignore_index=True)
    df_full[col_eval] = pd.to_numeric(df_full[col_eval], errors='coerce').fillna(0)
    total_val = df_full[col_eval].sum()
    if total_val > 0:
        df_full['보유비중'] = (df_full[col_eval] / total_val * 100).round(2)

    save_path = config.PROCESSED_DIR / config.PROCESSED_FILES.get('full_portfolio', '03Full_Portfolio.csv')
    local_io.save_csv(df_full, save_path)

    print(f"ℹ️ 총 자산: {latest_total:,.0f} | 주식: {stock_sum:,.0f} | 현금: {cash_amount:,.0f}")
    print(f"✅ {MODULE_TAG} 통합 포트폴리오 저장 완료")
    return df_full


# 4. Execution Block
def main():
    df_ledger = create_daily_ledger(business_days_only=False)
    if not df_ledger.empty:
        generate_integrated_portfolio(df_ledger)


if __name__ == "__main__":
    main()
