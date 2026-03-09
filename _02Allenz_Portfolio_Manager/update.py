"""
@Title: One-Click Pipeline Orchestrator (Refactored)
@Description: HTS 원본 데이터 파싱부터 퀀트 엔진, 타임머신 역산까지 모든 프로세스를
              내부 모듈 직접 호출(Import) 방식으로 순차 자동 실행합니다.
@Author: Allen & Gemini
@Date: 2026-03-10
"""

# 1. Imports
import sys
import time
import traceback
from pathlib import Path

# 상위 디렉토리(02src) 참조 설정 (Import를 위해 필수)
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "02src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# 각 파이프라인 모듈 직접 가져오기
from data_loaders import parser
from engines import ledger, metrics, benchmark, history

# 2. Constants (모듈 내 상수)
MODULE_TAG = "[Orchestrator]"

# 3. Main Logic (Classes or Functions)
def _run_module(module, step_name: str) -> None:
    """
    각 모듈의 main() 함수를 안전하게 실행하고 소요 시간을 측정합니다.

    Args:
        module: 실행할 파이썬 모듈 객체
        step_name (str): 출력할 단계의 이름
    """
    print(f"\n{'=' * 60}")
    print(f"🚀 {step_name} 실행 중...")
    print(f"📂 모듈: {module.__name__}")
    print(f"{'=' * 60}")

    start_time = time.time()

    try:
        # 각 스크립트 안에 정의된 main() 함수를 직접 호출합니다.
        # (만약 main()이 없고 if __name__ == '__main__': 안에 로직이 있다면
        # 해당 로직을 각 파일의 def main(): 으로 감싸주어야 합니다.)
        if hasattr(module, 'main') and callable(module.main):
            module.main()
        else:
            print(f"⚠️ {MODULE_TAG} {module.__name__} 모듈에 main() 함수가 없습니다. 실행을 건너뜁니다.")

        elapsed = time.time() - start_time
        print(f"\n✅ [Success] {step_name} 완료 ({elapsed:.2f}초)")

    except Exception as e:
        print(f"\n❌ [Error] {step_name} 실행 중 치명적인 오류 발생!")
        print(traceback.format_exc()) # 상세 에러 로그 출력
        sys.exit(1)  # 파이프라인 즉시 중단

def main() -> None:
    """파이프라인 전체를 순서대로 관장하는 메인 함수"""
    print(f"🔥 {MODULE_TAG} Allenz Portfolio Manager 데이터 파이프라인 가동 시작...")

    total_start = time.time()

    # 1. 데이터 파싱 (HTS -> CSV)
    _run_module(parser, "1. 데이터 파싱 (HTS -> CSV)")

    # 2. 자산 원장 생성 (Ledger)
    _run_module(ledger, "2. 자산 원장 생성 (Ledger)")

    # 3. 성과 지표 산출 (Metrics)
    _run_module(metrics, "3. 성과 지표 산출 (Metrics)")

    # 4. 벤치마크 수집 (SPY/QQQ)
    _run_module(benchmark, "4. 벤치마크 수집 (SPY/QQQ)")

    # 5. 타임머신 역산 (Historical Holdings)
    _run_module(history, "5. 타임머신 역산 (Historical Holdings)")

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"🎉 모든 파이프라인 업데이트가 성공적으로 완료되었습니다!")
    print(f"⏱️ 총 소요 시간: {total_elapsed:.2f}초")
    print(f"{'=' * 60}\n")

# 4. Execution Block (For Testing)
if __name__ == '__main__':
    main()