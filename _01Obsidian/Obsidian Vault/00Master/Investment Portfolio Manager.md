# 🛠️ Portfolio Manager Project (v1.0)
> **"Raw 데이터에서 알파를 찾다"** > 비정형 HTS/MTS 거래 내역을 정제하여 객관적인 투자 성과를 리포팅하고 관리하는 엔지니어링 프로젝트입니다.

---

## 📌 1. 프로젝트 개요 (Overview)
증권사에서 제공하는 데이터는 대개 파편화되어 있으며, 입출금이 잦은 개인 투자자의 경우 '진짜 실력(TWR)'과 '자금 운용 성과(MWR)'를 구분하기 어렵습니다. 이 프로젝트는 이러한 **데이터의 불투명성을 엔지니어링으로 해결**하고, 나아가 LLM을 활용한 개인화된 리포팅 시스템 구축을 목표로 합니다.

## 🛠️ 2. 핵심 기술적 도전 (Technical Highlights)
단순한 데이터 시각화를 넘어, 복잡한 증권사 로우 데이터를 처리하기 위한 로직을 직접 구현했습니다.
- **비정형 CSV 파싱**: 한 건의 거래가 2행에 걸쳐 분산된 2-Row-Per-Transaction 구조를 단일 레코드로 통합하는 전처리 엔진 구축.
- **하이브리드 보간 알고리즘**: 월간 자산 요약(Anchor)과 일간 거래 내역(Flow) 사이의 오차를 선형 배분하여 1원 단위까지 일치시키는 일별 원장 생성 로직 개발.
- **금융 분석 엔진**: TWR(시간가중), MWR(금액가중/XIRR), MDD(최대낙폭) 등 기관급 투자 분석 지표 산출 모듈 내장.

## 📂 3. 데이터 파이프라인 (System Architecture)
시스템은 단계별 데이터 가공을 통해 정밀도를 높이는 구조로 설계되었습니다.
1.  **Stage 1 (Ingestion)**: `00Transaction_History` / `01Asset_Summary` 원천 데이터 로드
2.  **Stage 2 (Processing)**: HTS 파싱 엔진을 통한 데이터 정규화 및 인코딩 보정
3.  **Stage 3 (Integration)**: 주식/현금/RP 자산 통합 및 `03Full_Portfolio` 생성
4.  **Stage 4 (Timeline)**: 하이브리드 보간법 기반의 `04Daily_Asset_Ledger` 엔진 가동
5.  **Stage 5 (Analytics)**: `05Performance_Data` 산출 및 시각화 리포팅

## 📊 4. 핵심 지표 (System Outputs)
*2026-01-24 기준 시스템 산출 데이터 (Test Case)*
- **TWR (운용 실력)**: `23.70%` (입출금 착시 제거)
- **MWR (베팅 성과)**: `36.63%` (자금 투입 타이밍 반영)
- **MDD (리스크 관리)**: `-25.68%` (최대 하락 폭)

## 🗺️ 5. 개발 로드맵 (Roadmap)
### Phase 1: 분석 엔진 고도화 (Current) ✅
- [x] 일별 자산 원장 및 하이브리드 보정 로직 구현
- [x] TWR / XIRR / MDD 연산 모듈 분리 및 자동화
- [x] 자산 통합 관리(Cash/RP) 기능

### Phase 2: 데이터 정밀도 강화 (Next Sprint) 🚀
- [ ] **Portfolio Time-Machine**: 과거 시점별 종목 보유 수량 복원 엔진 개발
- [ ] **FIFO Ledger**: 선입선출 기반 실현 손익 및 평단가 재계산 모듈

### Phase 3: AI 리포팅 서비스 (Future) 🤖
- [ ] **AI 주주서한**: LLM 기반의 정기 투자 복기 리포트 자동 생성 기능
- [ ] **Benchmark Alpha**: S&P500, Russell 2000 대비 초과 수익률 분석

---
**Maintained by:** [사용자 이름]  
**Tech Stack:** `Python`, `Pandas`, `NumPy`, `SciPy`, `Matplotlib`