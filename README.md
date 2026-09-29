# ⚡ SettleIQ — AI Finance Controller

> **AI-powered reconciliation and exception management for Indian SMB finance teams**

**Live Demo:** https://settleiq.streamlit.app

SettleIQ is an AI-assisted finance controller that automates reconciliation between **Razorpay settlements, bank statements, and GST invoice data**. It combines deterministic matching, fuzzy matching, AI-assisted exception classification, audit trails, and conversational Q&A into a single workflow.

---

## 🚀 Results at a Glance

| Metric                 |              Result |
| ---------------------- | ------------------: |
| Records processed      |             **500** |
| Processing time        |     **< 5 seconds** |
| Tier 1 exact matches   |             **405** |
| Tier 2 fuzzy matches   |              **56** |
| Exceptions             |              **89** |
| Auto-match rate        | **92.2% (461/500)** |
| Confirmed bank credits |     **₹1.04 crore** |
| Amount at risk         |     **₹21.5 lakhs** |
| Unit tests             |     **6/6 passing** |

All metrics above are calculated from the 500-record dataset included in the repository and can be reproduced locally.

---

# 🎯 Problem

Finance teams often reconcile payment settlements manually using spreadsheets. At higher transaction volumes, this creates several problems:

* Settlement dates may differ from bank credit dates.
* MDR deductions create small amount differences.
* Duplicate UTRs can create duplicate-credit anomalies.
* Missing Razorpay or bank entries require manual investigation.
* GST-related settlement differences need additional reconciliation.
* Spreadsheet-based matching becomes difficult to audit and scale.

SettleIQ turns this process into an automated, explainable workflow.

---

# 💡 What SettleIQ Does

SettleIQ processes three sources:

```text
Razorpay Settlement Data
          │
          ├──────────────┐
          │              │
Bank Statement Data   GST Invoice Data
          │              │
          └──────┬───────┘
                 ▼
        SettleIQ Data Pipeline
                 │
                 ▼
        3-Tier Reconciliation
                 │
        ┌────────┼─────────┐
        ▼        ▼         ▼
      Exact    Fuzzy      AI
      Match    Match   Exceptions
        │        │         │
        └────────┼─────────┘
                 ▼
          Finance Dashboard
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      Audit    Q&A      Exports
      Trail    Agent    Reports
```

---

# ⚙️ 3-Tier Reconciliation Engine

## Tier 1 — Deterministic Exact Matching

The first layer performs a high-confidence match using:

* UTR
* Settlement amount
* Integer-paise comparison
* Small amount tolerance

Amounts are converted to integer paise before comparison to avoid floating-point precision issues.

```python
rp_paise = int(round(amount_rp * 100))
bank_paise = int(round(amount_bank * 100))

if abs(rp_paise - bank_paise) <= 5:
    # MATCHED — 100% confidence
```

### Result

**405 records matched at 100% confidence.**

---

## Tier 2 — Scored Fuzzy Matching

Records that cannot be matched exactly are evaluated using:

* Merchant ID
* Amount difference
* Settlement/credit date gap
* T+3 settlement window

Example scoring:

```text
Score =
1.0
- amount difference factor
- date gap factor
```

The score is constrained to the configured confidence range.

### Result

**56 additional records matched with 75–94% confidence.**

---

## Tier 3 — AI-Assisted Exception Classification

Records that remain unmatched are classified into predefined exception categories.

| Category                 | Typical Investigation                   |
| ------------------------ | --------------------------------------- |
| Amount Mismatch          | Check settlement/MDR difference         |
| Timing Mismatch          | Check delayed settlement or bank credit |
| Missing Entry — Bank     | Verify bank credit using UTR            |
| Missing Entry — Razorpay | Check alternate payment channels        |
| Ghost Entry / Duplicate  | Investigate duplicate UTR               |
| GST Variance             | Reconcile GST calculation               |

### Result

**89 exceptions classified across 6 categories.**

---

# 🤖 AI Exception Explainer

SettleIQ uses a provider fallback chain for exception explanations:

```text
Exception Type
      │
      ▼
Type-Keyed Cache
      │
      ├── Cache Hit → Return explanation
      │
      ▼
Gemini 2.5 Flash
      │
      ▼
OpenAI
      │
      ▼
Domain Heuristic Fallback
```

### Key Optimization

The explanation cache is keyed by **exception type**, rather than individual payment ID.

Because the prototype uses six predefined exception categories, repeated exceptions can reuse the same explanation instead of triggering a new model request.

This reduced API calls from **47 to 6** during development and helped avoid unnecessary rate-limit usage.

The heuristic fallback also ensures that exception classification remains available even when an LLM provider is unavailable.

---

# 📊 Dashboard

SettleIQ provides four main dashboard areas.

### 1. Reconciliation Dashboard

* 92.2% auto-match rate
* Tier 1 / Tier 2 / Tier 3 breakdown
* Cash-gap analysis
* Settlement waterfall
* Exception amounts
* Risk prioritization

### 2. AI Exception Queue

* Filter by exception category
* Filter by confidence
* Search by payment ID
* AI-generated root cause
* Suggested action
* Human-in-the-loop resolution
* Bank escalation email drafting

