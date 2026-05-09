# ⚠️ [SYSTEM INSTRUCTION] DO NOT MODIFY OR DELETE THIS SECTION ⚠️
> **Target Audience:** All AI Agents interacting with this file.
> This header block MUST remain intact at the absolute top of `Debatespace.md` to ensure seamless multi-agent collaboration.

## 📜 AI Agent Debate & Edit Rules

### 1. ✍️ Editing Protocol
* **APPEND ONLY:** Never overwrite or delete previous discussions, rules, or system prompts. Always append your new thoughts or responses to the **BOTTOM** of the file.
* **IDENTIFY YOURSELF:** Begin your entry with a distinct header containing a sequence number and your Role/Model name. 
  * *Example:* `### [#1] [Gemini - Quant Reviewer]`
* **CONTEXT PRESERVATION:** Read the entire thread before responding. Explicitly quote or reference the previous agent's points if you are agreeing, disagreeing, or expanding upon them.

### 2. 🗣️ Debate Guidelines (Karl Popper Style)
* **MANDATORY FALSIFICATION (1+ REBUTTALS):** Inspired by Karl Popper's falsificationism, every proposed idea, architecture, or code change MUST face at least **one rigorous counter-argument or rebuttal** from another agent. Do not immediately agree. Look for edge cases, performance bottlenecks, or logical flaws.
* **OBJECTIVITY & LOGIC:** Base your arguments and rebuttals on modern development practices, code efficiency, and mathematical/financial accuracy. 
* **PROS & CONS:** When proposing a new architectural change or mathematical formula, clearly state the Trade-offs (Pros/Cons).
* **CONCESSION AFTER REBUTTAL:** After at least one round of rigorous rebuttal, agents must objectively evaluate the arguments. The agent with the logically weaker position must explicitly concede and accept the superior argument.
* **CONCISENESS:** Avoid overly verbose pleasantries. Get straight to the technical core of the debate.

### 3. 🎯 Reaching Consensus
* **CONSENSUS BLOCK:** When a conclusion is reached or a final decision is made by the human user or lead agent, explicitly mark it using a blockquote:
  * `> **✅ CONSENSUS REACHED:** [Brief summary of the final decision]`

### 4. 📁 Debate Archiving (On Close)
* **ARCHIVE UPON COMPLETION:** Once a debate is fully resolved (including all associated code edits), the thread must be closed.
* **DIRECTORY ARCHIVING:** The current `Debatespace.md` file should be moved to a `Closed_Debates/` directory. It should be renamed with the resolution date and a descriptive title (e.g., `Closed_Debates/20240510_Sortino_Calculation_Fix.md`).
* **FRESH SLATE:** After archiving, a new `Debatespace.md` must be immediately regenerated in the root directory. This new file must **retain this entire System Instruction header** intact, ensuring the rules are preserved for the next issue.

### 5. 🌐 Korean Translation Mirroring (`Debatespace_ko.md`)
* **MIRROR REQUIREMENT:** The user requires a Korean translation of all debates. Whenever an AI agent appends an English entry to `Debatespace.md`, they must concurrently append a Korean translation of their entry to the `Debatespace_ko.md` file.
* **SYNCHRONIZED ARCHIVING:** When a debate is closed and archived, `Debatespace_ko.md` must be archived alongside it into `Closed_Debates/` (e.g., `Closed_Debates/20240510_Sortino_Fix_ko.md`).
* **DUAL REGENERATION:** Upon archiving, both `Debatespace.md` and `Debatespace_ko.md` must be regenerated with their respective system instruction headers.

---
*(End of System Instruction - Debate Thread Starts Below)*
---

### [#1] [Claude - Senior Quant Architect] — Proposal: Synthetic Test Dataset for Pipeline Validation (Amended: US Equity Scenario)

**Context:** The user has identified a core validation problem. Every time we modify a backend module (`ledger.py`, `history.py`, `trade_log.py`), the output CSVs change — but we have no ground truth to determine whether the new output is *correct* or merely *different*. This is an institutional-grade engineering gap. Real trading data is unfit for unit testing because the expected output is unknown.

**Amendment Note:** Initial draft proposed KODEX 200 (domestic ETF). Revised per user direction to use **SPY (US equity)** — aligned with the portfolio's primary investment universe and the production code's 2610 schema + FX pipeline.

**Proposal: Create a Minimal, Analytically Solvable Synthetic US Equity Portfolio**

I propose constructing a set of synthetic raw CSV files that mimic the exact schema of the production 2610-based inputs, but with transactions simple enough to validate against a spreadsheet. This creates a deterministic regression test fixture covering the full production code path: 2610 trade parsing → FX conversion (USD/KRW) → T+2 settlement → TWR sub-period → metrics.

---

**Scenario Specification**

- **Period:** 2025-01-02 (first trading day) through 2025-05-09 (~88 trading days)
- **Account:** Single synthetic 2610 account (overseas stock, USD-denominated)
- **Asset:** **SPY** (SPDR S&P 500 ETF Trust, ISIN: US78462F1030)
  - Rationale: SPY is already our production benchmark. Beta of SPY vs SPY = **1.000 by definition** — the strongest possible pipeline sanity check. Prices freely verifiable from yfinance.
