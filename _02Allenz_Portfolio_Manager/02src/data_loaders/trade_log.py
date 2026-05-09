"""
@Title: Trade Log Data Loader (Single Source of Truth)
@Description: 해외주식(2610) + 한국 ETF(1750) 통합 거래 로그.
              ledger.py와 history.py가 공통으로 참조하는 SSOT 모듈.
@Author: Allen & Claude
@Date: 2026-05-10
"""

# 1. Imports
import sys
import numpy as np
import pandas as pd
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config
from data_loaders import io as local_io

# 2. Constants
MODULE_TAG = "[TradeLog]"

_TRADE_LOG_COLS = [
    'date', 'isin', 'quantity', 'currency', 'ticker',
    'source', 'settlement_date', 'settlement_amount',
]


# 3. Public API

def build_unified_trade_log() -> pd.DataFrame:
    """
    통합 거래 로그 생성 (SSOT).

    Primary   : 08Equity_Trade_History.csv (2610 기반)
                매매일/결제일/결제금액(KRW) 모두 포함.
    Supplement: 00Transaction_History.csv (1750 기반, 한국 ETF 장내 매매)
                settlement_date·settlement_amount 없음 → NaN 처리.

    Returns:
        pd.DataFrame: columns=[date, isin, quantity, currency, ticker,
                               source, settlement_date, settlement_amount]
    """
    df_primary = _load_2610_trades()
    df_supplement = _load_1750_kr_trades()

    combined = pd.concat([df_primary, df_supplement], ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date'])
    combined['settlement_date'] = pd.to_datetime(combined['settlement_date'])
    combined = (
        combined
        .dropna(subset=['date', 'isin'])
        .sort_values('date')
        .reset_index(drop=True)
    )

    if not combined.empty:
        print(f"✅ {MODULE_TAG} 통합 거래 로그: {len(combined)}건 "
              f"({combined['date'].min().date()} → {combined['date'].max().date()})")
    return combined


def build_daily_trade_cash_flows(trade_log: pd.DataFrame) -> pd.Series:
    """
    결제일 기준 일별 거래 현금 흐름 산출.

    2610(해외주식) + 1750_kr(한국 ETF) 모두 포함.
    settlement_date·settlement_amount가 유효한 행 전체를 대상으로 함.
    - 매도(quantity < 0) → +settlement_amount (현금 유입)
    - 매수(quantity > 0) → -settlement_amount (현금 유출)

    settlement_amount는 절대값(KRW)으로 저장됨.

    Args:
        trade_log (pd.DataFrame): build_unified_trade_log() 반환값

    Returns:
        pd.Series: index=settlement_date, values=KRW 현금 흐름 합계
    """
    df_settled = trade_log[
        trade_log['settlement_date'].notna() &
        trade_log['settlement_amount'].notna() &
        (trade_log['settlement_amount'] > 0)
    ].copy()

    if df_settled.empty:
        return pd.Series(dtype=float, name='trade_cash_flow')

    df_settled['cash_flow'] = df_settled.apply(
        lambda r: float(r['settlement_amount'])
                  if float(r['quantity']) < 0
                  else -float(r['settlement_amount']),
        axis=1
    )

    result = df_settled.groupby('settlement_date')['cash_flow'].sum()
    result.name = 'trade_cash_flow'
    return result


# 4. Private Loaders

def _load_2610_trades() -> pd.DataFrame:
    """2610 (해외주식) 거래 로드. settlement_date·settlement_amount 포함."""
    path = config.PROCESSED_DIR / config.PROCESSED_FILES.get('trade_history', '')
    empty = pd.DataFrame(columns=_TRADE_LOG_COLS)

    if not (path and path.exists()):
        return empty

    raw = local_io.load_csv(path)
    if raw.empty:
        return empty

    raw['trade_date'] = pd.to_datetime(raw['trade_date'], errors='coerce')

    # settlement_date: 결제예정일 (파서에서 row1[4] 추출, 항상 존재)
    raw['settlement_date'] = pd.to_datetime(
        raw['settlement_date'] if 'settlement_date' in raw.columns else raw['trade_date'],
        errors='coerce'
    )

    # settlement_amount: 결제금액(KRW 절대값). 파서의 _clean_number로 항상 양수.
    raw['settlement_amount'] = pd.to_numeric(
        raw['settlement_amount'] if 'settlement_amount' in raw.columns else 0,
        errors='coerce'
    ).abs().fillna(0)

    df_p = raw[[
        'trade_date', 'isin', 'quantity', 'currency', 'ticker',
        'settlement_date', 'settlement_amount',
    ]].copy()
    df_p.columns = [
        'date', 'isin', 'quantity', 'currency', 'ticker',
        'settlement_date', 'settlement_amount',
    ]
    df_p['source'] = '2610'

    print(f"ℹ️ {MODULE_TAG} 2610 primary  : {len(df_p)} trades "
          f"({raw['trade_date'].min().date()} → {raw['trade_date'].max().date()})")
    return df_p[_TRADE_LOG_COLS]


def _load_1750_kr_trades() -> pd.DataFrame:
    """1750 (한국 ETF) 거래 로드.

    settlement_date: 매매일 + 2 영업일 (국내 주식 T+2 결제 주기).
    settlement_amount: 1750.csv의 '변동금액' (수수료·세금 차감 후 KRW 절대값).
    """
    path_tx = config.PROCESSED_DIR / config.PROCESSED_FILES['transaction']
    empty = pd.DataFrame(columns=_TRADE_LOG_COLS)

    if not path_tx.exists():
        return empty

    df_tx = local_io.load_csv(path_tx)
    df_tx['_date'] = pd.to_datetime(df_tx['일자'], errors='coerce')

    kr_mask = df_tx['구분'].isin(['장내_매수', '장내_매도'])
    df_kr = df_tx[kr_mask].copy()

    if df_kr.empty:
        return empty

    df_kr['quantity'] = df_kr.apply(
        lambda r: float(r['수량']) if '매수' in str(r['구분']) else -float(r['수량']),
        axis=1
    )
    df_kr['isin'] = df_kr['종목번호'].astype(str).str.strip()
    df_kr['currency'] = 'KRW'
    df_kr['ticker'] = df_kr['isin'].map(config.ISIN_TO_TICKER).fillna('')

    df_s = df_kr[['_date', 'isin', 'quantity', 'currency', 'ticker']].copy()
    df_s.columns = ['date', 'isin', 'quantity', 'currency', 'ticker']
    df_s['source'] = '1750_kr'

    # 한국 ETF T+2 결제일 (영업일 기준)
    df_s['settlement_date'] = df_s['date'].apply(
        lambda d: d + pd.offsets.BDay(2) if pd.notna(d) else pd.NaT
    )
    # 변동금액 = 수수료·세금 차감 후 실제 현금 변동액 (절대값으로 저장).
    # df_s는 df_kr에서 파생되어 동일한 인덱스를 공유하므로 .values 불필요.
    # pd.to_numeric(.values)는 ndarray를 반환 → .abs() 미지원 → .values 제거.
    df_s['settlement_amount'] = pd.to_numeric(
        df_kr['변동금액'], errors='coerce'
    ).abs()

    print(f"ℹ️ {MODULE_TAG} 1750 supplement: {len(df_s)} trades (한국 ETF)")
    return df_s[_TRADE_LOG_COLS]
