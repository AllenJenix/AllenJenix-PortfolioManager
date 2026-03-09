"""
@Title: Performance Metrics Engine
@Description: 일별 자산 원장(04)을 기반으로 TWR(시간가중), MWR(금액가중/XIRR), MDD(최대낙폭)를 계산하는 엔진
@Author: Allen & Gemini
@Date: 2026-02-14
"""

# 1. Imports
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import optimize  # MWR(XIRR) 계산용

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
MODULE_TAG = "[Metrics]"


# 3. Helper Functions
def _calculate_xirr(cash_flows: list, dates: list) -> float:
    """
    비정기적 현금흐름에 대한 내부수익률(XIRR) 계산
    scipy.optimize.newton을 사용하여 해를 찾음
    """
    if len(cash_flows) != len(dates):
        return None

    def xnpv(rate, flows, dates):
        # rate가 -100% 이하면 계산 불가
        if rate <= -1.0: return float('inf')

        # 시작일 기준 경과일(days) 계산
        min_date = min(dates)

        # 합계: Flow / (1+r)^(일수/365)
        return sum([cf / (1 + rate) ** ((d - min_date).days / 365.0) for cf, d in zip(flows, dates)])

    try:
        # 초기 추정값 0.1 (10%)로 시작하여 해 찾기
        return optimize.newton(lambda r: xnpv(r, cash_flows, dates), 0.1)
    except (RuntimeError, OverflowError, ZeroDivisionError):
        return None


