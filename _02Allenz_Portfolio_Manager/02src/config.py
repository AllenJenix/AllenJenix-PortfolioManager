"""
@Title: Global Configuration (App Ready)
@Description: 프로젝트 전반의 파일 경로, 원본/정제 파일명 매핑, 공통 상수를 관리하는 모듈
@Author: Allen & Gemini
@Date: 2026-03-04
"""

# 1. Imports
import os
import sys
import json
from pathlib import Path

# 2. Execution Mode Detection (실행 모드 감지)
IS_FROZEN = getattr(sys, 'frozen', False)

# 3. Path Configuration (스마트 경로 설정)
if IS_FROZEN:
    # [배포 모드] PyInstaller로 패키징된 .exe 실행 상태
    # 소스 코드(json 등)는 임시 폴더(sys._MEIPASS)를 바라보게 하고,
    # 데이터(.csv, .pdf)는 OS의 영구 숨김 폴더(~/.allenz_portfolio/)를 바라보게 분리합니다.
    BUNDLE_DIR = Path(sys._MEIPASS)
    SRC_DIR = BUNDLE_DIR / "02src"

    USER_HOME = Path.home()
    DATA_DIR = USER_HOME / ".allenz_portfolio" / "01DATA"
else:
    # [개발 모드] 일반 파이썬 스크립트로 실행 상태
    # 기존과 동일하게 현재 프로젝트 폴더를 바라봅니다.
    SRC_DIR = Path(__file__).resolve().parent
    BASE_DIR = SRC_DIR.parent
    DATA_DIR = BASE_DIR / "01DATA"

# 세부 데이터 폴더 경로
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference" # AI가 참고할 PDF 자원 폴더 추가

# 4. Directory Initialization (디렉토리 자동 생성)
for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR, REFERENCE_DIR]:
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        print(f"🚀 [Config] 필수 디렉토리 확인/생성됨: {d}")

# 5. File Name Mapping (파일명 매핑 상수)
# 사용자가 다운로드한 HTS 원본 파일명
RAW_FILES = {
    'transaction': '1750.csv',       # 거래 내역 (HTS 1750 화면)
    'asset_summary': '1721.csv',     # 자산 현황 (HTS 1721 화면)
    'holdings': '17100001.csv'       # 보유 종목 (HTS 17100001 화면)
}

# 시스템이 생성/사용할 표준화된 파일명
PROCESSED_FILES = {
    'transaction': '00Transaction_History.csv',
    'asset': '01Asset_Summary.csv',
    'holdings': '02Portfolio_Holdings.csv',
    'full_portfolio': '03Full_Portfolio.csv',
    'ledger': '04Daily_Asset_Ledger.csv',
    'performance': '05Performance_Data.csv',
    'benchmark': '06Benchmark_Data.csv',
    'timeline': '07Historical_Holdings.csv'
}

# 6. Global Constants (공통 상수)
ENCODING_KR = 'cp949'      # HTS 다운로드 원본 (한글 윈도우 표준)
ENCODING_STD = 'utf-8-sig' # 내부 처리용 표준 (Excel 호환)

# --- [Tickers Mapping (Temporary JSON)] ---
ISIN_MAPPING_FILE = SRC_DIR / "isin_mapping.json"
ISIN_TO_TICKER = {}

if ISIN_MAPPING_FILE.exists():
    try:
        with open(ISIN_MAPPING_FILE, 'r', encoding='utf-8') as f:
            ISIN_TO_TICKER = json.load(f)
    except Exception as e:
        print(f"⚠️ [Config] isin_mapping.json 로드 실패: {e}")