```angular2html
Allenz_Portfolio_Manager/
│
├── 01DATA/                  # (데이터 저장소 - Data Repository)
│   ├── raw/                 # HTS에서 다운받은 원본 파일 (1750.csv 등)
│   └── processed/           # 시스템이 생성한 정제 파일 (00~06.csv)
│
├── 02src/                   # (소스 코드 - Source Code)
│   ├── config.py            # [Global Config] 경로 및 공통 설정 관리 (Root of Source)
│   ├── __init__.py
│   │
│   ├── 01data_loaders/      # [Layer 1] 데이터 입출력 & 파싱 (Data Access Layer)
│   │   ├── __init__.py
│   │   ├── io.py            # CSV 읽기/쓰기 공통 유틸리티
│   │   └── parser.py        # HTS 원본 데이터 파싱 및 표준화 로직
│   │
│   ├── 02engines/           # [Layer 2] 금융 계산 핵심 로직 (Business Logic Layer)
│   │   ├── __init__.py
│   │   ├── ledger.py        # 일별 자산 원장 생성 & 보간법 적용 (-> 04파일)
│   │   ├── metrics.py       # 성과 지표(TWR, MWR, MDD) 계산 (-> 05파일)
│   │   ├── timemachine.py   # 보유 수량 역산 & 최저점 보정 (-> 06파일)
│   │   └── benchmark.py     # yfinance 연동 & 시장 지수 비교 분석
│   │
│   └── 03ui/                # [Layer 3] 시각화 및 리포팅 (Presentation Layer)
│       ├── __init__.py
│       ├── dashboard.py     # 포트폴리오 타임머신 대시보드 (Interactive)
│       ├── plotter.py       # 정적 차트 및 벤치마크 그래프
│       └── letter_gen.py    # (Planned) AI 주주서한 프롬프트 생성기
│
├── requirements.txt         # 프로젝트 의존성 라이브러리 목록
└── main.py                  # 프로그램 실행 진입점 (Entry Point)
```