"""
@Title: FRED Risk-Free Rate Fetcher
@Description: FRED API (DTB3 시리즈)에서 3개월 T-Bill 금리를 실시간으로 조회.
              FRED_API_KEY 환경변수 없을 시 yfinance (^IRX)로 자동 fallback.
              24시간 TTL 파일 캐시로 불필요한 API 호출 방지.

Fetch Priority:
  1. File Cache (24h TTL)
  2. FRED API  — DTB3 (3-Month Treasury Bill: Secondary Market Rate, Daily)
  3. yfinance  — ^IRX (13-Week T-Bill, fallback)
  4. Hardcoded — FALLBACK_RF (최후 수단)

FRED API Key 발급: https://fredaccount.stlouisfed.org/apikeys (무료)
발급 후 프로젝트 루트 .env 파일에 FRED_API_KEY=your_key_here 추가

@Author: Allen & Claude
@Date: 2026-05-08
"""

# 1. Imports
import json
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 상위 디렉토리(02src) 참조 설정
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config

# 2. Constants
MODULE_TAG = "[FRED]"
FRED_SERIES_ID  = "DTB3"   # 3-Month Treasury Bill: Secondary Market Rate (Daily)
FRED_API_URL    = "https://api.stlouisfed.org/fred/series/observations"
YFINANCE_TICKER = "^IRX"   # 13-week T-Bill annualized yield (%)
CACHE_TTL_HOURS = 24        # 캐시 유효 시간 (시간 단위)
FALLBACK_RF     = 0.045     # 4.5% — 모든 조회 실패 시 사용하는 최후 상수

logger = logging.getLogger(__name__)


# 3. Helper Functions

def _get_cache_path() -> Path:
    """
    캐시 파일 경로를 반환하고, 상위 디렉토리가 없으면 자동 생성합니다.

    Returns:
        Path: rf_cache.json 파일의 절대 경로
    """
    cache_dir = config.DATA_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "rf_cache.json"


def _load_cache() -> dict | None:
    """
    캐시 파일을 읽어 TTL을 검증합니다.

    Returns:
        dict: TTL 내 유효한 캐시 데이터 (rf_rate, source, cached_at 포함)
        None: 캐시 파일이 없거나 TTL 만료, 또는 파싱 오류
    """
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)

        cached_at = datetime.fromisoformat(cache.get("cached_at", "2000-01-01"))
        if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
            return cache

        # TTL 만료
        logger.debug(f"{MODULE_TAG} 캐시 TTL 만료. 신규 조회 진행.")
        return None

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"⚠️ {MODULE_TAG} 캐시 파일 파싱 오류 (무시): {e}")
        return None


def _save_cache(rf_rate: float, source: str) -> None:
    """
    조회된 Rf 값을 캐시 파일에 저장합니다.

    Args:
        rf_rate (float): 연환산 무위험이자율 소수 (e.g. 0.045)
        source  (str):   데이터 출처 식별자 — "FRED" | "yfinance" | "fallback"
    """
    cache_path = _get_cache_path()
    cache_data = {
        "rf_rate":   rf_rate,
        "source":    source,
        "series":    FRED_SERIES_ID,
        "cached_at": datetime.now().isoformat(),
    }
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        # 캐시 저장 실패는 치명적이지 않으므로 경고만 출력
        logger.warning(f"⚠️ {MODULE_TAG} 캐시 저장 실패 (무시 가능): {e}")


def _fetch_from_fred(api_key: str) -> float | None:
    """
    FRED API에서 DTB3 (3-Month T-Bill) 최신 금리를 조회합니다.

    FRED API 응답의 value 필드는 % 단위 문자열 (e.g. "4.27").
    결측값(휴장일 등)은 "." 으로 표기되므로 유효한 첫 번째 관측값을 사용합니다.

    Args:
        api_key (str): FRED API Key

    Returns:
        float: 연환산 무위험이자율 소수 (e.g. 0.0427)
        None:  API 호출 실패 또는 유효 데이터 없음
    """
    try:
        import requests
    except ImportError:
        logger.warning(f"⚠️ {MODULE_TAG} 'requests' 패키지 미설치. pip install requests")
        return None

    params = {
        "series_id":         FRED_SERIES_ID,
        "api_key":           api_key,
        "file_type":         "json",
        "limit":             10,          # 최근 10개 관측값 (결측일 대비 여유분)
        "sort_order":        "desc",
        "observation_start": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
    }

    try:
        response = requests.get(FRED_API_URL, params=params, timeout=10)
        response.raise_for_status()
        observations = response.json().get("observations", [])

        for obs in observations:
            value_str = obs.get("value", ".")
            if value_str != ".":                    # "." = 결측값 (휴장일 등)
                return float(value_str) / 100.0     # % → 소수 변환

        logger.warning(f"⚠️ {MODULE_TAG} FRED 응답에 유효한 관측값 없음.")
        return None

    except Exception as e:
        logger.warning(f"⚠️ {MODULE_TAG} FRED API 호출 실패: {e}")
        return None


