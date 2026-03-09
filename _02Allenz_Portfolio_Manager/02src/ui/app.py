"""
@Title: Portfolio Manager Main UI
@Description: Streamlit 대시보드의 메인 실행 파일. 좌측 메뉴 렌더링 및 페이지 전환을 담당합니다.
@Author: Allen & Gemini
"""

# 1. Imports
import sys
import pandas as pd
import streamlit as st
from pathlib import Path

# 상위 디렉토리(02src) 참조 설정
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config
from data_loaders import io as local_io

# 우리가 만든 UI 컴포넌트 불러오기 (+ data_manager 추가)
from components import portfolio, analytics, history_tab, data_manager

# 2. Constants & Page Config
st.set_page_config(
    page_title="Allenz Portfolio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# 3. Helper Functions (Data Loader)
@st.cache_data
def load_all_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """모든 정제된 데이터를 로드하고 날짜 형식을 맞춥니다. 파일이 없으면 빈 데이터를 반환합니다."""

    # 1. 파일이 없으면 FileNotFoundError를 무시하고 빈 데이터프레임 할당
    try:
        df_perf = local_io.load_csv(config.PROCESSED_DIR / "05Performance_Data.csv")
    except FileNotFoundError:
        df_perf = pd.DataFrame()

    try:
        df_bench = local_io.load_csv(config.PROCESSED_DIR / "06Benchmark_Data.csv")
    except FileNotFoundError:
        df_bench = pd.DataFrame()

    try:
        df_full = local_io.load_csv(config.PROCESSED_DIR / "03Full_Portfolio.csv")
    except FileNotFoundError:
        df_full = pd.DataFrame()

    try:
        df_history = local_io.load_csv(config.PROCESSED_DIR / "07Historical_Holdings.csv")
    except FileNotFoundError:
        df_history = pd.DataFrame()

    # 2. 날짜 컬럼 Datetime 변환 (빈 데이터프레임이 아닐 때만 수행)
    if not df_perf.empty and 'Date' in df_perf.columns:
        df_perf['Date'] = pd.to_datetime(df_perf['Date'])
    if not df_bench.empty and 'Date' in df_bench.columns:
        df_bench['Date'] = pd.to_datetime(df_bench['Date'])
    if not df_history.empty and 'Date' in df_history.columns:
        df_history['Date'] = pd.to_datetime(df_history['Date'])

    return df_perf, df_bench, df_full, df_history

# 4. Main Logic
def main():
    """메인 라우팅 로직"""
    df_perf, df_bench, df_full, df_history = load_all_data()

    # --- Sidebar: Navigation Menu ---
    st.sidebar.title("🧭 Navigation")
    menu = st.sidebar.radio(
        "메뉴 이동",
        [
            "🏠 내 포트폴리오 (Current)",
            "📈 성과 분석 & 벤치마크 (Metrics)",
            "🕰️ 포트폴리오 스냅샷 (Historical Holdings)",
            "⚙️ 데이터 관리 (Data Manager)"  # [NEW] 데이터 업로드 탭 추가
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Allenz Portfolio Manager v1.0.0")

    # --- Page Routing ---
    if menu == "🏠 내 포트폴리오 (Current)":
        if not df_full.empty:
            portfolio.render_page(df_full)
        else:
            st.warning("데이터가 없습니다. '데이터 관리' 탭에서 파일을 업로드해주세요.")

    elif menu == "📈 성과 분석 & 벤치마크 (Metrics)":
        if not df_perf.empty and not df_bench.empty:
            analytics.render_page(df_perf, df_bench)
        else:
            st.warning("데이터가 없습니다. '데이터 관리' 탭에서 파일을 업로드해주세요.")

    elif menu == "🕰️ 포트폴리오 스냅샷 (Historical Holdings)":
        if not df_history.empty:
            history_tab.render_page(df_history)
        else:
            st.warning("데이터가 없습니다. '데이터 관리' 탭에서 파일을 업로드해주세요.")

    elif menu == "⚙️ 데이터 관리 (Data Manager)":
        data_manager.render() # data_manager는 함수명이 render()로 되어 있으므로 이대로 호출

# 5. Execution Block
if __name__ == "__main__":
    main()