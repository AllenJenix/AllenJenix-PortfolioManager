"""
@Title: Asset Ledger Engine (Direct Access)
@Description: 한글 컬럼명을 그대로 사용하여 직관적으로 자산 원장을 생성하는 엔진.
              (불필요한 매핑 로직 제거됨)
@Author: Allen & Gemini
@Date: 2026-02-14
"""

# 1. Imports
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 상위 디렉토리 참조 설정
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
MODULE_TAG = "[Ledger]"

# 3. Helper Functions
def _calculate_net_flow(df_tx: pd.DataFrame) -> pd.Series:
    """
    거래 내역(00)에서 순수 외부 자금 흐름을 계산합니다. (한글 컬럼 직접 사용)
    """
    if df_tx.empty:
        return pd.Series(dtype=float)

    # 데이터 복사
    df = df_tx.copy()

    # 날짜 처리 ('일자' 컬럼이 없으면 'Date' 확인)
    if '일자' in df.columns:
        df['Date'] = pd.to_datetime(df['일자'])
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    else:
        print(f"⚠️ {MODULE_TAG} 거래내역에 날짜 컬럼(일자)이 없습니다.")
        return pd.Series(dtype=float)

    # 검색용 텍스트 ('구분' + '적요')
    # 컬럼이 없으면 빈 문자열 처리
    col_type = '구분' if '구분' in df.columns else 'Type'
    col_desc = '적요' if '적요' in df.columns else 'Description'

    df['Type_Full'] = df.get(col_type, "").fillna('') + " " + df.get(col_desc, "").fillna('')

    # 금액 컬럼 찾기 (변동금액 우선, 없으면 거래대금)
    col_amount = '변동금액'
    if col_amount not in df.columns:
        col_amount = '거래대금'

    # 금액 전처리 (쉼표 제거)
    df['Amount_Clean'] = pd.to_numeric(
        df[col_amount].astype(str).str.replace(',', ''),
        errors='coerce'
    ).fillna(0)

    def _get_flow(row):
        t = str(row['Type_Full'])
        amt = float(row['Amount_Clean'])

        # 1. 유입 (+): 입금, 입고, 배당, 이자
        if any(x in t for x in ['입금', '입고', '배당', '이자']):
            # 제외: 내부 이동 (RP, 환전, 매도, 결제 등)
            if any(x in t for x in ['RP', '환전', '매도', '결제', '정산']):
                # 예외적으로 수익인 경우
                if '이자' in t or '이용료' in t: return amt
                return 0
            return amt

        # 2. 유출 (-): 출금, 출고, 세금
        if any(x in t for x in ['출금', '출고', '세금', '세액']):
            # 제외: 내부 이동
            if any(x in t for x in ['RP', '환전', '매수']):
                 if '세금' in t or '세액' in t: return -abs(amt)
                 return 0
            return -abs(amt)

        return 0

    df['NetFlow'] = df.apply(_get_flow, axis=1)

    # 일별 합계 반환
    return df.groupby('Date')['NetFlow'].sum()