### 3. Settlement Q&A Agent

Users can ask questions in plain English, for example:

```text
Why is pay_abc123 unreconciled?

How much cash is currently at risk?

What is our current match rate?
```

The agent uses the reconciliation results to provide contextual answers.

### 4. Audit Trail & Exports

Every reconciliation decision can be traced through:

* Match rule
* Confidence score
* Timestamp
* Exception category
* Resolution status

Users can export:

* Matched pairs CSV
* Exception queue CSV
* Color-coded Excel report

---

# 🧪 Validation & Unit Tests

The repository includes six unit tests covering important reconciliation scenarios.

```bash
python -m unittest test_reconciliation.py -v
```

Current test suite:

```text
test_duplicate_utr_flagged_as_ghost_entry ... ok
test_fuzzy_match_accepts_within_2_5_pct ... ok
test_fuzzy_match_rejects_beyond_2_5_pct ... ok
test_missing_bank_entry_classification ... ok
test_paise_conversion_float_fix ... ok
test_tier1_exact_utr_match ... ok

Ran 6 tests in 0.002s — OK
```

---

# 🐛 Development Bugs & Fixes

| Issue                                          | Root Cause                        | Fix                                        |
| ---------------------------------------------- | --------------------------------- | ------------------------------------------ |
| Amount comparison failed for small differences | IEEE 754 floating-point precision | Convert amounts to integer paise           |
| Excessive LLM API calls                        | Cache keyed by payment ID         | Cache by exception type                    |
| OpenAI quota exhaustion                        | Provider credits exhausted        | Gemini → OpenAI → heuristic fallback       |
| Settlement waterfall showed ₹0 received        | Incorrect dataframe used          | Read matched bank amounts                  |
| `payment_id` KeyError                          | CSV column normalization issue    | Added whitespace normalization and aliases |

---

# 📈 Reproducible Results

The current prototype operates on a 500-record dataset.

```text
Tier 1 — Exact UTR
405 matched
81.0%

Tier 2 — Fuzzy
56 matched
11.2%

Tier 3 — Exceptions
89 records
17.8%

Total matched
461 / 500
92.2%
```

Financial position from the current dataset:

```text
Cleared Position:  ₹10,478,225.64
Amount at Risk:    ₹2,155,357.19
```

Run the reconciliation engine to reproduce the results:

```bash
python reconciliation_engine.py
```

---

# 🛠️ Tech Stack

### Frontend / Dashboard

* Streamlit
* Plotly

### AI / LLM

* Google Gemini 2.5 Flash
* OpenAI
* Domain-specific heuristic fallback

### Data Processing

* Python
* Pandas

### Validation

* Python `unittest`

### Data Sources

* Razorpay settlement data
* Bank statement data
* GST invoice data

---

# 📁 Repository Structure

```text
SettleIQ/
│
├── app.py
├── reconciliation_engine.py
├── exception_explainer.py
├── generate_datasets.py
├── test_reconciliation.py
├── requirements.txt
├── .env.example
├── README.md
│
└── data/
    └── generated datasets
```

### Core Files

| File                       | Purpose                              |
| -------------------------- | ------------------------------------ |
| `app.py`                   | Streamlit dashboard                  |
| `reconciliation_engine.py` | 3-tier reconciliation engine         |
| `exception_explainer.py`   | AI + fallback exception explanations |
| `generate_datasets.py`     | Dataset generation / ingestion       |
| `test_reconciliation.py`   | Unit tests                           |
| `README.md`                | Project documentation                |

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd SettleIQ
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment variables

Create a `.env` file:

```bash
cp .env.example .env
```

Add the required API keys:

```env
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

## 4. Generate the dataset

```bash
python generate_datasets.py
```

## 5. Run reconciliation

```bash
python reconciliation_engine.py
```

## 6. Launch the dashboard

```bash
streamlit run app.py
```

## 7. Run tests

```bash
python -m unittest test_reconciliation.py -v
```

---

# 🌐 Live Demo

**SettleIQ:**
https://settleiq.streamlit.app

The live prototype demonstrates:

* Automated reconciliation
* Match confidence
* Exception classification
* Cash-gap analysis
* AI explanations
* Settlement Q&A
* Audit trail
* CSV/Excel exports

---

# 📌 Current Prototype Scope

SettleIQ is a working prototype designed to demonstrate an end-to-end automated reconciliation workflow.

The reported metrics are based on the **500-record dataset in this repository** and are not presented as industry-wide benchmarks.

The system is designed around explainability and human-in-the-loop review: automated matching and AI-assisted classification surface potential issues, while financial teams retain control over final resolution.

---

## 📊 Current Dataset Results

```text
500 Razorpay records processed

405  → Tier 1 exact matches
 56  → Tier 2 fuzzy matches
 89  → Tier 3 exceptions

461 / 500 → 92.2% auto-match rate

₹10,478,225.64 → Cleared position
₹2,155,357.19  → Amount at risk
```

**SettleIQ — From spreadsheet reconciliation to explainable financial control.**
