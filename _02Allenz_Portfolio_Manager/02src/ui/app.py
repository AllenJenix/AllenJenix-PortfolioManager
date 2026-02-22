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

# 우리가 만든 UI 컴포넌트 3대장 불러오기
from components import portfolio, analytics, history_tab

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
    """모든 정제된 데이터를 로드하고 날짜 형식을 맞춥니다."""
    df_perf = local_io.load_csv(config.PROCESSED_DIR / "05Performance_Data.csv")
    df_bench = local_io.load_csv(config.PROCESSED_DIR / "06Benchmark_Data.csv")
    df_full = local_io.load_csv(config.PROCESSED_DIR / "03Full_Portfolio.csv")
    df_history = local_io.load_csv(config.PROCESSED_DIR / "07Historical_Holdings.csv") # [NEW] 타임머신 데이터

    # 날짜 컬럼 Datetime 변환
    if not df_perf.empty:
        df_perf['Date'] = pd.to_datetime(df_perf['Date'])
    if not df_bench.empty:
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
            "🕰️ 역사적 스냅샷 (Time Machine)" # [NEW] 3번째 탭
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Allenz Portfolio Manager v1.0.0")

    # --- Page Routing ---
    if menu == "🏠 내 포트폴리오 (Current)":
        portfolio.render_page(df_full)
    elif menu == "📈 성과 분석 & 벤치마크 (Metrics)":
        analytics.render_page(df_perf, df_bench)
    elif menu == "🕰️ 역사적 스냅샷 (Time Machine)":
        history_tab.render_page(df_history)

# 5. Execution Block
if __name__ == "__main__":
    main()