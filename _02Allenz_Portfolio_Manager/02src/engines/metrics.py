"""
@Title: Performance Metrics Engine
@Description: 일별 자산 원장(04)을 기반으로 TWR(시간가중), MWR(금액가중/XIRR), MDD(최대낙폭),
              Sharpe/Sortino/Calmar/IR(정보비율)/Beta/Alpha(CAPM, SPY 기준)를 계산하는 엔진
@Author: Allen & Gemini
@Date: 2026-02-14
@Updated: 2026-05-07 — Risk-Adjusted Metrics 섹션(E) 추가
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
def _calculate_xirr(cash_flows: list, dates: list) -> float | None:
    """
    비정기적 현금흐름에 대한 내부수익률(XIRR) 계산
    1차 솔버: scipy.optimize.brentq (bracket: -0.999 ~ 100.0)
    2차 솔버: scipy.optimize.newton (fallback, 초기값 0.1)

    엣지케이스:
      - 현금흐름 부호가 모두 동일 → 수학적으로 해 없음 (None 반환)
      - 기간이 1일뿐 (날짜가 모두 동일) → 단순 수익률로 대체
    """
    if len(cash_flows) != len(dates):
        return None

    # 엣지케이스 (1): 현금흐름 부호가 모두 동일 → XIRR 해 존재 불가
    non_zero = [cf for cf in cash_flows if cf != 0]
    if non_zero and (all(cf > 0 for cf in non_zero) or all(cf < 0 for cf in non_zero)):
        return None

    # 엣지케이스 (2): 날짜가 모두 동일 (기간 0일) → 단순 수익률로 대체
    if len(set(dates)) == 1:
        inflow = sum(cf for cf in cash_flows if cf > 0)
        outflow = abs(sum(cf for cf in cash_flows if cf < 0))
        return (inflow / outflow - 1) if outflow != 0 else None

    def xnpv(rate, flows, dates):
        # rate가 -100% 이하면 계산 불가
        if rate <= -1.0:
            return float('inf')
        min_date = min(dates)
        return sum([cf / (1 + rate) ** ((d - min_date).days / 365.0) for cf, d in zip(flows, dates)])

    try:
        # 1차 솔버: brentq (bracket: -0.999 ~ 100.0)
        return optimize.brentq(lambda r: xnpv(r, cash_flows, dates), -0.999, 100.0)
    except ValueError:
        try:
            # 2차 솔버: newton (fallback, 초기값 0.1)
            return optimize.newton(lambda r: xnpv(r, cash_flows, dates), 0.1)
        except (RuntimeError, OverflowError, ZeroDivisionError):
            return None
    except (OverflowError, ZeroDivisionError):
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
    # Wealth Index = (1+r1)*(1+r2)*... : Flow 영향을 제거한 순수 운용 성과 지수
    # 자산 잔고 기준 MDD는 입출금으로 인해 왜곡되므로 Wealth Index 기준이 엄밀함

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
    # D. Risk-Adjusted Performance Metrics
    # ---------------------------------------------------------
    # 무위험이자율 (연환산, 소수)
    from data_loaders.fred import get_risk_free_rate
    rf_annual = get_risk_free_rate()

    cal_days = (df['Date'].iloc[-1] - df['Date'].iloc[0]).days  # 실제 역일(calendar day) 수

    # ── 월별 수익률 집계 (변동성 계산 기준 단위) ──────────────
    # 데이터 그래뉼래러티 이유:
    # 원장이 월별 Anchor 포인트(~18개) 기반 직선 보간으로 생성되어 있어
    # 일별 수익률은 기간 내 균등 배분된 합성값(daily_gain/prev_asset)임.
    # 일별 σ≈0.0023(연환산 3.7%)으로 과소 추정되어 Sharpe가 7배 이상 과대계상됨.
    # 실질 변동성은 Anchor 포인트 단위인 월별 수익률로만 정확히 측정 가능.
    df['_YM'] = df['Date'].dt.to_period('M')
    monthly_r = (
        df.groupby('_YM')['Daily_Return']
        .apply(lambda g: (1 + g).prod() - 1)
    )
    df.drop(columns=['_YM'], inplace=True)

    n_months = len(monthly_r)

    # CAGR (Wealth Index 기반 연환산 수익률 — 전체 기간 사용)
    final_wealth = (1 + df['Daily_Return']).prod()
    cagr = (final_wealth ** (365.0 / cal_days) - 1) if cal_days > 0 else None

    # 연환산 표준편차 (월별 σ × √12 — 월 Anchor 데이터에 적합)
    ann_std = monthly_r.std(ddof=1) * np.sqrt(12) if n_months > 1 else None

    # trading_returns: 일별 zero-return 제외 (첫날 등 처리용 — MDD·Beta 등 다른 계산에 활용)
    trading_returns = df.loc[df['Date'].dt.dayofweek < 5, 'Daily_Return']
    trading_returns = trading_returns[trading_returns != 0.0]
    n_days = len(trading_returns)

    # ── Sharpe Ratio ──────────────────────────────────────────
    # (CAGR - Rf) / σ_annualized  [월별 변동성 기반]
    if cagr is not None and ann_std and ann_std != 0:
        sharpe = (cagr - rf_annual) / ann_std
    else:
        sharpe = None

    # ── Sortino Ratio ─────────────────────────────────────────
    # (CAGR - Rf) / σ_downside_annualized  [하락 월만 사용, 월별 기반]
    neg_monthly = monthly_r[monthly_r < 0]
    if len(neg_monthly) > 1:
        downside_std = neg_monthly.std(ddof=1) * np.sqrt(12)
        sortino = (cagr - rf_annual) / downside_std if (cagr is not None and downside_std != 0) else None
    else:
        downside_std = None
        sortino = None

    # ── Calmar Ratio ──────────────────────────────────────────
    # CAGR / |MDD|
    if cagr is not None and current_mdd and current_mdd != 0:
        calmar = cagr / abs(current_mdd)
    else:
        calmar = None

    # ── Benchmark (SPY) 로드 및 정렬 ─────────────────────────
    path_bench = config.PROCESSED_DIR / config.PROCESSED_FILES['benchmark']
    info_ratio = beta_spy = alpha_spy = None
    rb_cagr    = None

    if path_bench.exists():
        bench_df = local_io.load_csv(path_bench)
        bench_df['Date']       = pd.to_datetime(bench_df['Date'])
        bench_df               = bench_df[['Date', 'SPY']].dropna()
        bench_df['SPY_Return'] = bench_df['SPY'].pct_change()

        # 포트폴리오 일별 수익률과 날짜 기준 inner join
        merged = pd.merge(
            df[['Date', 'Daily_Return']],
            bench_df[['Date', 'SPY_Return']],
            on='Date', how='inner'
        ).dropna()

        MIN_OBS = 30  # 최소 관측치 기준 (통계적 신뢰 하한)
        if len(merged) >= MIN_OBS:
            rp_series = merged['Daily_Return']
            rb_series = merged['SPY_Return']

            # 벤치마크 CAGR (SPY, 정렬된 구간 기준)
            bench_cal_days = (merged['Date'].iloc[-1] - merged['Date'].iloc[0]).days
            bench_wealth   = (1 + rb_series).prod()
            rb_cagr = (bench_wealth ** (365.0 / bench_cal_days) - 1) if bench_cal_days > 0 else None

            # ── Beta (CAPM 회귀: 월별 수익률 기반) ─────────────
            # 근거: 일별 원장이 선형 보간(monthly anchor)으로 생성되어
            #       Cov(일별 Rp, 일별 SPY) ≈ 0 — Sharpe/Sortino와 동일한 왜곡 원인.
            #       Anchor 포인트 단위인 월별 수익률로만 실제 공분산 측정 가능.
            bench_df['_YM'] = bench_df['Date'].dt.to_period('M')
            monthly_rb = (
                bench_df.dropna(subset=['SPY_Return'])
                .groupby('_YM')['SPY_Return']
                .apply(lambda g: (1 + g).prod() - 1)
            )
            bench_df.drop(columns=['_YM'], inplace=True)

            # 포트폴리오 월별(monthly_r)과 벤치마크 월별 inner join
            monthly_merged_beta = pd.DataFrame({
                'rp': monthly_r,
                'rb': monthly_rb
            }).dropna()

            MIN_MONTHS = 6  # 통계적 신뢰 최소 관측치 (월 기준)
            if len(monthly_merged_beta) >= MIN_MONTHS:
                rp_m     = monthly_merged_beta['rp']
                rb_m     = monthly_merged_beta['rb']
                var_rb_m = rb_m.var(ddof=1)
                if var_rb_m and var_rb_m != 0:
                    cov_m    = np.cov(rp_m.values, rb_m.values, ddof=1)
                    beta_spy = cov_m[0, 1] / var_rb_m
                else:
                    beta_spy = None
            else:
                beta_spy = None
                print(f"⚠️ {MODULE_TAG} 월별 정렬 후 관측치 {len(monthly_merged_beta)}개월 "
                      f"— Beta 계산 생략 (최소 {MIN_MONTHS}개월 필요)")

            # ── Alpha (Jensen's Alpha: 연환산) ────────────────
            # α = CAGR_portfolio - [Rf + β × (CAGR_benchmark - Rf)]
            if cagr is not None and beta_spy is not None and rb_cagr is not None:
                alpha_spy = cagr - (rf_annual + beta_spy * (rb_cagr - rf_annual))
            else:
                alpha_spy = None

            # ── Information Ratio ─────────────────────────────
            # (CAGR_portfolio - CAGR_benchmark) / Tracking_Error
            # Tracking Error = σ(일별 초과수익) × √252
            excess_daily = rp_series.values - rb_series.values
            te = np.std(excess_daily, ddof=1) * np.sqrt(252)
            if te and te != 0 and cagr is not None and rb_cagr is not None:
                info_ratio = (cagr - rb_cagr) / te
            else:
                info_ratio = None
        else:
            print(f"⚠️ {MODULE_TAG} 벤치마크 정렬 후 관측치 {len(merged)}개 — Beta/Alpha/IR 계산 생략 (최소 {MIN_OBS}개 필요)")
    else:
        print(f"⚠️ {MODULE_TAG} 벤치마크 파일(06) 없음 — Beta/Alpha/IR 계산 생략")

    # 스칼라 지표를 전 행에 상수 컬럼으로 저장 (CSV 조회 편의)
    df['CAGR']         = cagr
    df['Sharpe_Ratio'] = sharpe
    df['Sortino_Ratio']= sortino
    df['Calmar_Ratio'] = calmar
    df['Info_Ratio']   = info_ratio
    df['Beta_SPY']     = beta_spy
    df['Alpha_SPY']    = alpha_spy

    # ---------------------------------------------------------
    # E. 저장 및 리포트
    # ---------------------------------------------------------
    save_path = config.PROCESSED_DIR / config.PROCESSED_FILES['performance']
    local_io.save_csv(df, save_path)

    # ── 출력 헬퍼 ────────────────────────────────────────────
    def _fmt_ratio(val: float | None) -> str:
        return f"{val:>8.4f}" if val is not None else "     계산 불가"

    def _fmt_pct(val: float | None) -> str:
        return f"{val * 100:>7.2f}%" if val is not None else "    계산 불가"

    # 결과 출력
    last_twr = df['Cumulative_TWR'].iloc[-1] * 100
    mwr_str  = f"{mwr_val * 100:.2f}%" if mwr_val else "계산 실패 (데이터 부족 등)"
    mdd_str  = f"{current_mdd * 100:.2f}%"

    print(f"✅ {MODULE_TAG} 성과 분석 완료")
    print(f"─" * 52)
    print(f"📊 [TWR]    누적 수익률:   {last_twr:>7.2f}% (운용 실력)")
    print(f"📈 [CAGR]   연환산 수익률: {_fmt_pct(cagr):>8} (복리 성장률)")
    print(f"💰 [MWR]    연평균 수익률: {mwr_str:>8} (체감 수익)")
    print(f"📉 [MDD]    최대 낙폭:     {mdd_str:>8} (위험 지표)")
    print(f"─" * 52)
    print(f"⚡ [Sharpe]  Sharpe Ratio: {_fmt_ratio(sharpe)} (초과수익/총변동  | Rf={rf_annual:.2%})")
    print(f"⚡ [Sortino] Sortino Ratio:{_fmt_ratio(sortino)} (초과수익/하방변동)")
    print(f"⚡ [Calmar]  Calmar Ratio: {_fmt_ratio(calmar)} (CAGR / |MDD|)")
    print(f"─" * 52)
    print(f"📌 [IR]     Info. Ratio:   {_fmt_ratio(info_ratio)} (초과수익/TE, SPY 기준)")
    print(f"📌 [Beta]   Beta (SPY):    {_fmt_ratio(beta_spy)}")
    print(f"📌 [Alpha]  Alpha (SPY):   {_fmt_pct(alpha_spy):>8} (Jensen's α, 연환산)")

    return df


# 5. Execution Block
def main():
    calculate_metrics()

if __name__ == "__main__":
    main()