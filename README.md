📈 Portfolio Manager (Data ETL & Analysis Engine)
=================================================
![Development Status](https://img.shields.io/badge/Status-Work_in_Progress-yellow) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

개인 투자 포트폴리오의 **성과 분석 및 리포팅**을 위한 데이터 파이프라인/엔진입니다.  
증권사 HTS/MTS에서 내려받은 **비정형 CSV 원본 데이터**를 자동 전처리(ETL)하여,  
정확한 수익률(TWR, MWR/XIRR)과 리스크(MDD)를 산출하고, 과거 포트폴리오 상태를 복원(Time Machine)하는 것을 목표로 합니다.

> **"Raw 데이터에서 알파를 찾다"**  
> 비정형 HTS/MTS 거래 내역을 정제하여 객관적인 투자 성과를 리포팅하고 관리하는 엔지니어링 프로젝트입니다.

---

## 📌 1. 프로젝트 개요 (Overview)

증권사에서 제공하는 데이터는 대개 **파편화**되어 있고,  
입출금이 잦은 개인 투자자의 경우에는:

- **운용 실력(TWR)** 과
- **자금 운용 성과(MWR, XIRR)** 를 명확히 구분하기 어렵습니다.

이 프로젝트는 이러한 **데이터의 불투명성을 엔지니어링으로 해결**하고,  
궁극적으로는 LLM을 활용한 **개인화된 투자 리포팅 시스템**까지 확장하는 것을 목표로 합니다.

현재 레포지토리는 다음과 같은 핵심 로직을 포함합니다.

- HTS/MTS 거래 내역 Raw CSV → **표준화된 거래 히스토리**
- 월간 자산 요약 CSV → **정제된 Asset Summary**
- 위 두 데이터를 기반으로 한 **일별 자산 원장(Daily Ledger) 및 성과 지표 계산 엔진**

---

## 🛠 2. Tech Stack

- **Language**: Python 3.x
- **Data Processing**: `Pandas`, `NumPy`
- **Analysis / Math**: `SciPy` (XIRR 등, 계획/부분사용), `NumPy`
- **Visualization**: `Matplotlib`, `Seaborn` (Roadmap 단계)
- **Environment**: Jupyter Notebook (`_00TEST/TEST.ipynb`)

---

## 🔍 3. 핵심 기술적 도전 (Technical Highlights)

단순 엑셀 정리 수준이 아닌, **증권사 전용 포맷에 특화된 ETL + 금융 분석 로직**을 직접 구현했습니다.

- **비정형 CSV 파싱**
  - 한 건의 거래가 **2행(상세 + 메타 정보)에 걸쳐 있는 2-Row-Per-Transaction 구조**
  - `load_hts_dynamic_final()` 함수에서:
    - 헤더(상/하단) 위치를 동적으로 탐지 (`get_header_map`)
    - 각 행이 **날짜 패턴인지 (`YYYY/MM/DD`)** 판별하여 데이터 행만 인식
    - 2개의 행(Row1/Row2)을 하나의 레코드(dict)로 병합 후 DataFrame으로 변환
  - 결과는 `_00TEST/01DATA/00Transaction_History.csv` 로 저장

- **자산 요약 ETL**
  - 월말 기준의 자산 요약 CSV(순자산, 입금/출금, 손익, 수익률 등)를 정제
  - `load_asset_summary()` 함수에서:
    - `"조회일자"`가 포함된 헤더 행을 자동 탐지
    - `clean_asset_number()` 로 `"15,892,620."`, `"21.80%"`, `"."` 등의 특수 숫자 형식을 float로 정규화
    - `조회일자`는 날짜로 파싱하여 시계열 분석에 바로 사용 가능하도록 정리
  - 결과는 `_00TEST/01DATA/01Asset_Summary.csv` 로 저장

- **금융 분석 엔진 (설계/구현 진행 중)**
  - 거래 히스토리 + 월간 자산 스냅샷을 결합해:
    - **Daily Asset Ledger** (일별 자산 잔고, 입출금, 평가손익 분해)
    - **성과 지표**:  
      - TWR (Time-Weighted Return, 운용 실력)  
      - MWR / XIRR (Money-Weighted Return, 자금 투입 타이밍 반영)  
      - MDD (Maximum Drawdown, 최대 낙폭)
  - 일부 로직은 `_00TEST/TEST.ipynb` 에 구현되어 있으며, 향후 `.py` 모듈로 분리 예정

---

## 🧱 4. 데이터 파이프라인 (System Architecture)

데이터 파이프라인은 **원본 → 정제된 중간 산출물 → 분석 지표** 순으로 단계적으로 진행됩니다.

1. **Stage 0 – Raw Ingestion**
   - 입력 파일:
     - `_00TEST/00RAW_DATA/1750.csv` : HTS 거래 내역 원본
     - `_00TEST/00RAW_DATA/1721.csv` : 월간 자산 요약 원본
     - `_00TEST/00RAW_DATA/17100001.csv` : 추가 자산/거래 관련 Raw (테스트용)
   - 인코딩: `cp949` (국내 증권사 CSV 기본값)

2. **Stage 1 – Transaction History ETL**
   - 노트북: `_00TEST/TEST.ipynb`
   - 주요 함수: `load_hts_dynamic_final(file_path)`
   - 출력:
     - `_00TEST/01DATA/00Transaction_History.csv`
   - 컬럼 예시:
     - `일자`, `구분`, `종목번호`, `수량`, `거래대금`, `수수료`, `가격`, `최종금액`, `대체계좌/채널`, `통화` 등 총 26개 컬럼

3. **Stage 2 – Asset Summary ETL**
   - 노트북: `_00TEST/TEST.ipynb`
   - 주요 함수: `load_asset_summary(file_path)`
   - 출력:
     - `_00TEST/01DATA/01Asset_Summary.csv`
   - 대표 컬럼:
     - `조회일자`, `순자산`, `입금고`, `출금고`, `손익`, `수익률`,  
       `자산`, `부채`, `예수금잔고`, `위탁순자산`, `상품잔고`, `누적손익`, `누적수익률` 등

4. **Stage 3 – Portfolio Integration (WIP)**
   - 목표:
     - 거래 기반의 `Portfolio Holdings` 와 자산 요약을 결합
     - 현금 / RP / 주식 / 금융상품 등 자산 카테고리별로 통합 포트폴리오 생성
   - 타겟 파일 (명세상):
     - `_00TEST/01DATA/02Portfolio_Holdings.csv`
     - `_00TEST/01DATA/03Portfolio_with_Cash.csv`

5. **Stage 4 – Daily Asset Ledger (WIP)**
   - 목표:
     - 월말 자산 요약(Anchor) + 일별 거래 흐름(Flow)를 결합해 **일별 자산 원장** 생성
     - 입출금/평가손익을 분리하여 **실제 운용 성과 vs 자금 이동 효과**를 분해
   - 타겟 파일 (명세상):
     - `_00TEST/01DATA/04Daily_Asset_Ledger.csv`
     - `_00TEST/06Daily_Holdings_Timeline.csv`

6. **Stage 5 – Performance Analytics (WIP)**
   - 목표:
     - `05Performance_Data.csv` 등을 생성하여:
       - TWR, MWR(XIRR), MDD, 변동성 등 지표 테이블 구성
       - 벤치마크(S&P 500, Russell 2000 등)와 비교하여 Alpha 산출

---

## 📂 5. 디렉터리 구조

```text
Value-Quant-reports/
├─ _00TEST/
│  ├─ 00RAW_DATA/
│  │  ├─ 17100001.csv
│  │  ├─ 1721.csv
│  │  └─ 1750.csv
│  ├─ 01DATA/
│  │  ├─ 00Transaction_History.csv
│  │  ├─ 01Asset_Summary.csv
│  │  ├─ 02Portfolio_Holdings.csv
│  │  ├─ 03Portfolio_with_Cash.csv
│  │  ├─ 04Daily_Asset_Ledger.csv
│  │  └─ 05Performance_Data.csv
│  ├─ 06Daily_Holdings_Timeline.csv
│  ├─ TEST.ipynb
│  ├─ extract_asset.py
│  └─ extract_transaction.py
├─ _01Obsidian/
│  └─ Obsidian Vault/
│     ├─ .obsidian/
│     ├─ 00Master/
│     │  └─ Investment Portfolio Manager.md
│     └─ 01DayMemo/
│        ├─ _Format.md
│        ├─ 2026-01-22.md
│        └─ 2026-01-24.md
├─ .gitignore
├─ LICENSE
└─ README.md
```
--- 
## ▶️ 6. 사용 방법 (Quick Start)

이 프로젝트는 Python 환경에서 실행됩니다. 아래 절차에 따라 환경을 설정하고 분석을 시작해 보세요.

### 6.1. 환경 설정 (Environment Setup)

**1. Python 설치**
Python 3.x 버전이 설치되어 있어야 합니다.

**2. 가상환경 생성 (권장)**
프로젝트 격리를 위해 가상환경 사용을 권장합니다.

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

**3. 필수 패키지 설치**
분석 및 시각화에 필요한 라이브러리를 설치합니다.

```bash
pip install pandas numpy scipy matplotlib jupyter
```

### 6.2. 실행 (Run)
Jupyter Notebook을 실행하여 테스트 코드를 확인합니다.

```bash
jupyter notebook _00TEST/TEST.ipynb
```

---

## 🗺️ 7. 개발 로드맵 (Roadmap)

현재 **Phase 1** 단계가 진행 중이며, 데이터 정합성 확보 후 AI 기반 리포팅 기능을 도입할 예정입니다.

### Phase 1: 분석 엔진 고도화 (Current) 🚧
- [x] **HTS 거래 내역 ETL**: 신한투자증권 거래내역 파싱 및 전처리
- [x] **자산 요약(Asset Summary) ETL**: 일별 자산 평가액 및 변동 내역 데이터 파이프라인 구축

### Phase 2: 데이터 정밀도 강화 (Next)
- [ ] **Portfolio Time-Machine**: 과거 특정 시점의 포트폴리오 상태 복원 기능
- [ ] **FIFO Ledger**: 매매 차익 계산을 위한 선입선출(First-In-First-Out) 장부 로직 구현

### Phase 3: AI 리포팅 서비스 (Future)
- [ ] **AI 주주서한**: 포트폴리오 성과 및 변동 원인을 분석하는 LLM 기반 자동 리포트
- [ ] **Benchmark Alpha 분석**: Benchmark 대비 초과 수익률(Alpha) 심층 분석