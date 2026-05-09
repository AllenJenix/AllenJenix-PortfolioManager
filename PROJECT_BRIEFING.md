# Allenz Portfolio Manager — Project Briefing
> 최초 작성: 2026-05-06 | 최종 업데이트: 2026-05-09 (Phase 3 Ledger v2 완료)  
> 작성자: Claude (Cowork Senior Mentor Session)  
> 용도: Claude Code 세션 인계용 컨텍스트 문서. 각 섹션의 "Claude Code 작업 지시문"을 그대로 붙여넣어 사용.

---

## 1. 프로젝트 개요

**목표:** 개인 포트폴리오 관리 시스템을 단계적으로 기관급(Institutional-grade) 수준으로 발전시키는 것. 현재는 프로토타입 검증 단계.

**투자 철학:**
- Bottom-up, Deep Value, Small-cap 전략
- Peter Lynch / Mohnish Pabrai / Warren Buffett / Charlie Munger / Martin Whitman 영향
- "Alpha는 매크로 노이즈를 무시하고, 순수 펀더멘털 분석에서 나온다"

---

## 2. 기술 스택 및 아키텍처

### 디렉토리 구조
```
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
    │   │   ├── fred.py            # ✅ FRED/yfinance Rf 조회 모듈
    │   │   └── trade_log.py       # ✅ SSOT 통합 거래 로그 (2610+1750, ledger/history 공통 참조)
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

### 데이터 파이프라인 (순차 의존 관계)
```
HTS 다운로드(raw) → parser.py → 00~03.csv
                                    ↓
                              ledger.py → 04Daily_Asset_Ledger.csv
                                    ↓
                              metrics.py → 05Performance_Data.csv
                                    ↓
                             benchmark.py → 06Benchmark_Data.csv
