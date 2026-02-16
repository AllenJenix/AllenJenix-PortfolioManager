# 📜 Portfolio Manager - Coding Convention & Style Guide

이 문서는 `Allenz_Portfolio_Manager` 프로젝트의 모든 Python 코드 작성 시 준수해야 할 규칙을 정의합니다.

## 1. General Principles (기본 원칙)
1.  **PEP 8 준수**: 파이썬 공식 스타일 가이드를 기본으로 합니다.
2.  **Explicit is better than implicit**: 모호한 변수명이나 암시적인 로직을 피합니다.
3.  **Modular & Atomic**: 하나의 함수는 하나의 기능만 수행합니다.
4.  **Type Hinting**: 모든 함수의 인자와 반환값에 타입 힌트를 명시합니다.

## 2. Naming Conventions (명명 규칙)
| 항목 | 규칙 | 예시 | 비고 |
| :--- | :--- | :--- | :--- |
| **변수/함수** | `snake_case` | `calc_total_assets`, `user_name` | 동사+목적어 형태 권장 |
| **클래스** | `PascalCase` | `PortfolioManager`, `AssetLedger` | 명사형 사용 |
| **상수** | `UPPER_CASE` | `MAX_RETRY`, `DEFAULT_PATH` | `config.py` 등에서 사용 |
| **내부 변수** | `_snake_case` | `_parse_raw_data` | 외부에서 호출하지 않는 함수/변수 |

## 3. File Structure Template (파일 구조 템플릿)
모든 `.py` 파일은 아래 구조를 따릅니다.

```python
"""
@Title: 파일 제목 (예: Transaction Parser)
@Description: 이 모듈이 수행하는 역할에 대한 간략한 설명
@Author: Allen & Gemini
@Date: YYYY-MM-DD
"""

# 1. Imports (Standard -> Third Party -> Local)
import os
import pandas as pd
from typing import List, Dict, Optional

# 상위 디렉토리의 config 참조 시
from .. import config 

# 2. Constants (모듈 내 상수)
MODULE_TAG = "[Parser]"

# 3. Main Logic (Classes or Functions)
def process_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    함수 기능 설명
    
    Args:
        data (pd.DataFrame): 입력 데이터
        
    Returns:
        pd.DataFrame: 처리된 데이터
    """
    # Step 1: Logic A
    pass

# 4. Execution Block (For Testing)
if __name__ == "__main__":
    # 테스트 코드 작성
    pass
```

## 4. Logging & Output Style (로그 및 출력 양식)
시스템 상태를 출력할 때는 `print()` 함수를 사용하되, 가독성을 위해 **이모지 헤더**를 통일합니다.

| 상황 | 이모지 | 포맷 예시 |
| :--- | :--- | :--- |
| **시작/진행** | 🚀 | `print(f"🚀 {기능명} 가동 시작...")` |
| **성공/완료** | ✅ | `print(f"✅ {파일명} 저장 완료 ({len(df)}건)")` |
| **정보/상태** | ℹ️ | `print(f"ℹ️ {변수명}: {값}")` |
| **경고** | ⚠️ | `print(f"⚠️ {파일명} 데이터가 비어있습니다. 건너뜁니다.")` |
| **에러/실패** | ❌ | `print(f"❌ 오류 발생: {error_msg}")` |
| **파일 로드** | 📂 | `print(f"📂 파일 로드: {path}")` |
| **파일 저장** | 💾 | `print(f"💾 결과 저장: {path}")` |

## 5. Commenting Rules (주석 규칙)
1.  **Docstrings**: 모든 함수/클래스 바로 아래에 `"""`를 사용하여 설명, 인자(Args), 반환값(Returns)을 기술합니다.
2.  **Inline Comments**: 코드 라인 끝보다는 **해당 라인 위**에 작성하는 것을 권장합니다.
3.  **Block Comments**: 복잡한 로직의 경우 `Step 1`, `Step 2` 등으로 단계를 명시합니다.

## 6. Project Directory Reference (참조용)
```text
Allenz_Portfolio_Manager/
├── 01DATA/ (raw, processed)
└── 02src/
    ├── config.py
    ├── 01data_loaders/ (io.py, parser.py)
    ├── 02engines/ (ledger.py, metrics.py, ...)
    └── 03ui/
```