# ESG-Assure: Technical Deep Dive — Interview Preparation Guide

> **Purpose**: This document explains the **why** behind every architectural decision in the ESG-Assure Compliance Engine. Use it during technical interviews to demonstrate system design maturity, engineering rigor, and domain expertise in ESG/RegTech.

---

## 1. Architecture Overview

### Before (Prototype)
```
data_generation.py → audit_analysis.py → Notebook (GenAI) → Power BI
       ↓                    ↓                    ↓               ↓
  Hardcoded paths      iterrows()          Bare try/except    Manual merge
  No types             Monolithic rules    API key in source  No logging
```

### After (Production-Grade)
```
src/
├── config.py                      # Singleton + 12-Factor Config
├── models.py                      # Typed domain models (dataclasses + enums)
├── pipeline.py                    # ETL-A Orchestrator
├── cli.py                         # Professional CLI (argparse)
├── generators/
│   └── supplier_generator.py      # Strategy Pattern (anomaly injection)
├── engines/
│   ├── audit_engine.py            # Pluggable rules engine
│   └── rules/
│       ├── base.py                # AuditRule ABC (protocol)
│       ├── carbon_outlier.py      # Z-Score detection
│       ├── diversity_gap.py       # Null-value detection
│       └── logical_anomaly.py     # Impossible-value detection
├── ai/
│   ├── llm_client.py              # Factory + Circuit Breaker + Backoff
│   ├── prompt_builder.py          # Structured prompt engineering
│   └── batch_processor.py         # Resilient batch LLM processing
├── data/
│   └── (future: repository.py)    # Data access layer
└── utils/
    └── logger.py                  # JSON/Text structured logging
tests/
├── test_models.py                 # Domain model validation (9 tests)
├── test_audit_rules.py            # Rule logic tests (8 tests)
└── test_prompt_builder.py         # Prompt construction tests (4 tests)
```

---

## 2. Design Patterns Used & Why

### 2.1 Singleton Pattern — `config.py`

**What**: `Settings.get_instance()` returns the same configuration object everywhere.

**Why**: In a multi-module pipeline, passing config through 5 layers of function arguments is error-prone. The Singleton ensures:
- Config is loaded **once** from environment variables
- All modules share the **same** config state
- `Settings.reset()` enables clean test isolation

**Interview Phrase**: *"I chose Singleton over global variables because it gives me explicit lifecycle control — I can reset the config between tests, which you can't do with module-level globals."*

### 2.2 Strategy Pattern — `supplier_generator.py` + `engines/rules/`

**What**: Anomaly injection and audit rules are separate classes implementing a common interface.

**Why**: The original code had hardcoded if/else blocks for each anomaly type and audit rule. When a new regulation is added (e.g., EU CSRD mandatory disclosures), you'd need to modify the core generator and audit scripts — violating the **Open/Closed Principle**.

With the Strategy Pattern:
- Adding a new anomaly = creating a new `AnomalyStrategy` subclass
- Adding a new audit rule = creating a new `AuditRule` subclass
- **Zero changes** to `SupplierGenerator` or `AuditEngine`

**Interview Phrase**: *"This mirrors how enterprise GRC platforms like ServiceNow handle regulatory updates — compliance analysts define new rules without touching the core engine."*

### 2.3 Factory Pattern — `ai/llm_client.py`

**What**: `LLMClientFactory.create()` builds a production-ready LLM client regardless of provider.

**Why**: We currently use Groq, but in production we might need to:
- Switch to OpenAI for higher quality
- Use a local LLaMA model for sensitive data
- A/B test multiple providers simultaneously

The Factory abstracts the provider behind a `BaseLLMClient` interface, so the switch is a 1-line config change.

**Interview Phrase**: *"I used the Factory pattern because LLM providers are changing rapidly. By abstracting behind an interface, we can switch from Groq to OpenAI in production without modifying any business logic."*

### 2.4 Circuit Breaker Pattern — `ai/llm_client.py`

**What**: After 5 consecutive LLM API failures, the circuit "opens" and rejects all calls for 30 seconds before retrying.

**Why**: Without a circuit breaker, if Groq goes down:
1. Every request fails with a timeout (e.g., 30s each)
2. 109 suppliers × 30s = **~55 minutes** of hanging
3. The API gets hammered with retry traffic, prolonging the outage

With the circuit breaker:
1. After 5 failures (~7.5s), the circuit opens
2. All subsequent calls fail immediately (no waiting)
3. After 30s, one "probe" request tests if the API is back
4. If the probe succeeds, normal operation resumes

**Interview Phrase**: *"I implemented a circuit breaker because in production, you don't want cascade failures from one provider outage to bring down your entire pipeline."*

### 2.5 Exponential Backoff with Jitter — `ai/llm_client.py`

**What**: Retry delays double each attempt: 1.5s → 3s → 6s, with random jitter.

**Why**: Fixed-interval retries cause "thundering herd" — if 10 workers all hit a rate limit at the same time and retry after exactly 1.5s, they all hit the rate limit again simultaneously. Jitter desynchronizes the retries.

**Interview Phrase**: *"Exponential backoff with jitter is the industry standard for API resilience. AWS, Google Cloud, and Stripe all recommend this approach in their API documentation."*

---

## 3. Data Contract Philosophy

### The Problem
The original prototype used raw dictionaries and untyped DataFrames. This leads to:
- Runtime `KeyError` crashes when a column name changes
- No IDE autocompletion
- Impossible for new engineers to understand what data flows between stages

### The Solution: Typed Domain Models (`models.py`)

Every pipeline stage consumes and produces **typed, validated objects**:

