# 📈 Allenz Portfolio Manager

![Status](https://img.shields.io/badge/Status-Beta_v1.0-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![Gemini](https://img.shields.io/badge/AI-Google_Gemini-4285F4)
![PyInstaller](https://img.shields.io/badge/Build-PyInstaller_.exe-orange)

> 증권사 HTS 원본 데이터를 자동 정제하고, 성과 지표(TWR / MDD / Sharpe / Alpha)를 산출하며, 과거 포트폴리오 구성을 임의 시점으로 복원하는 **개인 투자 포트폴리오 통합 운용 플랫폼**.

---

## 📌 핵심 기능 (Key Features)

| 기능 | 설명 |
|------|------|
| **Robust ETL Pipeline** | HTS 비정형 CSV(cp949/utf-8 자동 감지, 다중 행 헤더)를 시스템 표준 포맷으로 완전 정제 |
| **Performance Analytics** | 현금흐름을 분리한 순수 운용 실력 측정 — TWR / MWR(XIRR) / MDD / Sharpe / Sortino / Calmar / IR / Beta / Alpha |
| **Dynamic Benchmark** | SPY · QQQ · IWM 실시간 연동 및 조회 구간 변경 시 시작점 0% 동적 재조정(Dynamic Rebasing) |
| **Historical Holdings (Time Machine)** | 현재 잔고를 Anchor로 거래 내역을 역산하여 **과거 임의 시점의 포트폴리오 구성을 100% 복원** |
| **AI Report Generation** `🚧` | Google Gemini + MCP 기반 주주서한 자동 생성 — **현재 개발 중지** |
| **Interactive Dashboard** | Streamlit + Plotly 기반 4-Tab 웹 대시보드 (포트폴리오 / 성과분석 / 과거복원 / 데이터관리) |
| **Standalone .exe** | PyInstaller + PyWebView로 패키징된 단일 실행 파일 — Python 환경 없이 즉시 구동 |

---

## 🏗️ 시스템 아키텍처 (3-Tier Architecture)

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 0 · Raw Input                                    │
│  HTS Exports: 1750(거래) · 1721(잔고) · 2610(해외주식) │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  LAYER 1 · Data Loaders  (02src/data_loaders/)         │
│  parser.py  ·  io.py  ·  fred.py  ·  trade_log.py      │
│  → 00~03 processed CSV 생성 (표준화된 거래·보유 데이터) │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  LAYER 2 · Calculation Engines  (02src/engines/)        │
│  ledger.py   → 04 Daily Asset Ledger                    │
│  metrics.py  → 05 Performance Data (TWR/MWR/Risk)       │
│  benchmark.py→ 06 Benchmark Data (SPY/QQQ/IWM)         │
│  history.py  → 07 Historical Holdings (Time Machine)    │
└──────────────┬────────────────────┬────────────────────-┘
               ↓                    ↓
┌──────────────────────┐  ┌─────────────────────────────-─┐
│  LAYER 3 · UI        │  │  LAYER 3 · AI Agent           │
│  (02src/ui/)         │  │  (02src/ai/)                  │
│  app.py              │  │  mcp_server.py (데이터 노출)  │
│  portfolio.py        │  │  agent.py (Gemini 호출)       │
│  analytics.py        │  │  prompts.py (페르소나 템플릿) │
│  history_tab.py      │  │  → 03Output/ 주주서한.md      │
│  data_manager.py     │  └───────────────────────────────┘
└──────────────────────┘
```

---

## 📊 산출 지표 (Metrics)

| 카테고리 | 지표 |
|---------|------|
| **수익률** | Time-Weighted Return (TWR), Money-Weighted Return / XIRR |
| **리스크** | Max Drawdown (MDD), Annualized Volatility |
| **위험조정수익률** | Sharpe Ratio, Sortino Ratio, Calmar Ratio, Information Ratio |
| **시장 민감도** | Beta (vs S&P 500), Alpha (CAPM 기반 초과 수익률) |

---

## 🛠️ 기술 스택 (Tech Stack)

| 분류 | 기술 |
|------|------|
| **Language** | Python 3.10+ |
| **Data Processing** | pandas, numpy, scipy (XIRR 계산) |
| **Finance API** | yfinance (주가·환율·지수), FRED API (무위험 수익률 DTB3) |
| **UI** | Streamlit, Plotly |
| **AI / LLM** `🚧` | Google Gemini API, MCP (Model Context Protocol), FastMCP — **개발 중지** |
| **Packaging** | PyInstaller (.exe), PyWebView (네이티브 데스크탑 창) |
| **Caching** | 24h TTL 파일 캐시 (FRED + yfinance) |

---

## 📁 디렉토리 구조 (Directory Structure)

```
_02Allenz_Portfolio_Manager/
├── 01DATA/
│   ├── raw/               # HTS 원본 CSV 파일 (1750, 1721, 2610 등)
│   ├── processed/         # 파이프라인 생성 파일 (00~08)
│   ├── reference/         # AI 분석용 참조 PDF (팩트시트, 주주서한)
│   └── cache/             # API 캐시 (rf_cache.json, yf_prices.pkl)
├── 02src/
│   ├── config.py          # 전역 경로 설정 (Dev / Frozen 모드)
│   ├── data_loaders/      # ETL: parser · io · fred · trade_log
│   ├── engines/           # 계산 엔진: ledger · metrics · benchmark · history
│   ├── ai/                # AI 에이전트: agent · mcp_server · prompts
│   └── ui/                # 대시보드: app · portfolio · analytics · history_tab · data_manager
├── 03Output/              # AI 생성 리포트 (주주서한 .md)
├── logs/                  # AI 파이프라인 실행 로그
├── dist/                  # 빌드 산출물 (.exe)
├── main.py                # 앱 런처 (Streamlit + PyWebView)
├── update.py              # 파이프라인 오케스트레이터 (전체 순차 실행)
└── isin_mapping.json      # ISIN → Ticker 자동 매핑 (40+ 종목)
```

---

## 🔄 파이프라인 생성 파일 (Processed Data Files)

| 파일 | 생성 모듈 | 내용 |
|------|----------|------|
| `00Transaction_History.csv` | parser.py | 국내 ETF 거래 내역 |
| `01Asset_Summary.csv` | parser.py | 자산군별 요약 |
| `02Portfolio_Holdings.csv` | parser.py | 현재 보유 종목 스냅샷 |
| `03Full_Portfolio.csv` | parser.py | 국내+해외 통합 포트폴리오 |
| `04Daily_Asset_Ledger.csv` | ledger.py | 일별 자산 원장 (bottom-up 재구성) |
| `05Performance_Data.csv` | metrics.py | TWR / MWR / MDD / Sharpe 등 |
| `06Benchmark_Data.csv` | benchmark.py | SPY · QQQ · IWM 누적 수익률 |
| `07Historical_Holdings.csv` | history.py | 과거 시점별 포트폴리오 구성 (wide) |
| `08Equity_Trade_History.csv` | parser.py | 해외주식 매매 내역 |

---

## 🤖 AI 주주서한 생성 (AI Report Generation) `🚧 개발 중지`

> **현재 이 기능은 잠정 구현 중지 상태입니다.** 모듈 코드(`02src/ai/`)는 보존되어 있으며, 향후 재개 예정입니다.

설계된 파이프라인은 아래와 같습니다:

```
MCP Server (mcp_server.py)
    ↓  포트폴리오 데이터 (CSV) 노출
Google Gemini API
    ↓  참조 PDF (팩트시트, 과거 서한) File API 업로드
agent.py
    ↓  딥밸류 펀드매니저 페르소나 (prompts.py)
03Output/YYYY_QN_Shareholder_Letter.md
```

- **페르소나**: 저평가 소형주 중심 장기 가치투자자 (Bottom-up, Fundamental)
- **할루시네이션 방지**: 실제 데이터 외 수치 인용 엄격 금지 제약 내장
- **출력**: 투자 철학 · 포트폴리오 현황 · 종목별 투자 논거 · 시장 전망 포함 한국어 서한

---

## ▶️ 시작하기 (Quick Start)

### 1. 환경 설정

```bash
git clone https://github.com/AllenJenix/AllenJenix-PortfolioManager.git
cd _02Allenz_Portfolio_Manager
pip install -r requirements.txt
```

`.env` 파일에 API 키 설정:
```
FRED_API_KEY=your_fred_api_key

# 아래 키는 AI 주주서한 기능(현재 개발 중지) 재개 시 필요
# GOOGLE_API_KEY=your_gemini_api_key
```

### 2. 원본 데이터 준비

`01DATA/raw/` 폴더에 HTS 내보내기 파일 배치:
- `1750.csv` — 국내 거래 내역
- `1721.csv` — 자산 현황 / 보유 종목
- `2610.csv` — 해외주식 매매 내역

### 3. 전체 파이프라인 실행 (원클릭)

```bash
python update.py
```

### 4. 대시보드 실행

```bash
streamlit run 02src/ui/app.py
# 또는 데스크탑 앱으로
python main.py
```

### 5. (미구현) AI 주주서한 생성

> ⚠️ **이 기능은 현재 개발 중지 상태입니다.** 아래 명령은 아직 사용 불가합니다.

```bash
# python 02src/ai/agent.py  ← 미구현, 실행 불가
```

---

## 🖥️ 대시보드 탭 구성

| 탭 | 기능 |
|----|------|
| **Portfolio** | 현재 보유 종목 도넛 차트 · 평가금액 · 현금 비중 |
| **Analytics** | 포트폴리오 vs SPY/QQQ/IWM 누적 수익률 비교 (동적 Rebasing) · XIRR |
| **History** | 날짜 슬라이더 → 과거 임의 시점 포트폴리오 구성 복원 |
| **Data Manager** | HTS 파일 업로드 → 파이프라인 실행 트리거 |

---

## 📄 라이선스

[MIT License](LICENSE) © 2026 Allen Jenix