```

### 핵심 설계 사항
- **ledger.py 보간 방식:** HTS에서 월 1회 스냅샷(`01Asset_Summary.csv`)을 받아 월간 손익을 일수로 균등 분배하는 직선 보간(`daily_gain = valuation_gain / n_days`). TWR 정확도는 앵커 밀도에 비례함.
- **배포:** PyInstaller `.exe` 빌드 완료 (`dist/Allenz_Portfolio_Manager.exe`)
- **AI 스택:** 현재 `gemini-2.5-pro` → **Claude(Anthropic API)로 전환 예정**

---

## 3. 성과 지표 현황

| 지표 | 구현 | 신뢰도 | 비고 |
|------|------|--------|------|
| TWR (시간가중수익률) | ✅ | ⚠️ | **BUG-01 수정 후 ~44% 예상** |
| CAGR (연환산 복리 수익률) | ✅ | ⚠️ | TWR 기반, BUG-01 수정 연동 |
| MWR / XIRR (금액가중수익률) | ✅ | ⚠️ | brentq→newton 2-tier 솔버. BUG-01 수정 연동 |
| MDD (최대낙폭) | ✅ | ✅ | Wealth Index 기준, 입출금 왜곡 없음 |
| Sharpe Ratio | ✅ | ⚠️ | **BUG-01 수정 필요** (현재 보간 왜곡으로 과대계상) |
| Sortino Ratio | ✅ | ⚠️ | **BUG-01 수정 필요** |
| Calmar Ratio | ✅ | ⚠️ | CAGR 기반, BUG-01 수정 연동 |
| Information Ratio | ✅ | ⚠️ | 일별 TE 기반, 보간 왜곡 잔존. Phase 3 전까지 참고용 |
| Beta / Alpha (CAPM) | ✅ | ⚠️ | 월별 수익률 기반으로 개선 (0.0002 → 0.12). 앵커 17개 한계로 과소추정 잔존 |
| VaR / CVaR | ❌ | — | Phase 2 |

---

## 4. 버그 트래커

### ✅ [RESOLVED] XIRR 솔버 교체 (2026-05-07)
`scipy.optimize.newton` → `brentq`(1차) + `newton`(fallback) 2-tier 구조 교체 완료.
엣지케이스(동일 부호 현금흐름, 1일 기간) 처리 포함.

### ✅ [RESOLVED] MDD Wealth Index 검증 (2026-05-07)
Wealth Index `(1+r1)*(1+r2)*...` 기준 MDD 구현 확인. 입출금 왜곡 없음.

### ✅ [RESOLVED] BUG-01: TWR 과소계상 + Sharpe/Sortino 과대계상 (2026-05-08)

**원인:** `ledger.py` 직선 보간 + `business_days_only=True` 조합이 두 가지 문제 동시 발생.
- 매일 동일한 보간값 → 수익률 분산 ≈ 0 → Sharpe/Sortino 폭등
- `business_days_only=True` 적용 시 External_Flow 타이밍 왜곡 → TWR 과소계상

**수정 내용:**
- `ledger.py`: `business_days_only=False` 롤백 → TWR 복구 (42.45%)
- `metrics.py`: Sharpe/Sortino를 월별 수익률(`monthly_r`) 기반으로 전환 → 보간 왜곡 차단

**최종 수치 (수정 후):**

| 지표 | 값 | 비고 |
|------|----|------|
| TWR | **42.45%** | HTS chain-linked 44.02% 대비 오차 ~1.6%p, 허용 범위 |
| Sharpe | **~1.07** | 월별 σ 기반, 보간 왜곡 제거 |
| Sortino | **~3.70** | 월별 하락 σ 기반 (하락월 표본 적음 → 여전히 높음, 허용) |

---

### ✅ [RESOLVED] 1750_kr 결제금액 누락 → Cash 음수 → Phantom MDD (2026-05-10)

**원인:** `_load_1750_kr_trades()`가 `settlement_date = NaT`, `settlement_amount = NaN`으로 반환 → 한국 ETF 매수 대금이 `build_daily_trade_cash_flows()`에서 집계되지 않음 → `daily_unexplained` 잔차에 ETF 매수 금액 전액이 포함 → 앵커 구간 전체에 역방향 균등 분배 → 구간 내 Cash가 일별 -160,186씩 감소 → May 7–14 Cash 음수(-1.17M KRW) → Phantom MDD.

**수정 내용 (`data_loaders/trade_log.py`):**
1. `_load_1750_kr_trades()`: T+2 영업일 `settlement_date` + `변동금액` 기반 `settlement_amount` 추가
2. `build_daily_trade_cash_flows()`: `source == '2610'` 필터 제거 → 1750_kr 결제일 현금흐름 포함
3. **버그 수정:** `pd.to_numeric(...values...).abs()` → `pd.to_numeric(...).abs()` (ndarray→Series, `.abs()` 미지원 오류 제거)

**연관 수정 (`engines/ledger.py`, `engines/history.py`):**
- `_build_daily_holdings()`: `settlement_date.fillna(date)` effective_date 기준으로 보유 수량 산출 (T+0/T+2 phantom drawdown 제거)
- `generate_timeline()`: ledger.py와 동일한 effective_date 로직으로 동기화

**아키텍처 개선:** `data_loaders/trade_log.py` SSOT 모듈 신설. `ledger.py`와 `history.py`가 동일한 통합 거래 로그(`build_unified_trade_log`)를 공통 참조.

---

### 🔍 [BUG-03] MDD 수치 변동 — Bottom-Up 전환 후 검토 필요 (2026-05-09)

**증상:** Ledger v2(Bottom-Up) 전환 후 MDD가 이전 대비 크게 변동.

| 구분 | 값 | 방식 |
|---|---|---|
| 이전 (선형 보간) | ~-15% | 월별 앵커 사이 직선 보간 → 인위적 평탄화 |
| 현재 (Bottom-Up v2) | **-35.51%** | 실제 주가×수량 기반 Equity_Value 계산 |

**가설 1 (보간 과소계상):** 선형 보간은 월간 앵커 사이 실제 주가 등락을 무시하므로 MDD가 구조적으로 과소계상됨. 15%는 하한선(floor)에 가까운 인위적 수치였을 가능성 높음.

**가설 2 (Bottom-Up 과대계상):** 현재 현금 보정 로직의 구조적 한계. 주식 매도 시 매도 대금이 즉시 현금으로 반영되지 않고 앵커 구간 잔여 일수에 선형 분배됨 → 매도 당일 Calculated_Asset이 일시적으로 낮아지는 인위적 낙폭 발생. 특히 구간 후반부 대량 매도 시 왜곡 심화.

**예시 (검증됨):** 2025-07-24 A466940 177주 매도 당일 일별 수익률 -10.7% 기록. 실제 포트폴리오는 Jun30/Jul31 앵커 모두 24.2M으로 당월 평보합이었음에도, 매도 당일 equity 급감 + 현금 지연 반영으로 Calculated_Asset이 ~30M → ~27M으로 하락한 것처럼 계산됨.

**결론:** 실제 MDD는 15%(과소)~35.51%(과대) 사이 어딘가에 위치할 것으로 추정. 정확한 MDD 산출을 위해서는 매도 당일 현금 즉시 반영 로직(결제일 기준 현금 플로우 추적)이 필요. Phase 3 고도화 항목으로 등록.

**현재 대응:** UI 출력에 "(참고용, 현금 지연 반영 한계)" 주석 표기 권장.

---

### 🟡 [BUG-02] Beta / Alpha / IR 수치 신뢰 부족 — 선형 보간의 구조적 한계 (부분 개선)

**벤치마크 SPY는 올바름.** 포트폴리오는 미국 주식 중심(일본 1종목)이므로 SPY가 적합한 벤치마크임.

**진짜 원인:**
Beta = `Cov(포트폴리오 수익률, SPY 수익률) / Var(SPY 수익률)`

포트폴리오 일별 수익률이 선형 보간으로 생성된 근-상수값이라 `Cov ≈ 0`으로 수렴.
Beta ≈ 0은 포트폴리오가 SPY와 무관해서가 아니라, 일별 변동성 정보 자체가 없기 때문.

**임시 처방 적용 (2026-05-09):**
`metrics.py` Beta 계산을 일별 → **월별 수익률 기반**으로 전환.
- 포트폴리오: `monthly_r` (Sharpe/Sortino와 동일 기준)
- 벤치마크: SPY 일별 → `(1+r).prod()-1` 월별 집계 후 inner join
- 최소 관측치: 6개월

**결과:**

| 항목 | 수정 전 | 수정 후 | 비고 |
|------|---------|---------|------|
| Beta (SPY) | 0.0002 | **~0.12** | 개선됨. 미국 주식 포트폴리오 기대값(0.8~1.3) 대비 여전히 과소추정 |
| 잔존 원인 | — | 월별 앵커 ~17개 | 표본 부족 + 보간 아키텍처 한계 |

**IR(Information Ratio):** Tracking Error가 일별 excess return 기반이라 동일한 보간 왜곡 잔존. 현재 참고용 수준.

**결론:** Beta / Alpha / IR은 **Phase 3 bottom-up 일별 재구성 전까지 참고용.**
UI 출력에 "(참고용, 보간 한계)" 주석 표기 권장.

---

## 5. 완료된 주요 구현

### ✅ Phase 3 — Ledger v2 Bottom-Up Reconstruction (2026-05-09)

**파일:** `engines/ledger.py` (전면 재작성), `engines/history.py` (effective_date 동기화), `data_loaders/trade_log.py` (SSOT 신설), `data_loaders/parser.py`, `config.py`, `isin_mapping.json`

**핵심 변경:**
- HTS 2610.csv (해외주식매매내역) 통합: 매매일 기준 221건, Jan 2025 ~ Apr 2026 전구간 커버
- 한국 ETF 보완: 1750.csv 장내_매수/매도 11건 (A466940, A494670)
- `_build_unified_trade_log()` → `_build_daily_holdings()` → yfinance 가격조회 → KRW 환산 파이프라인 구축
- HTS 앵커(월말 NAV) 기반 Cash 보정: 구간별 외부자금흐름 정확 반영 + 잔차(FX·배당) 균등 배분

**ISIN 티커 해결 로직 (`_resolve_tickers`):**

| 통화 | 규칙 | 예시 |
|---|---|---|
| USD | `isin_mapping` 키 존재 시 우선 적용, 없으면 2610 티커 fallback | BRK.B→BRK-B, AMRZ.SW→AMRZ |
| JPY | 2610 티커 + `.T` 접미사 | `3093` → `3093.T` |
| KRW | `isin_mapping` `.KS` 티커 | `A466940` → `466940.KS` |

**데이터 품질 이슈 해결:**
- CHR (CHEER HOLDING INC, `KYG399732042`): 역분할(Reverse Split)로 yfinance 역사 가격이 $24 (실제 거래가 $0.167)로 왜곡 → `isin_mapping`에서 `""` 처리(의도적 제외). 실질 포지션 net=0 (Oct 7 매수 → Oct 8 매도)이므로 앵커 보정으로 흡수됨.
- `02src/isin_mapping.json` 신규 엔트리: Korean ETF(466940.KS, 494670.KS), ITRN, LEN, LW, BMI, INVE. 루트 `isin_mapping.json`과 동기화 완료.

**최종 성과 지표 (Bottom-Up v2 기준):**

| 지표 | 값 | 비고 |
|---|---|---|
| TWR | **33.79%** | 이전 42.45% 대비 하락 → Bottom-Up이 외부자금 타이밍을 더 정밀하게 반영 |
| CAGR | **24.05%** | |
| MWR | **42.71%** | |
| MDD | **재실행 필요** | 1750_kr 결제금액 수정 전 수치(-35.51%). 수정 후 파이프라인 재실행 필요 |
| Sharpe | **0.81** | |
| Sortino | **3.17** | |
| Alpha (SPY) | **+19.52%** | |

**알려진 한계:**
- Jan 2025: Dec 2024 보유 포지션(USLM/FIX/CPNG/IGIC)이 2610.csv 커버리지 밖(매매일 Dec 2024) → 해당월 Equity_Value 과소계상, Jan 31 앵커 보정으로 흡수
- MDD 과대계상 가능성 (BUG-03 참조)

---

### ✅ Beta 월별 수익률 기반 전환 (2026-05-09)
**파일:** `engines/metrics.py` — Beta 계산 섹션

일별 `rp_series` vs `rb_series` 기반 계산을 월별 집계 수익률로 전환.
- 포트폴리오 월별: `monthly_r` (Sharpe/Sortino와 동일 기준, `(1+r).prod()-1`)
- 벤치마크 월별: SPY 일별 → 월별 집계 후 Period index 기준 inner join
- 최소 관측치 기준: `MIN_MONTHS = 6`
- 결과: 0.0002 → ~0.12 (방향성 개선, 앵커 17개 한계로 과소추정 잔존)

Alpha(Jensen's)는 Beta에 자동 연동되어 별도 수정 불필요.
IR Tracking Error는 일별 기반 유지 (사용자 요청 범위 외).

---

### ✅ FRED 무위험이자율 조회 모듈 (2026-05-08)
**파일:** `data_loaders/fred.py`

조회 우선순위: 파일 캐시(24h TTL) → FRED API(`DTB3`) → yfinance(`^IRX`) → 하드코딩 fallback(4.5%)

```python
# metrics.py에서 사용법
from data_loaders.fred import get_risk_free_rate
rf = get_risk_free_rate()   # 예: 0.036 = 3.6%
```

- FRED API Key 발급(무료): https://fredaccount.stlouisfed.org/apikeys
- `.env`에 `FRED_API_KEY=xxx` 추가 시 FRED 우선 사용
- 캐시 위치: `01DATA/cache/rf_cache.json`
- `config.py`에 `RISK_FREE_RATE_FALLBACK = 0.045`, `CACHE_DIR` 추가 완료

---

## 6. Phase별 로드맵

### Phase 1 — 진행 중

| 항목 | 상태 | 비고 |
|------|------|------|
| XIRR 솔버 안정화 | ✅ 완료 | brentq 2-tier |
| MDD Wealth Index 검증 | ✅ 완료 | |
| CAGR / Sharpe / Sortino / Calmar / IR / Beta / Alpha 구현 | ✅ 완료 | — |
| FRED Rf 조회 모듈 | ✅ 완료 | `data_loaders/fred.py` |
| **BUG-01: ledger 롤백 + Sharpe/Sortino 월별 전환** | ✅ 완료 | TWR 42.45%, Sharpe ~1.07 |
| **BUG-02: Beta 월별 수익률 기반 전환** | 🟡 부분 완료 | 0.0002 → 0.12, 완전 해결은 Phase 3 |
| DuckDB 도입 검토 | ⏸ 보류 | CSV 파이프라인 안정화 후 |
| **Phase 3 Ledger v2 — 2610 기반 Bottom-Up 재구성** | ✅ 완료 | TWR 33.79%, MDD 재실행 필요 (BUG-03 + 1750_kr 수정 후) |
| **SSOT trade_log.py + 1750_kr 결제금액 + effective_date 통일** | ✅ 완료 | Phantom MDD 원인(음수 Cash) 제거, ndarray .abs() 수정 |

### Phase 2 — 중기

| 기능 | 비고 |
|------|------|
| Factor Attribution (Fama-French 3-factor) | Small-cap Effect 철학과 정합. Kenneth French 데이터 무료 |
| VaR / CVaR 엔진 | 소형주 Tail Risk 측정 |
| AI Agent → Claude 전환 | `agent.py` Anthropic SDK 재구성 (아래 지시문 참조) |
| Obsidian ↔ Python 연동 | Daily Memo → Transaction rationale 자동 파싱 |
| 자동 스케줄링 | 월말 전체 파이프라인 자동 실행 (Cowork Schedule Skill 연동) |

### Phase 3 — 장기

| 기능 | 비고 |
|------|------|
| Position Sizing 최적화 | Kelly Criterion / Black-Litterman |
| Watch-list 자동 스크리닝 | yfinance + Value 필터 (P/B, EV/EBIT, Net-Net) |
| Capital IQ 실시간 연동 | Cowork `sp-global` 플러그인 → MCP Tool 등록 |
| RAG 기반 투자 메모 검색 | Obsidian 볼트 → chromadb/faiss 인덱싱 |
| ✅ Ledger 아키텍처 개선 | 월별 보간 → 거래 기반 bottom-up 재구성 완료 (2610.csv 매매일 기준). 다음 단계: 매도 당일 현금 즉시 반영 (BUG-03 해결) |

---

## 7. 데이터 소스 현황

| 소스 | 상태 | 용도 |
|------|------|------|
| HTS (국내 증권사) | ✅ 사용 중 | 거래내역/잔고 원본 (cp949 인코딩) |
| yfinance | ✅ 사용 중 | SPY/QQQ/IWM 벤치마크, ^IRX Rf fallback |
| FRED API | ✅ 구현됨 | 3M T-Bill Rf (DTB3), Key 발급 완료 |
| S&P Capital IQ (Cowork 플러그인) | ✅ 설치됨, 미활용 | 재무제표, 밸류에이션, 기업 프로필 |
| Norgate Data | 🔍 검토 중 | 히스토리컬 point-in-time 데이터 (백테스팅 전용) |
| Fama-French 데이터 | ❌ 미확보 | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ 무료 |

---

## 8. 코딩 컨벤션

- **언어:** Python 3.11+, PEP 8, OOP 원칙
- **파일 헤더:** `@Title`, `@Description`, `@Author`, `@Date` docstring 필수
- **섹션:** `# 1. Imports` → `# 2. Constants` → `# 3. Helper Functions` → `# 4. Main Logic` → `# 5. Execution Block`
- **모듈 태그:** `MODULE_TAG = "[ModuleName]"` 상수 → 모든 출력 prefix
- **출력 컨벤션:** `✅ 완료`, `❌ 오류`, `⚠️ 경고`, `🚀 시작`, `📊 결과`
- **경로:** `config.py` 상수만 참조, 하드코딩 금지
- **인코딩:** HTS 원본 = `cp949` / 내부 표준 = `utf-8-sig`