```python
# Data Generation → Supplier dataclass → CSV
# CSV → Audit Engine → AuditException dataclass → CSV  
# CSV → GenAI → AuditMemo dataclass → CSV
# CSV → Dashboard Builder → Final merged CSV
```

The `IssueType` and `RiskLevel` enums ensure that only valid values propagate through the system. If someone adds a new issue type but forgets to add its regulatory context, the `test_all_issue_types_have_context` test catches it immediately.

**Interview Phrase**: *"In audit/compliance software, data integrity is non-negotiable. If a 'Carbon Outlier' exception gets silently renamed to 'Carbon_Outlier', the LLM prompt breaks and generates incorrect regulatory citations — a serious compliance risk. Typed models prevent this at compile time, not runtime."*

---

## 4. Testing Strategy

### Test Categories

| Test File | Type | What It Verifies | Count |
|:---|:---|:---|:---|
| `test_models.py` | Unit | Domain model creation, serialization, enum completeness | 9 |
| `test_audit_rules.py` | Unit | Each audit rule detects correct anomalies, no false positives | 8 |
| `test_prompt_builder.py` | Unit | Prompt structure, regulatory injection, fallback handling | 4 |

### Key Testing Principles Applied

1. **No I/O in unit tests**: All tests use in-memory DataFrames — no file reads, no API calls
2. **Deterministic**: No randomness — every test produces the same result every time
3. **Isolation**: Each rule is tested independently — a bug in `CarbonOutlierRule` doesn't affect `DiversityGapRule` tests
4. **Edge cases**: Tests verify zero values, NaN values, and unknown issue types

**Interview Phrase**: *"I structured tests as pure business logic validation — no LLM calls, no file I/O. This keeps the test suite running in under 1 second, which means developers actually run tests before pushing."*

---

## 5. Logging & Observability

### Before
```python
print(f"✅ Success! 'suppliers_raw.csv' generated with {num_suppliers} rows.")
```

### After
```json
{"timestamp": "2026-04-02T18:14:11.605Z", "level": "INFO", "module": "supplier_generator", "function": "generate", "line": 213, "message": "Generating 1000 suppliers with seed=42"}
```

### Why This Matters
- **Structured JSON logs** are ingestible by ELK, Datadog, Splunk — `print()` is not
- **Timestamps** enable audit trail reconstruction: "When exactly was the last data generation run?"
- **Module + function + line** enable instant debugging without stack traces
- **Log levels** allow filtering: in production, set `LOG_LEVEL=WARNING` to suppress info noise

---

## 6. Configuration Management

### Before
```python
# Hardcoded in notebook cell
API_KEY = "YOUR_GROQ_API"
df.to_csv('E:/analytics/datasets_for_DA_proj_Self/esg-assure-compliance-engine/data/suppliers_raw.csv')
```

### After
```python
# From environment / .env file
settings = Settings.get_instance()
api_key = settings.llm.api_key  # From GROQ_API_KEY env var
output = settings.paths.suppliers_raw  # From DATA_DIR env var + path joining
```

### Why This Matters
- **Security**: API keys never appear in source code or Git history
- **Portability**: The same code runs on local, CI/CD, staging, and production — only env vars change
- **12-Factor Compliance**: Config is a deployment concern, not an application concern

---

## 7. Scalability Considerations

### Current Bottleneck: Sequential LLM Processing
The batch processor currently processes exceptions sequentially. For 109 exceptions at 1.5s/call, that's ~2.7 minutes.

### Future Enhancement: Async Processing
The `ResilientLLMClient` is designed to be wrapped in an async adapter:
```python
# Future: asyncio + aiohttp for concurrent LLM calls
async def process_batch(exceptions, max_concurrency=5):
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [process_one(ex, semaphore) for ex in exceptions]
    return await asyncio.gather(*tasks)
```
This would reduce processing time from ~2.7 minutes to ~30 seconds with 5 concurrent workers.

### Database Migration Path
The current system uses CSV files. The `save()` and `load()` methods on each pipeline component are designed to be swappable — replacing CSV with SQLite/PostgreSQL requires changes only in the data access layer, not in business logic.

---

## 8. Business & Domain Context

### Regulations Referenced

| Regulation | Scope | How We Use It |
|:---|:---|:---|
| **BRSR Principle 6** | India (SEBI) | Flags carbon emission outliers |
| **SEBI BRSR Core** | India (listed entities) | Flags missing diversity disclosures |
| **ISA 240** | International (IAASB) | Flags logically impossible data (fraud indicators) |

### Why This Project Matters to Employers
ESG compliance is a **$1.3 trillion market** growing at 20% CAGR. Every Fortune 500 company needs:
1. Automated vendor screening (this project's Stage 2)
2. AI-assisted audit documentation (this project's Stage 3)
3. Real-time risk dashboards (this project's Stage 4)

**Interview Phrase**: *"I built this because I saw a real industry gap — auditors are drowning in supplier data from new BRSR mandates. This engine automates 90% of the initial screening, letting auditors focus on judgment calls, not data crunching."*

---

## Quick Reference: Running the System

```bash
# Setup
cp .env.example .env          # Add your GROQ_API_KEY
pip install -r requirements.txt

# Run individual stages
python -m src generate         # Stage 1: Generate supplier data
python -m src audit            # Stage 2: Run audit rules
python -m src ai-memo          # Stage 3: Generate AI memos (requires API key)
python -m src build-dashboard  # Stage 4: Build dashboard data

# Run full pipeline
python -m src run-all

# Run tests
python -m pytest tests/ -v
```