# 4. Main Logic
def calculate_metrics() -> pd.DataFrame:
    """
    성과 지표 계산 메인 함수
    Input: 04Daily_Asset_Ledger.csv
    Output: 05Performance_Data.csv
    """
    print(f"🚀 {MODULE_TAG} 성과 지표(TWR, MWR, MDD) 계산 시작...")

    # 1. 데이터 로드
    path_ledger = config.PROCESSED_DIR / config.PROCESSED_FILES['ledger']
    if not path_ledger.exists():
        print(f"❌ {MODULE_TAG} 원장 파일(04)이 없습니다. ledger.py를 먼저 실행하세요.")
        return pd.DataFrame()

    df = local_io.load_csv(path_ledger)

    # 날짜 변환 및 정렬
    if 'Date' not in df.columns:
        print(f"❌ {MODULE_TAG} 원장에 Date 컬럼이 없습니다.")
        return pd.DataFrame()

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')

    # ---------------------------------------------------------
    # A. TWR (시간가중수익률) 계산
    # ---------------------------------------------------------
    # 공식: r = (End - (Start + Flow)) / (Start + Flow)

    # 전일 자산 (Start Value)
    df['Prev_Asset'] = df['Calculated_Asset'].shift(1)

    # 첫날 처리: 전일 자산이 없으므로, 당일 자산에서 Flow를 뺀 값을 기초자산으로 추정
    # (또는 첫날 수익률을 0으로 처리)
    df.loc[df.index[0], 'Prev_Asset'] = df.loc[df.index[0], 'Calculated_Asset'] - df.loc[df.index[0], 'External_Flow']

    # 분모 = 기초자산 + 당일 유입액
    # (가정: 자금 유입은 장 시작 전에 이루어졌다고 간주하여 운용 수익에 기여함)
    denominator = df['Prev_Asset'] + df['External_Flow']

    # 일별 수익률 계산 (0 나누기 방지)
    df['Daily_Return'] = 0.0
    mask = denominator != 0
    df.loc[mask, 'Daily_Return'] = (df.loc[mask, 'Calculated_Asset'] / denominator[mask]) - 1

    # 첫날 수익률 0% 처리 (데이터 시작점)
    df.loc[df.index[0], 'Daily_Return'] = 0.0

    # 누적 수익률 (Chain-linking)
    # (1+r1) * (1+r2) * ... - 1
    df['Cumulative_TWR'] = (1 + df['Daily_Return']).cumprod() - 1

    # ---------------------------------------------------------
    # B. MDD (최대 낙폭) 계산
    # ---------------------------------------------------------
    # 역대 최고 자산(Peak) 갱신 (Flow가 섞여있어 정확한 MDD는 아니지만, 자산 규모 기준 MDD)
    # *엄밀한 MDD는 누적수익률 곡선 기준이어야 함* -> TWR 기준으로 변경

    df['Peak_TWR'] = df['Cumulative_TWR'].cummax()

    # Peak가 -100% 등 비정상일 경우 대비
    # Drawdown = (Current - Peak) / (1 + Peak)  <-- 수익률 기준 낙폭 공식
    # 편의상 자산 기준이 아닌 '누적 수익 지수(Wealth Index)' 기준으로 계산

    wealth_index = (1 + df['Daily_Return']).cumprod()
    peak_index = wealth_index.cummax()
    df['Drawdown'] = (wealth_index - peak_index) / peak_index

    current_mdd = df['Drawdown'].min()

    # ---------------------------------------------------------
    # C. MWR (금액가중수익률 / XIRR) 계산
    # ---------------------------------------------------------
    # XIRR 관점:
    # - 투자자 입장에서 돈을 넣음(Flow > 0) -> 현금 유출 (-)
    # - 투자자 입장에서 돈을 뺌(Flow < 0) -> 현금 유입 (+)

    flows = (-df['External_Flow']).tolist()  # 부호 반전
    dates = df['Date'].tolist()

    # 초기값: 첫날 기초 자산만큼 투자했다고 가정
    # 첫날 External_Flow가 이미 처리되었을 수 있으므로 확인 필요
    # 원장의 첫날 Calculated_Asset은 이미 초기 투자금이 반영된 상태
    # 따라서 첫날 Flow를 강제로 -Calculated_Asset으로 설정하는 것이 가장 깔끔함 (잔고 기반 XIRR)

    # [방식]
    # t=0: -기초잔고
    # t=1~n-1: -중간Flow (입금은 마이너스, 출금은 플러스)
    # t=n: +기말잔고

    xirr_flows = flows.copy()

    # 첫날 보정: 첫날의 자산 잔고 전체를 투자한 것으로 간주
    # (주의: 첫날 Flow가 중복 계산되지 않도록 처리)
    xirr_flows[0] = -df.iloc[0]['Calculated_Asset']

    # 중간 날짜들의 Flow는 이미 `flows` 리스트에 (-External_Flow)로 들어가 있음.
    # 단, 첫날의 Flow는 위에서 잔고 전체로 덮어썼으므로 무시됨 (OK)

    # 마지막날 보정: 현재 잔고를 전액 회수(매도)한 것으로 간주 (+)
    # 마지막날의 Flow 효과는? -> 마지막날 입금 후 종료했다면?
    # XIRR에서는 마지막날 잔고(Calculated_Asset) 자체가 최종 가치이므로
    # 마지막날 Flow는 무시하고 잔고만 더해주는 게 맞음.
    xirr_flows[-1] = df.iloc[-1]['Calculated_Asset']

    # 0이 아닌 현금흐름만 추출 (계산 속도 및 에러 방지)
    xirr_data = [(f, d) for f, d in zip(xirr_flows, dates) if abs(f) > 1.0 or d == dates[-1] or d == dates[0]]

    mwr_val = None
    if xirr_data:
        x_flows, x_dates = zip(*xirr_data)
        mwr_val = _calculate_xirr(x_flows, x_dates)

    # ---------------------------------------------------------
    # D. 저장 및 리포트
    # ---------------------------------------------------------
    save_path = config.PROCESSED_DIR / config.PROCESSED_FILES['performance']
    local_io.save_csv(df, save_path)

    # 결과 출력
    last_twr = df['Cumulative_TWR'].iloc[-1] * 100
    mwr_str = f"{mwr_val * 100:.2f}%" if mwr_val else "계산 실패 (데이터 부족 등)"
    mdd_str = f"{current_mdd * 100:.2f}%"

    print(f"✅ {MODULE_TAG} 성과 분석 완료")
    print(f"📊 [TWR] 누적 수익률: {last_twr:>7.2f}% (운용 실력)")
    print(f"💰 [MWR] 연평균 수익률: {mwr_str:>8} (체감 수익)")
    print(f"📉 [MDD] 최대 낙폭:     {mdd_str:>8} (위험 지표)")

    return df


# 5. Execution Block
def main():
    calculate_metrics()

if __name__ == "__main__":
    main()