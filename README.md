# 📈 Allenz Portfolio Manager
![Development Status](https://img.shields.io/badge/Status-Active_Development-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)

개인 투자 포트폴리오의 **전문적인 성과 분석 및 시각화**를 돕는 투자 관리 애플리케이션입니다.

증권사 HTS의 비정형 원본 데이터를 자동 전처리(ETL)하고, 객관적인 성과 지표(TWR, MWR, MDD)를 산출하며, 과거의 포트폴리오 스냅샷(Historical Holdings)을 완벽하게 복원하여 투자 내역을 직관적으로 관리할 수 있도록 지원합니다. 차후 고도화된 분석 기능들을 지속적으로 추가할 예정입니다.

---

## 📌 1. 프로젝트 핵심 기능 (Key Features)

* **Robust Data Pipeline (ETL)**: 한글 인코딩('cp949'/'utf-8') 자동 감지 및 HTS 특유의 불필요한 메타데이터, 다중 행(Multi-line) 헤더를 깔끔하게 정제하는 파서(Parser) 내장.
* **Performance Metrics**: 단순 평가손익이 아닌, 입출금 현금흐름(Cash Flow)을 분리하여 순수 운용 실력을 평가하는 **시간가중수익률(TWR)**과 체감 수익률인 **금액가중수익률(MWR/XIRR)** 산출.
* **Dynamic Rebasing & Benchmark**: S&P 500(SPY), Nasdaq 100(QQQ) 등 시장 지수를 'yfinance'로 수집하여 내 포트폴리오와 비교. 조회 기간 변경 시 시작점을 0%로 실시간 재조정(Dynamic Rebasing)하여 초과 수익률(Alpha) 측정.
* **Historical Holdings (과거 포트폴리오 복원)**: 현재 잔고를 기준점(Anchor)으로 삼아 과거의 거래 내역을 역산(Reverse Engineering)하고 과거 주가/환율을 매핑하여, **과거 특정 시점의 주식 및 현금 비중을 100% 복원**해내는 기능.
* **Interactive Web Dashboard**: 'Streamlit'과 'Plotly'를 기반으로 한 3-Tab 멀티 페이지 관제탑 제공.

---

## 🏗️ 2. 시스템 아키텍처 (Layered Architecture)

프로젝트는 유지보수성과 확장성을 위해 **3-Tier 아키텍처**로 분리되어 있습니다. (상세 내역은 'FILE_TREE.md' 참조)

1. **Layer 1: Data Loaders ('data_loaders/')**
   * HTS 원본 파일 ➡️ 시스템 표준 CSV 파일로 변환
2. **Layer 2: Calculation Engines ('engines/')**
   * 'ledger.py': 일별 자산 원장 생성 및 하이브리드 보간
   * 'metrics.py': TWR, MWR, MDD 산출
   * 'benchmark.py': 시장 지수 API 연동
   * 'history.py': 과거 포트폴리오 역산 (Historical Holdings)
3. **Layer 3: UI Dashboard ('ui/')**
   * 사용자 친화적인 웹 기반 인터랙티브 대시보드 ('app.py' 라우팅)

---

## 🛠️ 3. 기술 스택 (Tech Stack)

* **Language**: Python 3.10+
* **Data Processing**: 'pandas', 'numpy'
* **Finance API**: 'yfinance' (과거 주가, 환율 및 벤치마크 지수 수집)
* **Frontend / UI**: 'Streamlit' (웹 프레임워크), 'Plotly' (인터랙티브 차트 시각화)

---

## ▶️ 4. 시작하기 (Quick Start)

본 프로젝트는 파이썬 환경에서 구동됩니다. 아래 명령어들을 터미널에 입력하여 대시보드를 실행할 수 있습니다.

### 설치 및 환경 구성
```bash
# 1. 저장소 클론
git clone https://github.com/your-repo/Allenz_Portfolio_Manager.git
cd Allenz_Portfolio_Manager

# 2. 필수 라이브러리 설치
pip install -r requirements.txt
```

### 파이프라인 가동 및 대시보드 실행
*'01DATA/raw/' 폴더에 HTS 원본 파일(1750, 1721, 17100001)이 준비되어 있어야 합니다.*

```bash
# 1. 데이터 파싱
python 02src/data_loaders/parser.py

# 2. 백엔드 엔진 순차 실행
python 02src/engines/ledger.py
python 02src/engines/metrics.py
python 02src/engines/benchmark.py
python 02src/engines/history.py

# 3. Streamlit 웹 대시보드 런칭! 🚀
streamlit run 02src/ui/app.py
```
*(향후 단일 명령어로 전체 파이프라인을 실행하는 'update.py' 스크립트가 추가될 예정입니다.)*