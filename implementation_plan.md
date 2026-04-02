# ESG-Assure: Production-Grade Transformation Roadmap

> **Goal**: Transition the ESG-Assure Compliance Engine from a functional prototype into an enterprise-grade, interview-ready system that demonstrates **advanced software engineering**, **system design maturity**, and **domain expertise** in ESG/RegTech.

---

## Executive Assessment of Current State

### What Works Well ✅
- **Clear ETL-A pipeline concept** — the 4-stage flow (Generate → Audit → AI → Dashboard) is logically sound
- **Domain grounding** — regulatory context mapping (BRSR Principle 6, SEBI, ISA 240) shows real-world alignment
- **LLM integration** — prompt engineering with structured output format is well-executed
- **Low temperature (0.1)** — demonstrates understanding of controlling LLM hallucination

### Critical Weaknesses 🚨

| Area | Issue | Severity |
|:---|:---|:---|
| **Architecture** | No separation of concerns — monolithic scripts with hardcoded paths, no interfaces, no dependency injection | 🔴 Critical |
| **Configuration** | Hardcoded file paths (`E:/analytics/...`), API keys in notebook source | 🔴 Critical |
| **Error Handling** | Bare `except Exception as e` with string return, no retry logic, no circuit breaker | 🔴 Critical |
| **Data Validation** | No schema validation on CSV ingestion, no data contracts | 🟡 High |
| **Testing** | Zero test coverage — no unit, integration, or property tests | 🟡 High |
| **Logging** | `print()` statements for all output — no structured logging | 🟡 High |
| **Rate Limiting** | Naive `time.sleep(1.5)` — no exponential backoff, no token bucket | 🟡 High |
| **Reproducibility** | `random.seed(42)` only in data gen, no run-level experiment tracking | 🟠 Medium |
| **Type Safety** | No type hints anywhere, no dataclasses/Pydantic models | 🟠 Medium |
| **CLI Interface** | No command-line interface — must `cd src` and run scripts manually | 🟠 Medium |

---

## Proposed Changes

### Component 1: Project Structure & Configuration

**WHY**: Enterprise code separates *configuration from logic*, *business rules from infrastructure*, and uses environment-based config for deployment portability. A recruiter scanning `/src` instantly judges your organizational maturity.

#### [NEW] `src/config.py` — Centralized Configuration (Singleton Pattern)
- Environment-variable-based configuration using `pydantic-settings` or `dataclasses`
- Follows the **12-Factor App** methodology
- API keys via `os.environ` (never source code)
- All file paths relative to project root, configurable via env vars
- Industry baselines as structured config, not inline dicts

#### [NEW] `src/models.py` — Domain Models (Data Classes)
- `Supplier` dataclass with typed fields and validation
- `AuditException` dataclass with severity enum
- `AuditMemo` dataclass for AI-generated output
- `RegulatoryContext` dataclass for compliance mappings
- Uses Python `dataclasses` + `enum.Enum` for type safety

#### [NEW] `.env.example` — Environment template
```
GROQ_API_KEY=your_key_here
DATA_DIR=./data
LOG_LEVEL=INFO
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.1
RATE_LIMIT_DELAY=1.5
```

#### [MODIFY] `src/data_generation.py` → `src/generators/supplier_generator.py`
- Extract into a **`SupplierGenerator` class** implementing a `Generator` protocol
- Use **Strategy Pattern** for anomaly injection — each anomaly type is a separate `AnomalyStrategy` class
- Replace hardcoded path (`E:/analytics/...`) with config-driven output
- Add type hints throughout
- Add structured logging

#### [MODIFY] `src/audit_analysis.py` → `src/engines/audit_engine.py`
- Extract into an **`AuditEngine` class** with pluggable **audit rules** (Strategy Pattern)
- Each rule (`CarbonOutlierRule`, `DiversityGapRule`, `LogicalAnomalyRule`) implements an `AuditRule` protocol
- Makes rules composable, testable, and extensible
- Add Pandas-native vectorized operations (currently uses slow `iterrows()`)

---

### Component 2: GenAI Auditor Refactoring

**WHY**: The current notebook code is a single 70-line cell with no error handling. In production, LLM calls fail regularly (rate limits, network errors, model downtime). A senior engineer builds *resilient* LLM integrations.

#### [NEW] `src/ai/llm_client.py` — LLM Client (Factory Pattern)
- **`LLMClientFactory`** — abstracts provider (Groq, OpenAI, local) behind a common interface
- Implements **exponential backoff with jitter** for rate limiting
- **Circuit breaker pattern** — stops hammering the API after N consecutive failures
- Structured error handling with custom exception hierarchy
- Token counting and cost estimation per request

#### [NEW] `src/ai/prompt_builder.py` — Prompt Engineering as Code
- **`PromptBuilder` class** — constructs prompts programmatically
- Template-based prompt generation (Jinja2-style or f-string with validation)
- Regulatory context injection from config (simulating lightweight RAG)
- Output format validation — parses and validates LLM responses against expected schema

#### [NEW] `src/ai/batch_processor.py` — Batch Processing Engine
- **Async batch processing** — uses `asyncio` + `aiohttp` for concurrent LLM calls
- Configurable concurrency limits
- Progress tracking with `tqdm`
- Result caching — skips already-processed suppliers on retry
- Checkpoint/resume capability for long batch runs

---

### Component 3: Data Pipeline Hardening

**WHY**: Real audit data is messy. A production system must validate inputs, handle schema drift, and provide data lineage.

#### [NEW] `src/data/validator.py` — Schema Validation
- Uses Pydantic or `pandera` for DataFrame schema validation
- Validates columns exist, types are correct, value ranges are sane
- Catches data quality issues before they reach the audit engine

