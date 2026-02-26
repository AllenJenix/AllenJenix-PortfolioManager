"""
@Title: One-Click Pipeline Updater
@Description: HTS 원본 데이터 파싱부터 퀀트 엔진, 타임머신 역산까지 모든 프로세스를 순차적으로 자동 실행합니다.
@Author: Allen & Gemini
"""

import sys
import subprocess
import time
from pathlib import Path

# 프로젝트 루트 경로 설정 (_02Allenz_Portfolio_Manager)
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "02src"


def run_script(script_path: Path, step_name: str):
    """지정된 파이썬 스크립트를 실행하고 결과를 출력합니다."""
    print(f"\n{'=' * 60}")
    print(f"🚀 [Step: {step_name}] 실행 중...")
    print(f"📂 경로: {script_path.relative_to(PROJECT_ROOT)}")
    print(f"{'=' * 60}")

    start_time = time.time()

    try:
        # 현재 실행 중인 파이썬 인터프리터(가상환경 포함)를 사용하여 서브 프로세스 실행
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            text=True,
            capture_output=False  # 로그를 실시간으로 터미널에 출력
        )
        elapsed = time.time() - start_time
        print(f"\n✅ [Success] {step_name} 완료 ({elapsed:.2f}초)")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ [Error] {step_name} 실행 중 오류 발생!")
        print(f"Exit Code: {e.returncode}")
        sys.exit(1)  # 파이프라인 즉시 중단


def main():
    print(f"🔥 Allenz Portfolio Manager 데이터 파이프라인 가동 시작...")

    # 실행할 스크립트 목록 (순서 보장)
    pipeline = [
        (SRC_DIR / "data_loaders" / "parser.py", "1. 데이터 파싱 (HTS -> CSV)"),
        (SRC_DIR / "engines" / "ledger.py", "2. 자산 원장 생성 (Ledger)"),
        (SRC_DIR / "engines" / "metrics.py", "3. 성과 지표 산출 (Metrics)"),
        (SRC_DIR / "engines" / "benchmark.py", "4. 벤치마크 수집 (SPY/QQQ)"),
        (SRC_DIR / "engines" / "history.py", "5. 타임머신 역산 (Historical Holdings)")
    ]

    total_start = time.time()

    for script_path, step_name in pipeline:
        if not script_path.exists():
            print(f"❌ 파일이 존재하지 않습니다: {script_path}")
            sys.exit(1)
        run_script(script_path, step_name)

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"🎉 모든 파이프라인 업데이트가 성공적으로 완료되었습니다!")
    print(f"⏱️ 총 소요 시간: {total_elapsed:.2f}초")
    print(f"{'=' * 60}")
    print(f"\n💡 터미널에 'streamlit run 02src/ui/app.py'를 입력하여 대시보드를 확인하세요.")


if __name__ == "__main__":
    main()