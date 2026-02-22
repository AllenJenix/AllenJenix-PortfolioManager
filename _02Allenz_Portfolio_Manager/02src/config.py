"""
@Title: Global Configuration
@Description: 프로젝트 전반의 파일 경로, 원본/정제 파일명 매핑, 공통 상수를 관리하는 모듈
@Author: Allen & Gemini
@Date: 2026-02-12
"""

# 1. Imports
import os
import json
from pathlib import Path

# 2. Path Configuration (경로 설정)
# SRC_DIR: config.py가 위치한 현재 폴더 (02src)
SRC_DIR = Path(__file__).resolve().parent

# BASE_DIR: 프로젝트 최상위 루트 폴더 (Allenz_Portfolio_Manager)
BASE_DIR = SRC_DIR.parent

# 데이터 저장소 경로
DATA_DIR = BASE_DIR / "01DATA"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# 3. Directory Initialization (디렉토리 초기화)
# 데이터 폴더가 없으면 자동으로 생성
if not RAW_DIR.exists():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🚀 [Config] Raw Data 폴더 생성됨: {RAW_DIR}")

if not PROCESSED_DIR.exists():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🚀 [Config] Processed Data 폴더 생성됨: {PROCESSED_DIR}")

# 4. File Name Mapping (파일명 매핑 상수)
# 사용자가 다운로드한 HTS 원본 파일명 (변경 시 여기만 수정)
RAW_FILES = {
    'transaction': '1750.csv',       # 거래 내역 (HTS 1750 화면)
    'asset_summary': '1721.csv',     # 자산 현황 (HTS 1721 화면)
    'holdings': '17100001.csv'       # 보유 종목 (HTS 17100001 화면)
}

# 시스템이 생성/사용할 표준화된 파일명
PROCESSED_FILES = {
    'transaction': '00Transaction_History.csv',      # 정제된 거래 내역
    'asset': '01Asset_Summary.csv',                  # 정제된 자산 요약
    'holdings': '02Portfolio_Holdings.csv',          # 정제된 보유 현황
    'full_portfolio': '03Full_Portfolio.csv',        # cash 포함 보유 현황
    'ledger': '04Daily_Asset_Ledger.csv',            # 일별 자산 원장 (시계열)
    'performance': '05Performance_Data.csv',         # 성과 지표 (TWR/MWR/MDD)
    'benchmark': '06Benchmark_Data.csv',             # 시장 지수 데이터
    'timeline': '07Historical_Holdings.csv'          # 종목별 보유수량 타임라인 (타임머신용)
}

# 5. Global Constants (공통 상수)
# 파일 인코딩
ENCODING_KR = 'cp949'      # HTS 다운로드 원본 (한글 윈도우 표준)
ENCODING_STD = 'utf-8-sig' # 내부 처리용 표준 (Excel 호환)

# --- [Tickers Mapping (Temporary JSON)] ---
# 향후 자동화 전까지 수동 매핑(ISIN -> Ticker)을 분리하여 관리합니다.
ISIN_MAPPING_FILE = SRC_DIR / "isin_mapping.json"
ISIN_TO_TICKER = {}

if ISIN_MAPPING_FILE.exists():
    try:
        with open(ISIN_MAPPING_FILE, 'r', encoding='utf-8') as f:
            ISIN_TO_TICKER = json.load(f)
    except Exception as e:
        print(f"⚠️ [Config] isin_mapping.json 로드 실패: {e}")