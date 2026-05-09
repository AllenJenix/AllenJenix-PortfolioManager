```text
Value-Quant-reports/
├── _01Obsidian/                   # 투자 지식 관리 볼트 (Daily Memo, 투자 thesis)
└── _02Allenz_Portfolio_Manager/
    ├── 01DATA/
    │   ├── raw/                   # HTS 원본 (1750.csv, 1721.csv, 17100001.csv)
    │   ├── processed/             # 시스템 생성 CSV (00~07)
    │   ├── reference/             # AI 참조 PDF (RVE Factsheet, Robotti Letters)
    │   └── cache/                 # 외부 API 캐시 (rf_cache.json 등, 24h TTL)
    ├── 02src/
    │   ├── config.py              # 경로/파일명/상수 전역 설정 (Dev/Frozen 모드 분기)
    │   ├── data_loaders/
    │   │   ├── io.py              # CSV 입출력
    │   │   ├── parser.py          # HTS 원본 파싱
    │   │   └── fred.py            # ✅ FRED/yfinance Rf 조회 모듈
    │   ├── engines/
    │   │   ├── ledger.py          # 04Daily_Asset_Ledger 생성 (월별 앵커 보간)
    │   │   ├── metrics.py         # 05Performance_Data 생성 (TWR, MWR, MDD 등)
    │   │   ├── benchmark.py       # 06Benchmark_Data 생성 (SPY, QQQ, IWM)
    │   │   └── history.py         # 07Historical_Holdings 생성
    │   ├── ai/
    │   │   ├── agent.py           # AI 리포트 파이프라인 (Gemini → Claude 전환 예정)
    │   │   ├── mcp_server.py      # MCP 서버 (포트폴리오 데이터 제공)
    │   │   └── prompts.py         # System Persona + Master Report Template
    │   └── ui/
    │       ├── app.py             # 메인 Streamlit UI
    │       └── components/        # analytics, data_manager, history_tab, portfolio
    ├── 03Output/                  # AI 생성 리포트 (.md)
    ├── main.py
    ├── CLAUDE.md
    ├── CODING_CONVENTION.md
    └── requirements.txt
```