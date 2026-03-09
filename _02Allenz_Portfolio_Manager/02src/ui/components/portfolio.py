"""
@Title: Portfolio Component
@Description: 현재 포트폴리오의 자산 배분(도넛 차트)과 상세 종목 정보를 렌더링합니다.
@Author: Allen & Gemini
"""

import pandas as pd
import streamlit as st
import plotly.express as px

# 1. Constants
MODULE_TAG = "[UI: Portfolio]"

# 2. Helper Functions
def _color_returns(val):
    """수익률에 따라 초록색(양수)과 빨간색(음수) 색상을 적용하는 스타일 함수"""
    if pd.isna(val):
        return ''
    try:
        val_float = float(str(val).replace('%', '').replace(',', ''))
        if val_float > 0:
            return 'color: #2ecc71; font-weight: bold;' # 미국식 상승(초록)
        elif val_float < 0:
            return 'color: #e74c3c; font-weight: bold;' # 미국식 하락(빨강)
        return 'color: gray;'
    except ValueError:
        return ''

# 3. Main Logic
def render_page(df_full: pd.DataFrame):
    """내 포트폴리오 화면 렌더링"""
    st.header("🏠 현재 포트폴리오 현황")
    st.markdown("---")

    if df_full.empty:
        st.warning("포트폴리오 데이터가 없습니다. 03Full_Portfolio.csv를 확인해주세요.")
        return

    # --- [Top] 최상단 요약 ---
    total_asset = df_full['평가금액'].sum()
    st.metric(label="💰 총 평가 자산 (Net Asset)", value=f"₩ {total_asset:,.0f}")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- [Middle] 자산 배분 시각화 ---
    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.subheader("🍩 자산 배분 (Asset Allocation)")
        fig = px.pie(
            df_full,
            values='평가금액',
            names='종목명',
            hole=0.4,
            hover_data=['보유비중']
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("📊 비중 요약 Top 5")
        summary_df = df_full.sort_values(by='보유비중', ascending=False).head(5)[['종목명', '보유비중']]
        summary_df['보유비중'] = summary_df['보유비중'].apply(lambda x: f"{x:.2f}%")
        st.dataframe(summary_df, width="stretch", hide_index=True)

    st.markdown("---")

    # --- [Bottom] 보유 종목 상세 명세서 ---
    st.subheader("📋 보유 종목 상세")

    display_cols = ['종목명', '구분', '잔고수량', '평균단가', '현재가', '평가금액', '수익률', '보유비중']
    display_df = df_full[display_cols].sort_values(by='평가금액', ascending=False)

    styled_df = display_df.style.format({
        '잔고수량': '{:,.2f}',
        '평균단가': '{:,.2f}',
        '현재가': '{:,.2f}',
        '평가금액': '{:,.0f}',
        '수익률': '{:.2f}%',
        '보유비중': '{:.2f}%'
    }).map(_color_returns, subset=['수익률'])

    st.dataframe(styled_df, width="stretch", hide_index=True)