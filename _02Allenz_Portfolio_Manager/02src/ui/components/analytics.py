"""
@Title: Analytics Component
@Description: 성과 분석 및 벤치마크 비교 화면을 렌더링합니다. (동적 리베이싱 포함)
@Author: Allen & Gemini
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from scipy import optimize

# 1. Constants
MODULE_TAG = "[UI: Analytics]"

# 2. Helper Functions
def _calculate_xirr(cash_flows: list, dates: list) -> float:
    """선택된 기간에 대한 내부수익률(XIRR)을 동적으로 계산합니다."""
    if len(cash_flows) < 2: return 0.0
    def xnpv(rate, flows, dates):
        if rate <= -1.0: return float('inf')
        min_date = min(dates)
        return sum([cf / (1 + rate) ** ((d - min_date).days / 365.0) for cf, d in zip(flows, dates)])
    try:
        return optimize.newton(lambda r: xnpv(r, cash_flows, dates), 0.1)
    except:
        return 0.0

def _rebase_data(df_perf: pd.DataFrame, df_bench: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp):
    """선택된 기간에 맞춰 수익률을 0%부터 다시 계산(Rebasing)합니다."""
    # 1. 기간 필터링
    mask_perf = (df_perf['Date'] >= start_date) & (df_perf['Date'] <= end_date)
    p_df = df_perf.loc[mask_perf].copy()

    mask_bench = (df_bench['Date'] >= start_date) & (df_bench['Date'] <= end_date)
    b_df = df_bench.loc[mask_bench].copy()

    if p_df.empty or b_df.empty:
        return p_df, b_df

    # 2. 내 포트폴리오 리베이싱 (TWR & MDD)
    # 시작일의 Daily_Return을 0으로 간주하여 해당 기간의 누적 수익률 재계산
    p_df['Period_TWR'] = (1 + p_df['Daily_Return']).cumprod() - 1

    wealth_index = (1 + p_df['Daily_Return']).cumprod()
    peak_index = wealth_index.cummax()
    p_df['Period_Drawdown'] = (wealth_index - peak_index) / peak_index

    # 3. 벤치마크 리베이싱
    first_spy = b_df['SPY'].iloc[0]
    first_qqq = b_df['QQQ'].iloc[0]
    first_iwm = b_df['IWM'].iloc[0]

    b_df['SPY_TWR'] = (b_df['SPY'] / first_spy) - 1
    b_df['QQQ_TWR'] = (b_df['QQQ'] / first_qqq) - 1
    b_df['IWM_TWR'] = (b_df['IWM'] / first_iwm) - 1

    return p_df, b_df

# 3. Main Logic
def render_page(df_perf: pd.DataFrame, df_bench: pd.DataFrame):
    """성과 분석 화면 렌더링"""
    st.header("📈 성과 분석 & 벤치마크")
    st.markdown("---")

    if df_perf.empty or df_bench.empty:
        st.warning("데이터가 부족합니다. 파이프라인 엔진을 먼저 실행해 주세요.")
        return

    # --- [Top] 컨트롤 패널 ---
    min_date = df_perf['Date'].min().date()
    max_date = df_perf['Date'].max().date()

    col_date, _ = st.columns([1, 2])
    with col_date:
        selected_dates = st.date_input(
            "📅 분석 기간 선택",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )

    if len(selected_dates) != 2:
        st.info("종료일을 선택해 주세요.")
        return

    start_date, end_date = pd.to_datetime(selected_dates[0]), pd.to_datetime(selected_dates[1])

    # 데이터 리베이싱 (선택 기간에 맞춤)
    p_df, b_df = _rebase_data(df_perf, df_bench, start_date, end_date)

    if p_df.empty:
        st.warning("선택한 기간에 데이터가 없습니다.")
        return

    # --- [Middle] 4대 KPI 카드 ---
    # 지표 계산
    period_twr = p_df['Period_TWR'].iloc[-1] * 100
    period_mdd = p_df['Period_Drawdown'].min() * 100
    period_spy = b_df['SPY_TWR'].iloc[-1] * 100
    alpha = period_twr - period_spy

    # MWR(XIRR) 계산용 현금흐름
    flows = (-p_df['External_Flow']).tolist()
    dates = p_df['Date'].tolist()
    flows[0] = -p_df.iloc[0]['Calculated_Asset'] # 시작 자산
    flows[-1] = p_df.iloc[-1]['Calculated_Asset'] # 종료 자산
    period_mwr = _calculate_xirr(flows, dates) * 100

    st.markdown("### 📊 구간 성과 요약")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    # Streamlit은 delta 값이 양수면 초록색, 음수면 빨간색을 자동 지원합니다. (미국식)
    with kpi1:
        st.metric("📈 시간 가중 수익률 (TWR)", f"{period_twr:.2f}%", delta=f"{period_twr:.2f}%")
    with kpi2:
        st.metric("💰 금액 가중 수익률 (MWR)", f"{period_mwr:.2f}%", delta=f"{period_mwr:.2f}%")
    with kpi3:
        st.metric("📉 최대 낙폭 (MDD)", f"{period_mdd:.2f}%", delta=f"{period_mdd:.2f}%", delta_color="inverse")
    with kpi4:
        st.metric("🥊 초과 수익 (vs S&P500)", f"{alpha:.2f}%p", delta=f"{alpha:.2f}%p")

    st.markdown("---")

    # --- [Bottom] 심층 분석 차트 (3분할 탭) ---
    tab1, tab2, tab3 = st.tabs(["📊 자산 & 현금 흐름", "🥊 벤치마크 비교", "🌊 리스크 (Drawdown)"])

    # 병합된 데이터를 기준으로 차트를 그림
    df_merged = pd.merge(p_df, b_df, on='Date', how='left')

    with tab1:
        st.subheader("순자산 성장 추이 및 입출금")
        fig1 = go.Figure()
        # 자산 면적 차트
        fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df['Calculated_Asset'], fill='tozeroy',
                                  mode='lines', name='순자산', line=dict(color='#3498db')))
        # 현금 흐름 막대 차트 (보조 축 사용 없이 크기 스케일만 맞춤)
        fig1.add_trace(go.Bar(x=p_df['Date'], y=p_df['External_Flow'], name='입출금(Flow)', marker_color='#f1c40f'))
        fig1.update_layout(height=400, hovermode='x unified', margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("내 포트폴리오 vs 시장 지수")

        fig2 = go.Figure()
        # 내 포트폴리오 (두꺼운 선)
        fig2.add_trace(go.Scatter(x=df_merged['Date'], y=df_merged['Period_TWR']*100,
                                  mode='lines', name='내 포트폴리오', line=dict(color='#2ecc71', width=3)))
        # 벤치마크 (얇은 선)
        fig2.add_trace(go.Scatter(x=df_merged['Date'], y=df_merged['SPY_TWR']*100,
                                  mode='lines', name='S&P 500 (SPY)', line=dict(color='#95a5a6', width=1.5)))
        fig2.add_trace(go.Scatter(x=df_merged['Date'], y=df_merged['QQQ_TWR']*100,
                                  mode='lines', name='Nasdaq 100 (QQQ)', line=dict(color='#f39c12', width=1.5)))
        fig2.add_trace(go.Scatter(x=df_merged['Date'], y=df_merged['IWM_TWR']*100,
                                  mode='lines', name='Russell 2000 (IWM)', line=dict(color='#9b59b6', width=1.5)))

        fig2.update_layout(height=450, hovermode='x unified', yaxis_title="수익률 (%)", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("구간 내 최대 낙폭 분석")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=p_df['Date'], y=p_df['Period_Drawdown']*100, fill='tozeroy',
                                  mode='lines', name='Drawdown', line=dict(color='#e74c3c')))
        fig3.update_layout(height=400, hovermode='x unified', yaxis_title="낙폭 (%)", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig3, use_container_width=True)