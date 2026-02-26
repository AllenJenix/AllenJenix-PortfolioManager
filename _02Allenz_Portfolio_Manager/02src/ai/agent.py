"""
@Title: Portfolio AI Agent (Multimodal PDF Native Support)
@Description: Fetches data & PDF paths via MCP, uploads PDFs to Gemini via File API, and generates report.
@Author: Allen & Gemini
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Google GenAI Native SDK
from google import genai

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from prompts import SYSTEM_PROMPT, MASTER_REPORT_PROMPT

# 설정 로드
load_dotenv()
MODULE_TAG = "[AI Agent]"
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent
OUTPUT_DIR = ROOT_DIR / "03Output"
LOG_DIR = ROOT_DIR / "logs"
SERVER_SCRIPT_PATH = CURRENT_DIR / "mcp_server.py"

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"ai_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

async def generate_report():
    logger.info(f"🚀 {MODULE_TAG} 파이프라인 가동 (Native PDF + MCP)")

    if "GOOGLE_API_KEY" not in os.environ:
        logger.error("❌ GOOGLE_API_KEY 환경 변수가 없습니다 (.env 확인).")
        sys.exit(1)

    # 1. Google GenAI 클라이언트 초기화
    client = genai.Client()
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT_PATH)])

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("✅ MCP 서버 접속 성공!")

                # 2. Resource (PDF 파일 경로) 수집
                logger.info("📂 레퍼런스(PDF) 경로 수집 중...")
                res_fact = await session.read_resource("resource://reference/factsheet_pdf")
                res_phil = await session.read_resource("resource://reference/philosophy_pdf")
                factsheet_path = res_fact.contents[0].text
                philosophy_path = res_phil.contents[0].text

                # 3. Tool (정량 데이터 CSV) 수집
                logger.info("⚙️ 포트폴리오 성과 데이터 추출 중...")
                perf_result = await session.call_tool("get_performance_vs_benchmarks", arguments={"target_month": "2025-01"})
                hold_result = await session.call_tool("get_current_holdings_and_cash", arguments={})
                change_result = await session.call_tool("get_key_portfolio_changes", arguments={"start_date": "2025-01-02", "end_date": "2025-01-31"})

                perf_data = perf_result.content[0].text
                hold_data = hold_result.content[0].text
                change_data = change_result.content[0].text

        # 4. PDF 구글 서버 업로드 (File API)
        logger.info("📤 PDF 레퍼런스를 Gemini 서버로 전송 중...")
        fact_file_obj = client.files.upload(file=factsheet_path)
        phil_file_obj = client.files.upload(file=philosophy_path)

        # 5. 프롬프트 조립 및 생성 요청 (멀티모달)
        logger.info(f"🧠 Gemini-2.5-pro 모델이 PDF 레이아웃과 데이터를 분석하여 딥 밸류 서한을 집필 중입니다...")

        final_prompt_text = MASTER_REPORT_PROMPT.format(
            performance_data=perf_data,
            holdings_data=hold_data,
            portfolio_changes=change_data
        )

        # Flash 대신 가장 똑똑한 Pro 모델로 변경!
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=[
                SYSTEM_PROMPT,
                fact_file_obj,  # 업로드된 Factsheet PDF 객체 전달
                phil_file_obj,  # 업로드된 Letter PDF 객체 전달
                final_prompt_text
            ]
        )

        # 6. 파일 저장
        output_file = OUTPUT_DIR / "2025_01_Integrated_Report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text)

        logger.info(f"🎉 리포트 생성 완료! 파일 위치: {output_file.relative_to(ROOT_DIR)}")

        # (선택) 구글 서버에 업로드된 임시 파일 삭제
        client.files.delete(name=fact_file_obj.name)
        client.files.delete(name=phil_file_obj.name)

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(generate_report())