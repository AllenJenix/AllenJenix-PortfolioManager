```text
Allenz_Portfolio_Manager/
│
├── .env                     # 🔒 API 키 등 환경 변수 저장 (git 제외)
├── .gitignore               # git 추적 제외 목록 (.env, logs 등)
│
├── 01DATA/                  # 💾 [데이터 계층]
│   ├── raw/                 # [Input] HTS에서 다운받은 원본 CSV (자동화 시작점)
│   ├── processed/           # [Output] 파이프라인이 정제/생성한 시스템 데이터 (00~07)
│   └── reference/           # 📚 [AI Source] 주주서한/팩트시트 원본 PDF
│
├── 02src/                   # 🧠 [소스 코드]
│   ├── config.py            # [전역 설정] 절대 경로, 파일명 매핑, 공통 상수 관리
│   ├── isin_mapping.json    # [설정] ISIN 국제표준코드 ↔ 실제 Ticker 수동 매핑 사전
│   │
│   ├── data_loaders/        # 🧱 [Layer 1] 데이터 수집 및 전처리
│   │   ├── io.py            
│   │   └── parser.py        
│   │
│   ├── engines/             # ⚙️ [Layer 2] 퀀트 분석 핵심 엔진
│   │   ├── ledger.py        
│   │   ├── metrics.py       
│   │   ├── benchmark.py     
│   │   └── history.py       
│   │
│   ├── ui/                  # 🖥️ [Layer 3] Streamlit 웹 대시보드
│   │   ├── app.py           
│   │   └── components/      
│   │       ├── portfolio.py 
│   │       ├── analytics.py 
│   │       └── history_tab.py 
│   │
│   └── ai/                  # 🤖 [Layer 4] 멀티모달 AI 리포트 생성 (Gemini 2.5 Pro)
│       ├── mcp_server.py    
│       ├── agent.py         
│       └── prompts.py       
│
├── 03Output/                # ✉️ [출력 계층] AI가 생성한 최종 결과물
│   └── 2025_01_Integrated_Report.md
│
├── logs/                    # 📝 실행 로그 폴더
│
├── CODING_CONVENTION.md     # 📜 코딩 표준 정의서
├── FILE_TREE.md             # 📜 프로젝트 디렉터리 구조
│
└── update.py                # 🔄 [메인 스위치] 전체 데이터 갱신 및 파이프라인 트리거
```