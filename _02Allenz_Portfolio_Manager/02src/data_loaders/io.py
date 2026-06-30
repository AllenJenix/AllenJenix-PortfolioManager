"""
@Title: I/O Utilities
@Description: CSV 파일 읽기/쓰기를 위한 공통 유틸리티 모듈 (인코딩 자동 처리 및 폴더 생성 포함)
@Author: Allen & Gemini
@Date: 2026-02-12
"""

# 1. Imports
import os
import sys
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any

# 상위(02src) 디렉토리의 config.py를 참조하기 위한 경로 설정
# (단독 실행 및 패키지 실행 모두 호환되도록 설정)
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config

# 2. Constants
MODULE_TAG = "[IO]"


# 3. Main Functions
def load_csv(file_path: str, encoding: str = config.ENCODING_STD, **kwargs) -> pd.DataFrame:
    """
    CSV 파일을 안전하게 로드합니다. 인코딩 에러 발생 시 CP949로 재시도합니다.

    Args:
        file_path (str): 읽을 파일 경로
        encoding (str): 우선 시도할 인코딩 (기본값: utf-8-sig)
        **kwargs: pd.read_csv에 전달할 추가 인자

    Returns:
        pd.DataFrame: 로드된 데이터프레임

    Raises:
        FileNotFoundError: 파일이 없을 경우
    """
    path_obj = Path(file_path)

    if not path_obj.exists():
        # 파일이 없으면 에러 발생 (호출하는 쪽에서 처리)
        raise FileNotFoundError(f"❌ {MODULE_TAG} 파일을 찾을 수 없습니다: {path_obj}")

    try:
        # 1차 시도: 지정된 인코딩(보통 utf-8)
        df = pd.read_csv(path_obj, encoding=encoding, **kwargs)
        return df

    except pd.errors.EmptyDataError:
        print(f"⚠️ {MODULE_TAG} 빈 파일 감지. 빈 DataFrame 반환: {path_obj.name}")
        return pd.DataFrame()

    except UnicodeDecodeError:
        # 2차 시도: 한국어 인코딩(cp949)
        print(f"⚠️ {MODULE_TAG} 인코딩({encoding}) 실패. '{config.ENCODING_KR}'로 재시도합니다: {path_obj.name}")
        try:
            df = pd.read_csv(path_obj, encoding=config.ENCODING_KR, **kwargs)
            return df
        except pd.errors.EmptyDataError:
            print(f"⚠️ {MODULE_TAG} 빈 파일 감지 (CP949). 빈 DataFrame 반환: {path_obj.name}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ {MODULE_TAG} CP949 로드 실패: {e}")
            raise e


def save_csv(df: pd.DataFrame, file_path: str, encoding: str = config.ENCODING_STD, index: bool = False) -> None:
    """
    DataFrame을 CSV로 저장합니다. 부모 디렉토리가 없으면 생성합니다.

    Args:
        df (pd.DataFrame): 저장할 데이터
        file_path (str): 저장 경로
        encoding (str): 저장 인코딩
        index (bool): 인덱스 저장 여부
    """
    path_obj = Path(file_path)

    # 저장할 폴더가 없으면 생성
    if not path_obj.parent.exists():
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        print(f"📂 {MODULE_TAG} 폴더 생성됨: {path_obj.parent}")

    try:
        df.to_csv(path_obj, encoding=encoding, index=index)
        print(f"💾 {MODULE_TAG} 저장 완료: {path_obj.name}")
    except Exception as e:
        print(f"❌ {MODULE_TAG} 저장 실패: {e}")
        raise e


# 4. Execution Block (For Verification)
if __name__ == "__main__":
    # 테스트용 더미 데이터 생성 및 저장/로드 테스트
    print(f"🚀 {MODULE_TAG} Unit Test 시작...")

    test_file = config.DATA_DIR / "test_io.csv"
    dummy_data = pd.DataFrame({'col1': [1, 2], 'col2': ['A', 'B']})

    # 저장 테스트
    save_csv(dummy_data, test_file)

    # 로드 테스트
    loaded_df = load_csv(test_file)
    print(f"ℹ️ 로드된 데이터:\n{loaded_df}")

    # 테스트 파일 삭제
    if test_file.exists():
        os.remove(test_file)
        print(f"🗑️ 테스트 파일 삭제 완료")