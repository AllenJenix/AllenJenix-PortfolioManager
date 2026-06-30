"""
@Title: Data Manager UI Component
@Description: 사용자로부터 HTS 원본(Raw) 데이터를 업로드 받아 저장하고 파이프라인을 트리거하는 UI
@Author: Allen & Gemini
@Date: 2026-03-04
"""

import sys
import subprocess
import streamlit as st
from pathlib import Path

# --- 상위 폴더의 config 모듈 임포트 ---
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

import config

def render():
    st.header("📂 데이터 적재 및 파이프라인 관리")
    st.markdown("""
    HTS에서 다운로드한 최신 원본 파일들을 아래에 드래그 앤 드롭으로 업로드해 주세요.
    업로드 후 **[데이터 갱신 및 파이프라인 가동]** 버튼을 누르면 모든 지표가 자동으로 재계산됩니다.
    """)

    st.divider()

    # 1. 필요 파일 목록 안내
    st.subheader("📌 필요 파일 체크리스트")
    col1, col2, col3, col4 = st.columns(4)
    col1.info(f"거래 내역\n\n**{config.RAW_FILES['transaction']}**")
    col2.info(f"자산 현황\n\n**{config.RAW_FILES['asset_summary']}**")
    col3.info(f"보유 종목\n\n**{config.RAW_FILES['holdings']}**")
    col4.info(f"해외주식 매매내역\n\n**{config.RAW_FILES['trade_history']}**")

    # 2. 파일 업로더 위젯
    uploaded_files = st.file_uploader(
        "CSV 또는 Excel 파일을 여러 개 선택해서 올려주세요.",
        accept_multiple_files=True,
        type=['csv', 'xls', 'xlsx']
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)}개의 파일이 대기 중입니다.")

        # 3. 파이프라인 트리거 버튼
        if st.button("🚀 데이터 갱신 및 파이프라인 가동", use_container_width=True, type="primary"):
            with st.spinner("데이터를 저장하고 파이프라인을 가동하고 있습니다. 잠시만 기다려주세요..."):

                # Step A: 업로드된 파일들을 config.RAW_DIR (또는 ~/.allenz_portfolio/raw/)에 저장
                saved_count = 0
                for file in uploaded_files:
                    # 파일명이 우리가 요구하는 이름(1750.csv 등)과 일치하는지 확인
                    if file.name in config.RAW_FILES.values():
                        save_path = config.RAW_DIR / file.name
                        with open(save_path, "wb") as f:
                            f.write(file.getbuffer())
                        saved_count += 1
                    else:
                        st.warning(f"⚠️ 인식할 수 없는 파일명 무시됨: {file.name}")

                # Step B: 필수 파일이 잘 저장되었는지 확인 후 update.py 실행
                if saved_count > 0:
                    st.info(f"✅ {saved_count}개의 파일이 성공적으로 로컬 저장소에 적재되었습니다.")

                    # update.py 경로 찾기 (루트 디렉토리에 존재한다고 가정)
                    root_dir = src_dir.parent
                    update_script = root_dir / "update.py"

                    try:
                        # [핵심 수정] subprocess 대신 파이썬 내부 모듈로 직접 가져와서 실행합니다.
                        import sys
                        from pathlib import Path

                        # 최상위 루트 경로를 시스템 경로에 추가하여 update.py를 찾을 수 있게 함
                        root_dir = Path(__file__).resolve().parent.parent.parent.parent
                        if str(root_dir) not in sys.path:
                            sys.path.append(str(root_dir))

                        # 이제 root에 있는 update.py를 모듈로 불러올 수 있습니다.
                        import update

                        # update.py 안의 메인 로직 함수(main)를 직접 실행
                        update.main()

                        st.success("🎉 파이프라인 실행이 완료되었습니다! 대시보드를 확인해 주세요.")
                        st.cache_data.clear()

                    except Exception as e:
                        st.error("❌ 파이프라인 실행 중 오류가 발생했습니다.")
                        with st.expander("에러 로그 보기"):
                            st.code(str(e))
                else:
                    st.error("❌ 올바른 이름(1750.csv 등)의 파일이 업로드되지 않았습니다.")