"""
@Title: Benchmark Data Engine
@Description: 내 포트폴리오 성과 기간과 동일한 기간의 시장 지수(SPY, QQQ, IWM) 데이터를 수집하고 누적 수익률을 계산합니다.
@Author: Allen & Gemini
"""

# 1. Imports
import sys
import pandas as pd
import yfinance as yf
from pathlib import Path

# 상위 디렉토리(02src) 참조 설정
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
MODULE_TAG = "[Benchmark]"
TICKERS = {
    'S&P 500': 'SPY',
    'Nasdaq 100': 'QQQ',
    'Russell 2000': 'IWM'
}

# 3. Helper Functions
def _fetch_yahoo_data(ticker: str, start_date: str, end_date: str) -> pd.Series:
    """
    yfinance를 통해 특정 종목의 수정 종가를 수집합니다.
    안정성을 위해 download 대신 Ticker.history()를 사용합니다.
    """
    # yfinance는 end_date 당일을 제외하므로 하루를 더해줍니다.
    end_date_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    try:
        stock = yf.Ticker(ticker)
        # history()는 기본적으로 배당/액면분할이 자동 반영된(auto-adjusted) 데이터를 반환합니다.
        data = stock.history(start=start_date, end=end_date_dt.strftime('%Y-%m-%d'))

        if data.empty or 'Close' not in data.columns:
            return pd.Series(dtype='float64')

        # 'Close' 컬럼이 곧 수정 종가입니다.
        close_data = data['Close']
        return close_data

    except Exception as e:
        print(f"⚠️ {MODULE_TAG} {ticker} 수집 중 에러 발생: {e}")
        return pd.Series(dtype='float64')

# 4. Main Logic
def generate_benchmark_data() -> pd.DataFrame:
    """
    05Performance_Data.csv의 기간을 기준으로 벤치마크 데이터를 생성하고 병합합니다.
    """
    print(f"🚀 {MODULE_TAG} 벤치마크 데이터 수집 시작...")

    perf_file = config.PROCESSED_DIR / "05Performance_Data.csv"
    if not perf_file.exists():
        print(f"❌ {MODULE_TAG} 05Performance_Data.csv 파일이 없습니다.")
        return pd.DataFrame()

    df_perf = local_io.load_csv(perf_file)
    df_perf['Date'] = pd.to_datetime(df_perf['Date'])

    start_date = df_perf['Date'].min().strftime('%Y-%m-%d')
    end_date = df_perf['Date'].max().strftime('%Y-%m-%d')

    print(f"ℹ️ 조회 기간: {start_date} ~ {end_date}")

    df_bench = pd.DataFrame(index=df_perf['Date'])

    for name, ticker in TICKERS.items():
        print(f"ℹ️ {ticker} ({name}) 데이터 다운로드 중...")
        series = _fetch_yahoo_data(ticker, start_date, end_date)

        if series.empty:
            print(f"⚠️ {MODULE_TAG} {ticker} 데이터를 가져오지 못했습니다.")
            continue

        series.index = pd.to_datetime(series.index).tz_localize(None)
        df_bench = df_bench.join(series.rename(ticker), how='left')

        # 비어있는 주말/공휴일은 금요일 가격으로 Forward Fill, 맨 앞 빈값은 Backward Fill
        df_bench[ticker] = df_bench[ticker].ffill().bfill()

        # 누적 수익률 계산
        first_price = df_bench[ticker].iloc[0]
        df_bench[f'{name}_TWR'] = (df_bench[ticker] / first_price) - 1

    df_bench = df_bench.reset_index()

    save_path = config.PROCESSED_DIR / "06Benchmark_Data.csv"
    local_io.save_csv(df_bench, save_path)

    print(f"✅ {MODULE_TAG} 벤치마크 데이터(06) 저장 완료 ({len(df_bench)}건)")
    return df_bench

# 5. Execution Block
def main():
    generate_benchmark_data()

if __name__ == "__main__":
    main()