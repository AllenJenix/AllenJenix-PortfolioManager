"""
@Title: Portfolio MCP Server (Native PDF Support)
@Description: Serves CSV data as text, and PDF references as file paths for Gemini File API.
@Author: Allen & Gemini
"""

import sys
import pandas as pd
from pathlib import Path
from mcp.server.fastmcp import FastMCP

MODULE_TAG = "[MCP Server]"
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
ROOT_DIR = SRC_DIR.parent

PROCESSED_DIR = ROOT_DIR / "01DATA" / "processed"
REFERENCE_DIR = ROOT_DIR / "01DATA" / "reference"

mcp = FastMCP("Allenz_Portfolio_Server")

# --- 1. Resources (Returns Absolute File Paths for PDF Uploads) ---
@mcp.resource("resource://reference/factsheet_pdf")
def get_factsheet_pdf_path() -> str:
    pdf_path = REFERENCE_DIR / "RVE-Fact-Sheet-December-2025.pdf"
    if not pdf_path.exists(): raise FileNotFoundError("Factsheet PDF missing.")
    return str(pdf_path)

@mcp.resource("resource://reference/philosophy_pdf")
def get_philosophy_pdf_path() -> str:
    pdf_path = REFERENCE_DIR / "Robotti-Company-Advisors-YE-2025-Letter-w-disc.pdf"
    if not pdf_path.exists(): raise FileNotFoundError("Letter PDF missing.")
    return str(pdf_path)

# --- 2. Tools (Dynamic Data Extractors) ---
@mcp.tool()
def get_performance_vs_benchmarks(target_month: str) -> str:
    asset_path = PROCESSED_DIR / "01Asset_Summary.csv"
    bench_path = PROCESSED_DIR / "06Benchmark_Data.csv"
    if not asset_path.exists() or not bench_path.exists(): raise FileNotFoundError("CSV missing.")
    df_asset = pd.read_csv(asset_path)
    return f"### My Data 1: Performance for {target_month}\n" + df_asset.tail(3).to_markdown(index=False)

@mcp.tool()
def get_current_holdings_and_cash() -> str:
    portfolio_path = PROCESSED_DIR / "03Full_Portfolio.csv"
    if not portfolio_path.exists(): raise FileNotFoundError("CSV missing.")
    df = pd.read_csv(portfolio_path)
    top_holdings = df.sort_values(by='보유비중', ascending=False).head(10) if '보유비중' in df.columns else df.head(10)
    return "### My Data 2: Current Holdings\n" + top_holdings[['종목명', '보유비중', '수익률', '평가금액']].to_markdown(index=False)

@mcp.tool()
def get_key_portfolio_changes(start_date: str, end_date: str) -> str:
    history_path = PROCESSED_DIR / "07Historical_Holdings.csv"
    if not history_path.exists(): raise FileNotFoundError("CSV missing.")
    df = pd.read_csv(history_path)
    start_data = df[df['Date'] == start_date]
    end_data = df[df['Date'] == end_date]
    return f"### My Data 3: Changes\n**Start ({start_date}):**\n{start_data.to_markdown(index=False)}\n\n**End ({end_date}):**\n{end_data.to_markdown(index=False)}\n"

if __name__ == "__main__":
    mcp.run()