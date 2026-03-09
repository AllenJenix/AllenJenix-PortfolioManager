"""
@Title: Allenz Portfolio Manager - App Launcher
@Description: 백그라운드에서 Streamlit 서버를 실행하고 PyWebView로 데스크톱 창을 띄우는 런처
@Author: Allen & Gemini
@Date: 2026-03-10
"""

# 1. Imports
import os
import sys
import time
import multiprocessing
import webview
from pathlib import Path

# [PyInstaller 강제 패키징용 미끼 (Dummy Imports)]
import yfinance
import scipy
import plotly
import pandas


# 윈도우 환경 이모지 출력 시 cp949 인코딩 에러 방지
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# 2. Constants (모듈 내 상수)
MODULE_TAG = "[App Launcher]"
SERVER_PORT = 8501

# 3. Main Logic (Classes or Functions)
def _run_streamlit() -> None:
    """
    subprocess(외부 명령) 대신, 파이썬 내부에서 Streamlit 엔진을 직접 구동합니다.

    Args:
        None

    Returns:
        None
    """
    # 경로 설정
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent

    app_path = base_dir / "02src" / "ui" / "app.py"

    # 2. Streamlit 내부 모듈 직접 호출 (무한 증식 방지)
    import streamlit.web.cli as stcli
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--server.port", str(SERVER_PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--global.developmentMode", "false",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none"  # [핵심 추가] 임시 폴더 환경에서의 무한 멈춤 버그 방지
    ]

    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.exit(stcli.main())

def main() -> None:
    """
    메인 실행 함수: Streamlit 프로세스 가동 및 WebView 창 생성

    Args:
        None

    Returns:
        None
    """
    print(f"🚀 {MODULE_TAG} 백그라운드 데이터 엔진 가동 시작...")

    # 별도의 독립된 메모리 공간(Process)에서 Streamlit을 켭니다.
    server_process = multiprocessing.Process(target=_run_streamlit)
    server_process.start()

    # Streamlit 서버가 부팅될 때까지 3초간 대기
    time.sleep(3)

    print(f"ℹ️ {MODULE_TAG} Allenz Portfolio 앱 화면을 띄웁니다...")

    # [수정] PyWebView 데스크톱 창 생성
    window = webview.create_window(
        title="Allenz Portfolio Manager (Beta v1.0)",
        url=f"http://127.0.0.1:{SERVER_PORT}",  # [수정] localhost 대신 127.0.0.1로 통일
        width=1400,
        height=900,
        min_size=(1024, 768)
    )

    webview.start()

    print(f"ℹ️ {MODULE_TAG} 앱을 종료합니다. 백그라운드 서버를 정리합니다...")
    server_process.terminate()
    server_process.join()
    print(f"✅ {MODULE_TAG} 안전하게 종료되었습니다.")

# 4. Execution Block (For Testing)
if __name__ == '__main__':
    # [핵심 방어막] Windows + PyInstaller 환경에서 앱이 무한 증식하는 것을 막아주는 필수 코드
    multiprocessing.freeze_support()
    main()