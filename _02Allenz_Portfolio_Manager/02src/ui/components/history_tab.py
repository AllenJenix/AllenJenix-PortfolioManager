"""
@Title: Historical Portfolio Snapshot Component
@Description: 과거 특정 일자의 포트폴리오 비중(주식+현금)을 슬라이더와 도넛 차트로 시각화합니다.
@Author: Allen & Gemini
"""

import pandas as pd
import streamlit as st
import plotly.express as px


def render_page(df_history: pd.DataFrame):
    st.header("🕰️ 포트폴리오 스냅샷 (Historical Holdings)")
    st.markdown("---")

    if df_history.empty:
        st.warning("타임머신 데이터가 없습니다. 먼저 엔진(history.py)을 실행해 주세요.")
        return

    # 1. 날짜 슬라이더 위젯 설정
    min_date = df_history['Date'].min().date()
    max_date = df_history['Date'].max().date()

    st.markdown("#### 📅 스냅샷 날짜 선택")
    selected_date = st.slider(
        "조회하고 싶은 과거의 날짜를 선택하세요:",
        min_value=min_date,
        max_value=max_date,
        value=max_date,  # 기본값은 가장 최근 날짜
        format="YYYY-MM-DD"
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 선택된 날짜의 데이터 추출 및 변환 (Wide -> Long)
    # 선택된 날짜와 일치하는 행 1개 추출
    day_row = df_history[df_history['Date'].dt.date == selected_date]

    if day_row.empty:
        st.info("해당 날짜의 데이터가 존재하지 않습니다.")
        return

    # 'Date' 컬럼 제외하고 Series로 변환
    day_data = day_row.drop(columns=['Date']).iloc[0]

    # 평가액이 0보다 큰 자산만 필터링 (보유하지 않았던 종목 숨김)
    day_data = day_data[day_data > 0].sort_values(ascending=False)

    if day_data.empty:
        st.warning("해당 날짜에는 보유 중인 자산이 없습니다.")
        return

    # 시각화를 위해 DataFrame으로 변환
    plot_df = pd.DataFrame({
        '자산명': day_data.index,
        '평가금액': day_data.values
    })

    # 비중(%) 계산
    total_asset = plot_df['평가금액'].sum()
    plot_df['비중'] = (plot_df['평가금액'] / total_asset) * 100

    # 3. 화면 분할 렌더링 (차트 & 요약)
    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.subheader(f"🍩 자산 비중 ({selected_date})")
        fig = px.pie(
            plot_df,
            values='평가금액',
            names='자산명',
            hole=0.4,
            hover_data=['비중']
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("💰 총 평가 자산")
        st.metric(label="Net Asset Value (KRW)", value=f"₩ {total_asset:,.0f}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 비중 요약")
        # 비중 문자열 포맷팅
        summary_df = plot_df[['자산명', '비중']].copy()
        summary_df['비중'] = summary_df['비중'].apply(lambda x: f"{x:.2f}%")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # 4. 상세 명세서 테이블
    st.markdown("---")
    st.subheader(f"📋 상세 자산 명세서")

    # 테이블 예쁘게 출력
    display_df = plot_df.copy()
    styled_df = display_df.style.format({
        '평가금액': '₩ {:,.0f}',
        '비중': '{:.2f}%'
    })
    st.dataframe(styled_df, use_container_width=True, hide_index=True)