def _fetch_from_yfinance() -> float | None:
    """
    yfinance ^IRX (13-Week T-Bill) 티커로 현재 금리를 조회합니다.
    FRED API Key가 없거나 FRED 호출이 실패했을 때 자동으로 사용됩니다.

    ^IRX 는 연환산 % 단위로 반환됩니다 (e.g. 4.27 = 4.27%).

    Returns:
        float: 연환산 무위험이자율 소수 (e.g. 0.0427)
        None:  조회 실패
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.warning(f"⚠️ {MODULE_TAG} 'yfinance' 패키지 미설치.")
        return None

    try:
        hist = yf.Ticker(YFINANCE_TICKER).history(period="5d")

        if hist.empty or "Close" not in hist.columns:
            logger.warning(f"⚠️ {MODULE_TAG} ^IRX 데이터 비어있음.")
            return None

        rate_pct = float(hist["Close"].dropna().iloc[-1])   # % 단위
        return rate_pct / 100.0                             # 소수 변환

    except Exception as e:
        logger.warning(f"⚠️ {MODULE_TAG} yfinance ^IRX 조회 실패: {e}")
        return None


# 4. Main Logic

def get_risk_free_rate() -> float:
    """
    현재 3개월 T-Bill 금리를 연환산 소수(float)로 반환합니다.
    Sharpe Ratio, Sortino Ratio 등 무위험이자율(Rf)이 필요한 모든 모듈에서 호출합니다.

    조회 우선순위:
      1. 파일 캐시       — 24시간 TTL, 네트워크 불필요
      2. FRED API        — DTB3 시리즈, FRED_API_KEY 환경변수 필요
      3. yfinance ^IRX   — 자동 fallback, 별도 키 불필요
      4. FALLBACK_RF     — 4.5% 하드코딩 상수 (최후 수단, 경고 출력)

    Returns:
        float: 연환산 무위험이자율 소수 (e.g. 0.045 = 4.5%)

    Usage:
        from data_loaders.fred import get_risk_free_rate
        rf = get_risk_free_rate()
        sharpe = (portfolio_return - rf) / portfolio_std
    """
    # --- Step 1: 캐시 확인 ---
    cached = _load_cache()
    if cached:
        rf     = cached["rf_rate"]
        source = cached["source"]
        print(f"ℹ️ {MODULE_TAG} 캐시 사용 | Rf = {rf:.4%} | 출처: {source} | "
              f"갱신: {cached.get('cached_at', 'N/A')[:16]}")
        return rf

    print(f"🔄 {MODULE_TAG} 무위험이자율(Rf) 실시간 조회 시작...")

    # --- Step 2: FRED API ---
    fred_api_key = os.getenv("FRED_API_KEY")
    if fred_api_key:
        rf = _fetch_from_fred(fred_api_key)
        if rf is not None:
            _save_cache(rf, "FRED")
            print(f"✅ {MODULE_TAG} FRED 조회 성공 | Rf = {rf:.4%} (DTB3: 3M T-Bill Daily)")
            return rf
        print(f"⚠️ {MODULE_TAG} FRED API 실패. yfinance로 전환...")
    else:
        print(f"ℹ️ {MODULE_TAG} FRED_API_KEY 없음. yfinance로 시도...")
        print(f"    → FRED API Key 발급(무료): https://fredaccount.stlouisfed.org/apikeys")

    # --- Step 3: yfinance Fallback ---
    rf = _fetch_from_yfinance()
    if rf is not None:
        _save_cache(rf, "yfinance")
        print(f"✅ {MODULE_TAG} yfinance 조회 성공 | Rf = {rf:.4%} (^IRX: 13-Week T-Bill)")
        return rf

    # --- Step 4: 하드코딩 최후 Fallback ---
    print(f"⚠️ {MODULE_TAG} 모든 외부 조회 실패. 하드코딩 Fallback 사용 | "
          f"Rf = {FALLBACK_RF:.4%} (config 수정 가능: fred.py > FALLBACK_RF)")
    _save_cache(FALLBACK_RF, "fallback")
    return FALLBACK_RF


def get_cached_info() -> dict | None:
    """
    현재 캐시 상태를 딕셔너리로 반환합니다. UI 디버깅/표시용.

    Returns:
        dict | None: 캐시 데이터 또는 캐시 없음 시 None
    """
    return _load_cache()


# 5. Execution Block (독립 실행 테스트용)
def main():
    """모듈 단독 실행 시 현재 Rf를 조회하고 캐시 상태를 출력합니다."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 50)
    print("  FRED Risk-Free Rate Fetcher — 테스트 실행")
    print("=" * 50)

    rf = get_risk_free_rate()
    print(f"\n🎯 최종 무위험이자율(Rf): {rf * 100:.4f}% ({rf:.6f})")

    cache_info = get_cached_info()
    if cache_info:
        print(f"\n📋 캐시 상태:")
        for k, v in cache_info.items():
            print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