#### [NEW] `src/data/repository.py` — Data Access Layer (Repository Pattern)
- Abstracts CSV I/O behind a `DataRepository` interface
- Enables future swap to PostgreSQL/SQLite without changing business logic
- Handles file path resolution, encoding, and error handling

#### [MODIFY] Data files to use relative paths throughout

---

### Component 4: CLI Interface & Orchestration

**WHY**: Professional tools have CLI interfaces with help text, argument parsing, and composable commands. Running `cd src && python script.py` is unacceptable in production.

#### [NEW] `src/cli.py` — Command-Line Interface
- Uses `click` or `argparse` for a professional CLI
- Commands: `generate`, `audit`, `ai-memo`, `build-dashboard`, `run-all`
- `--dry-run` flag for audit without writing
- `--verbose` flag for debug logging
- Entrypoint: `python -m src.cli run-all`

#### [NEW] `src/pipeline.py` — Pipeline Orchestrator
- Orchestrates the full ETL-A pipeline
- Each stage reports status, timing, and row counts
- Pipeline is idempotent — can be re-run safely

---

### Component 5: Testing Infrastructure

**WHY**: Zero tests = zero confidence. A hiring manager will check for test coverage immediately.

#### [NEW] `tests/test_models.py` — Model unit tests
#### [NEW] `tests/test_audit_rules.py` — Audit rule unit tests
- Tests each rule in isolation with known inputs/outputs
- Property-based tests for edge cases (zero values, NaN, negative)

#### [NEW] `tests/test_prompt_builder.py` — Prompt construction tests
#### [NEW] `tests/test_pipeline.py` — Integration tests

---

### Component 6: Logging & Observability

**WHY**: `print()` is invisible in production. Structured logging enables debugging, monitoring, and audit trails — especially important in compliance software.

#### [NEW] `src/utils/logger.py` — Structured Logger
- Python `logging` module with JSON formatter
- Log levels: DEBUG, INFO, WARNING, ERROR
- File and console handlers
- Correlation IDs for tracing requests through the pipeline

---

## Recruiter "Hooks" — Hard Engineering Features

These 3 features will trigger a **"must-hire"** response during technical review:

### 🎯 Hook 1: Async LLM Batch Processing with Circuit Breaker
**What**: Replace the naive sequential `for` loop + `time.sleep(1.5)` with a production async engine.
- `asyncio` + `aiohttp` for concurrent API calls
- **Token bucket rate limiter** — respects API quotas precisely
- **Circuit breaker** (using `tenacity`) — after 5 consecutive failures, backs off for 30s before retrying
- **Resume from checkpoint** — if batch crashes at row 47/109, restart picks up at row 48

**Interview talking point**: *"I implemented a circuit breaker pattern because in production, you don't want a cascade failure from one provider outage to bring down your entire pipeline. The async approach cut batch processing time from ~3 minutes to ~30 seconds with 5 concurrent workers while respecting API rate limits."*

### 🎯 Hook 2: Audit Rule Engine with Strategy Pattern + Plugin Architecture
**What**: Transform the hardcoded if/else audit rules into a pluggable rule engine.
- Each rule is a class implementing `AuditRule` protocol
- Rules are auto-discovered from the `src/engines/rules/` directory
- New rules can be added by dropping a .py file — **zero code changes** in the engine
- Rules have severity, description, and regulatory reference metadata
- Rule execution is parallelizable

**Interview talking point**: *"I used the Strategy pattern because audit regulations change frequently. With a plugin architecture, compliance analysts can add new rules without modifying the core engine. This mirrors how real enterprise GRC platforms like ServiceNow or SAP handle regulatory updates."*

### 🎯 Hook 3: Data Contracts + Schema Validation Pipeline
**What**: Implement data contracts between pipeline stages.
- Input validation with `pandera` schemas
- Each stage declares what it expects and what it produces
- Schema violations halt the pipeline with actionable error messages
- This prevents "garbage in, garbage out" — critical in audit software

**Interview talking point**: *"In a real supply chain, vendor data arrives in inconsistent formats. I implemented data contracts between pipeline stages using Pandera so that schema violations are caught at ingestion, not at the AI stage where bad data would generate misleading audit memos — a serious compliance risk."*

---

## Open Questions

> [!IMPORTANT]
> **Scope Confirmation**: This is a significant refactoring effort. Before I begin execution, I need your input on the following:

1. **Depth vs. Breadth**: Should I implement ALL components above, or focus on a subset? My recommendation is to prioritize:
   - Components 1-2 (Structure + GenAI refactoring) — highest impact on code quality
   - Component 5 (Testing) — highest impact on recruiter impression
   - The 3 Hook features — highest differentiation value

2. **Notebook Preservation**: Should I refactor the notebook code into production `.py` files and leave the notebooks as lightweight demo/exploration tools? Or should the notebooks also be updated?

3. **Power BI**: The `.pbix` dashboard is outside code scope. Should I leave it as-is, or should I also build a lightweight web-based dashboard alternative (e.g., Streamlit/Plotly Dash) that could run without Power BI Desktop?

4. **Dependencies**: Adding `pydantic`, `tenacity`, `click`, `pandera`, `tqdm`, `aiohttp` etc. changes the `requirements.txt`. Are you comfortable with these additions?

---

## Verification Plan

### Automated Tests
- Run `pytest tests/` — all tests pass
- Run `python -m src.cli run-all` — full pipeline executes without error
- Verify `data/dashboard_master_data.csv` output matches expected schema

### Manual Verification
- Code review of new module structure
- Review the "Technical Deep Dive" document for interview readiness
- Verify the refactored code maintains identical functional output to the original