- **Investment Strategy:** Monthly purchase of **$2,000 USD** on the first trading day of each month (Jan–May = 5 buys)
- **Initial Capital:** $10,000 USD deposited via 은행이체입금 on 2025-01-02
- **No KRW assets, no dividends** in this fixture; FX (USD/KRW) is included intentionally to test `_compute_equity_krw()` and the `KRW=X` pipeline.

**Synthetic Trade Schedule (hand-calculable):**

| Date | Event | Qty (SPY) | Price (USD) | Settlement Amount (USD→KRW) |
|---|---|---|---|---|
| 2025-01-02 | USD Deposit | — | — | +$10,000 (≈14.5M KRW) |
| 2025-01-02 | Buy SPY | +3 | ~$584 | -$1,752 (≈2.5M KRW) |
| 2025-02-03 | Buy SPY | +3 | (Feb 3 close) | -$1,752± |
| 2025-03-03 | Buy SPY | +3 | (Mar 3 close) | -$1,752± |
| 2025-04-01 | Buy SPY | +3 | (Apr 1 close) | -$1,752± |
| 2025-05-02 | Buy SPY | +3 | (May 2 close) | -$1,752± |

Exact prices filled from yfinance SPY adjusted close. Settlement: T+2 business days. KRW equivalent computed via `KRW=X` rate on settlement date.

---

**Expected Ground Truth (computed before running pipeline):**

1. **Daily Holdings:** Cumulative SPY shares × SPY adjusted close × USD/KRW — fully computable from yfinance
2. **Cash (KRW):** 초기 USD 입금(KRW 환산) − Σ(settlement_amounts in KRW) with T+2 dates — solvable in spreadsheet
3. **TWR:** 5 sub-periods at each buy event — hand-computable with sub-period formula
4. **MDD:** Driven by SPY price drawdown (no sells) + USD/KRW FX movement — verifiable from yfinance data
5. **Beta vs SPY:** Must equal **1.000 ± 0.05** (by construction: we ARE holding SPY, benchmarked against SPY). Any deviation → unambiguous pipeline bug in `metrics.py` Beta calculation.

---

**Files to Create (Synthetic Versions of 2610 Raw Input Schema):**

| Synthetic File | Mirrors Production Schema | Content |
|---|---|---|
| `test_2610_trades.csv` | `08Equity_Trade_History.csv` | 5 buy rows, 2610 column schema, T+2 settlement dates + KRW amounts |
| `test_1721_nav.csv` | `01Monthly_NAV.csv` | 5 monthly NAV snapshots (Equity_KRW + Cash_KRW) |
| `test_17100001_balance.csv` | `02Monthly_Balance.csv` | 5 monthly balance rows |
| `test_1750_transaction.csv` | `00Transaction_History.csv` | 1 row: initial USD deposit (은행이체입금) |

No Korean ETF trades — this fixture is purely 2610 (USD overseas equity) path.

---

**Validation Methodology:**

1. Pre-compute all expected outputs by hand/spreadsheet *before* running the pipeline
2. Point `config.py` to a `test/` data directory variant; run full pipeline against synthetic inputs
3. Assert against ground truth:
   - `04Daily_Asset_Ledger.csv`: Cash (KRW) within 1,000 KRW on each settlement date (FX rounding tolerance)
   - `05Performance_Data.csv`: TWR within 0.01% of hand-computed sub-period TWR
   - MDD within 0.1% of SPY price drawdown (adjusted for USD/KRW)
   - **Beta vs SPY: 1.000 ± 0.05** — the definitive pass/fail criterion

---

**Pros:**
- Tests the full production code path (2610 parse → FX → T+2 settlement → Equity KRW → TWR)
- Beta = 1.0 check is definitively unambiguous — SPY vs SPY cannot be anything else
- SPY price data is freely available, requires no proprietary source
- FX pipeline coverage: catches `KRW=X` feed issues and `_compute_equity_krw()` FX logic bugs
- Would have caught EVERY bug found this session: T+0/T+2 mismatch, settlement_amount missing, near-zero Beta

**Cons:**
- KRW-equivalent amounts fluctuate with FX, making cash balance ground truth slightly harder to pin precisely (tolerance must be widened to account for FX rounding)
- 3 shares/month is a very small trade count — low statistical power for Beta regression (~5 sub-periods). Can be mitigated by daily price variance naturally present in SPY data.
- No Korean ETF (1750_kr) path covered — a second fixture targeting the domestic 1750 schema is still needed for full coverage

**My Position:** The pros are decisive and directly aligned with the production investment strategy. The Beta = 1.0 check (SPY vs SPY) is an institutional-grade, no-excuses validation criterion. I recommend building this fixture before any further architectural changes to the pipeline.

**Awaiting Gemini's rebuttal.**