---

## 9. AI Agent 전환 계획 (Gemini → Claude)

**현재 구현 수준:**
- MCP Client-Server 패턴: `agent.py`에서 실전 구현 완료 (`ClientSession`, `call_tool`, `read_resource`)
- RAG 기초: CSV 데이터를 프롬프트에 주입하는 방식으로 구현 중
- 이론적 깊이(MCP Tool 정의, 벡터 DB) 추가 학습 필요

**Claude Code 작업 지시문 (AI Agent 전환 시):**
> `_02Allenz_Portfolio_Manager/02src/ai/agent.py`를 Google GenAI SDK에서 Anthropic SDK(`anthropic` 패키지)로 전환해줘. `gemini-2.5-pro` 모델 호출을 `claude-opus-4-6` 또는 `claude-sonnet-4-6`로 교체하고, PDF는 base64 인코딩 후 Claude의 `document` content block으로 전달해줘. MCP 구조(`ClientSession`, `call_tool`, `read_resource`)는 그대로 유지. `.env` 키를 `ANTHROPIC_API_KEY`로 교체. 기존 `logging` 모듈과 `MODULE_TAG` 컨벤션 유지.

**다음 학습 포인트:**
1. MCP Tool 정의 심화 → `mcp_server.py`에 신규 Tool 추가
2. RAG 심화 → chromadb + Obsidian 볼트 인덱싱
3. Claude Agent SDK → agentic loop 재설계

---

*Claude Code 세션 시작 시 `@PROJECT_BRIEFING.md`로 이 파일을 참조하면 컨텍스트가 유지됩니다.*