# 4. Main Logic
def create_daily_ledger() -> pd.DataFrame:
    """
    일별 자산 원장 생성 (한글 컬럼 직접 접근)
    Input: 01Asset_Summary.csv ('순자산'), 00Transaction_History.csv
    """
    print(f"🚀 {MODULE_TAG} 일별 자산 원장 생성 시작...")

    # 1. 데이터 로드
    try:
        df_anchor = local_io.load_csv(config.PROCESSED_DIR / config.PROCESSED_FILES['asset'])
        df_tx = local_io.load_csv(config.PROCESSED_DIR / config.PROCESSED_FILES['transaction'])
    except FileNotFoundError as e:
        print(f"❌ {MODULE_TAG} 필수 파일 누락: {e}")
        return pd.DataFrame()

    # 2. Anchor(자산) 전처리 - 한글 컬럼 '순자산', '조회일자' 직접 사용
    # 날짜 컬럼 찾기
    col_date = '조회일자' if '조회일자' in df_anchor.columns else 'Date'
    col_asset = '순자산' if '순자산' in df_anchor.columns else 'Net_Asset'

    if col_asset not in df_anchor.columns:
        print(f"❌ {MODULE_TAG} 자산 파일에 '{col_asset}' 컬럼이 없습니다.")
        return pd.DataFrame()

    df_anchor['Date'] = pd.to_datetime(df_anchor[col_date])

    # 숫자 변환 (콤마 제거)
    df_anchor['Net_Asset_Value'] = pd.to_numeric(
        df_anchor[col_asset].astype(str).str.replace(',', ''),
        errors='coerce'
    )

    # 날짜 정렬 및 중복 제거 (월말 데이터 기준)
    df_anchor = df_anchor.sort_values('Date').drop_duplicates('Date', keep='last')
    anchors = df_anchor.set_index('Date')['Net_Asset_Value']

    # 3. Flow(거래) 전처리
    daily_flow = _calculate_net_flow(df_tx)

    # 4. 타임라인 및 보간 준비
    if anchors.empty:
        print(f"❌ {MODULE_TAG} 자산 데이터(Anchor)가 유효하지 않습니다.")
        return pd.DataFrame()

    start_date = anchors.index.min()
    end_date = pd.Timestamp.today()
    if anchors.index.max() > end_date:
        end_date = anchors.index.max()

    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    ledger = pd.DataFrame(index=date_range)
    ledger.index.name = 'Date'

    ledger['Anchor_Asset'] = anchors
    ledger['External_Flow'] = daily_flow
    ledger['External_Flow'] = ledger['External_Flow'].fillna(0)
    ledger['Calculated_Asset'] = np.nan

    # 5. 하이브리드 보간 (Logic 유지)
    anchor_dates = ledger[ledger['Anchor_Asset'].notnull()].index

    prev_date = anchor_dates[0]
    prev_asset = ledger.loc[prev_date, 'Anchor_Asset']
    ledger.loc[prev_date, 'Calculated_Asset'] = prev_asset

    for curr_date in anchor_dates[1:]:
        mask = (ledger.index > prev_date) & (ledger.index <= curr_date)
        days_in_period = ledger.loc[mask].index

        curr_asset = ledger.loc[curr_date, 'Anchor_Asset']

        period_flows = ledger.loc[mask, 'External_Flow']
        total_flow = period_flows.sum()
        theoretical_end = prev_asset + total_flow

        valuation_gain = curr_asset - theoretical_end
        daily_gain = valuation_gain / len(days_in_period) if len(days_in_period) > 0 else 0

        running_asset = prev_asset
        for day in days_in_period:
            flow = ledger.loc[day, 'External_Flow']
            running_asset += flow + daily_gain
            ledger.loc[day, 'Calculated_Asset'] = running_asset

        ledger.loc[curr_date, 'Calculated_Asset'] = curr_asset
        prev_date = curr_date
        prev_asset = curr_asset

    # 미래 구간 처리
    last_anchor_date = anchor_dates[-1]
    if last_anchor_date < ledger.index[-1]:
        mask_future = ledger.index > last_anchor_date
        running_asset = ledger.loc[last_anchor_date, 'Anchor_Asset']
        for day in ledger[mask_future].index:
            flow = ledger.loc[day, 'External_Flow']
            running_asset += flow
            ledger.loc[day, 'Calculated_Asset'] = running_asset

    # 6. 저장
    ledger = ledger.reset_index()
    ledger['Calculated_Asset'] = ledger['Calculated_Asset'].round(0)

    local_io.save_csv(ledger, config.PROCESSED_DIR / config.PROCESSED_FILES['ledger'])
    print(f"✅ {MODULE_TAG} 일별 자산 원장 저장 완료 ({len(ledger)} rows)")

    return ledger


def generate_integrated_portfolio(ledger_df: pd.DataFrame) -> pd.DataFrame:
    """
    [Fixed] 현금 통합 포트폴리오 생성 (FutureWarning 완벽 해결 버전)
    """
    print(f"🚀 {MODULE_TAG} 현금 통합 포트폴리오 생성 시작...")

    path_holdings = config.PROCESSED_DIR / config.PROCESSED_FILES['holdings']
    if not path_holdings.exists():
        return pd.DataFrame()

    df_holdings = local_io.load_csv(path_holdings)

    if ledger_df.empty:
        return df_holdings

    latest_total_asset = ledger_df.iloc[-1]['Calculated_Asset']

    # [한글 컬럼 사용] '평가금액'
    col_eval = '평가금액'
    if col_eval not in df_holdings.columns:
        print(f"⚠️ {MODULE_TAG} 보유종목에 '{col_eval}' 컬럼이 없습니다.")
        return df_holdings

    # 평가금액 합계 계산
    stock_sum = pd.to_numeric(
        df_holdings[col_eval].astype(str).str.replace(',', ''),
        errors='coerce'
    ).sum()

    cash_amount = latest_total_asset - stock_sum

    # [Fix] 모든 컬럼을 None으로 초기화하지 않고, 필요한 데이터만 정의합니다.
    # 나머지 컬럼은 pd.concat 과정에서 자동으로 NaN으로 채워집니다.
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

    # 1행짜리 DataFrame 생성
    cash_df = pd.DataFrame([cash_data])

    # concat 수행
    df_full = pd.concat([df_holdings, cash_df], ignore_index=True)

    # 비중 재계산
    df_full[col_eval] = pd.to_numeric(df_full[col_eval], errors='coerce').fillna(0)
    total_val = df_full[col_eval].sum()

    if total_val > 0:
        df_full['보유비중'] = (df_full[col_eval] / total_val * 100).round(2)

    # 저장
    save_path = config.PROCESSED_DIR / "03Full_Portfolio.csv"
    if 'full_portfolio' in config.PROCESSED_FILES:
        save_path = config.PROCESSED_DIR / config.PROCESSED_FILES['full_portfolio']

    local_io.save_csv(df_full, save_path)

    print(f"ℹ️ 총 자산: {latest_total_asset:,.0f}")
    print(f"ℹ️ 주식 합계: {stock_sum:,.0f}")
    print(f"ℹ️ 산출 현금: {cash_amount:,.0f}")
    print(f"✅ {MODULE_TAG} 통합 포트폴리오 저장 완료")

    return df_full

# 5. Execution Block
if __name__ == "__main__":
    df_ledger = create_daily_ledger()
    if not df_ledger.empty:
        generate_integrated_portfolio(df_ledger)