import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# 1. 설정 및 경로 잡기 (Basic Setup)
# --------------------------------------------------------------------------
# 페이지 기본 설정 (제목, 아이콘, 레이아웃)
st.set_page_config(
    page_title="Allenz Portfolio",
    page_icon="📈",
    layout="wide"
)

# 데이터 파일 경로 설정
# 현재 파일(app.py)의 상위(ui)의 상위(02src)의 상위(Project)에서 01DATA/processed로 이동
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "01DATA" / "processed"
PERF_FILE = DATA_DIR / "05Performance_Data.csv"


# --------------------------------------------------------------------------
# 2. 데이터 로드 함수 (Data Loader)
# --------------------------------------------------------------------------
@st.cache_data  # 데이터를 매번 읽지 않고 캐싱해서 속도를 높임
def load_data():
    if not PERF_FILE.exists():
        st.error(f"데이터 파일이 없습니다: {PERF_FILE}")
        return pd.DataFrame()

    df = pd.read_csv(PERF_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    return df


# 데이터 불러오기
df = load_data()

if df.empty:
    st.stop()  # 데이터 없으면 멈춤

# --------------------------------------------------------------------------
# 3. 사이드바 (Sidebar) - 컨트롤 패널
# --------------------------------------------------------------------------
st.sidebar.title("🎮 Control Panel")

# 날짜 필터링 기능
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

start_date, end_date = st.sidebar.date_input(
    "조회 기간 선택",
    [min_date, max_date],  # 기본값: 전체 기간
    min_value=min_date,
    max_value=max_date
)

# 선택한 날짜로 데이터 자르기 (Slicing)
mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
filtered_df = df.loc[mask]

# --------------------------------------------------------------------------
# 4. 메인 화면 (Main Dashboard)
# --------------------------------------------------------------------------
st.title("💰 Allenz Portfolio Manager")
st.markdown("---")  # 구분선

# (1) 최상단 요약 지표 (KPI Cards)
# 가장 최근 데이터 가져오기
latest = filtered_df.iloc[-1]
initial = filtered_df.iloc[0]

# 컬럼 3개로 나누기
col1, col2, col3 = st.columns(3)

with col1:
    # 현재 자산
    cur_asset = latest['Calculated_Asset']
    st.metric(
        label="현재 순자산 (Net Asset)",
        value=f"{cur_asset:,.0f} 원",
        delta=f"{cur_asset - initial['Calculated_Asset']:,.0f} 원 (기간 변동)"
    )

with col2:
    # 누적 수익률 (TWR)
    twr = latest['Cumulative_TWR'] * 100
    st.metric(
        label="누적 수익률 (TWR)",
        value=f"{twr:.2f} %",
        delta_color="normal"  # 빨강/파랑 자동 색상
    )

with col3:
    # 최대 낙폭 (MDD) - 기간 내 최저점
    mdd = filtered_df['Drawdown'].min() * 100
    st.metric(
        label="최대 낙폭 (MDD)",
        value=f"{mdd:.2f} %",
        delta="Risk Factor",
        delta_color="inverse"  # 낮을수록 좋음 (녹색 표시)
    )

st.markdown("---")

# (2) 메인 차트 그리기
st.subheader("📈 자산 성장 & 수익률 추이")

# 탭을 나눠서 보여주기
tab1, tab2 = st.tabs(["자산(Asset)", "수익률(TWR)"])

with tab1:
    # 자산 그래프 (Area Chart)
    chart_data = filtered_df.set_index('Date')[['Calculated_Asset']]
    st.line_chart(chart_data, color="#2980b9")  # 파란색

with tab2:
    # 수익률 그래프 (Line Chart)
    twr_data = filtered_df.set_index('Date')[['Cumulative_TWR']]
    st.line_chart(twr_data, color="#e74c3c")  # 빨간색

# (3) 데이터 테이블 (접었다 폈다 기능)
with st.expander("📊 상세 데이터 보기 (Click to expand)"):
    st.dataframe(filtered_df.style.format({
        'Calculated_Asset': '{:,.0f}',
        'Cumulative_TWR': '{:.2%}',
        'Drawdown': '{:.2%}'
    }))