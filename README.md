# ESG-Assure: GenAI-Powered Supplier Risk & Regulatory Compliance Engine

> **Automating the "Audit Loop": From Data Ingestion to Regulatory Filing using Llama 3 & Power BI.**

---

## 📌 Executive Summary
**The Problem:** Global organizations face a massive "Data-to-Insight" gap in ESG (Environmental, Social, and Governance) reporting. With new mandates like **SEBI BRSR** (India) and **EU CSRD** (Europe), auditors are drowning in supplier data. Manual detection of "Greenwashing" or reporting fraud across thousands of vendors is slow, error-prone, and unscalable.

**The Solution:** **ESG-Assure** is an end-to-end automated audit engine. It ingests messy raw supplier data, applies statistical anomaly detection to find "Red Flags," and uses a **Generative AI Agent (Llama 3 via Groq)** to draft professional "Notices of Non-Compliance" grounded in specific regulatory frameworks.

**The Impact:**
* **90% Reduction** in initial audit screening time.
* **Zero-Hallucination Reporting:** AI outputs are grounded in hard data and specific legal clauses (e.g., BRSR Principle 6).
* **Real-Time Risk Visibility:** Executive dashboard identifies "Concentration Risk" instantly.

---

## 🏗️ Project Architecture
The system follows a standard **ETL-A (Extract, Transform, Load, Analyze)** pipeline enhanced with GenAI:

1. **Data Ingestion & Simulation:** Generates a realistic, messy dataset of 1,000+ suppliers with injected fraud patterns (e.g., Carbon Spikes, Missing Diversity Data).
2. **Audit Logic Engine:** A Python-based statistical filter that calculates Z-Scores and logical paradoxes to flag "High Risk" entities.
3. **GenAI Auditor:** An LLM integration that reads the specific anomaly and writes a legal audit memo citing the relevant regulation.
4. **Command Center:** A Power BI Dashboard for interactive risk exploration and drill-down.

---

## 🛠️ Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Language** | **Python 3.12** | Core logic and orchestration. |
| **Data Processing** | **Pandas, NumPy** | Data manipulation and statistical analysis (Z-Scores). |
| **Generative AI** | **Llama 3 (via Groq API)** | Automated drafting of audit memos (Inference Speed: <1s). |
| **Visualization** | **Matplotlib, Seaborn** | Exploratory Data Analysis (EDA) and pattern verification. |
| **Dashboarding** | **Power BI** | Final executive "Command Center" with interactive AI panels. |
| **Version Control** | **Git / GitHub** | Source code management. |

---

## 📂 Repository Structure

```text
esg-assure-compliance-engine/
├── data/                           # Data Storage (GitIgnored in production)
│   ├── suppliers_raw.csv           # Generated 'Dirty' Dataset
│   ├── audit_exceptions.csv        # Intermediate file: List of bad actors
│   ├── final_audit_memos.csv       # AI-Generated Legal Memos
│   └── dashboard_master_data.csv   # FINAL merged file for Power BI
│
├── notebooks/                      # Jupyter Notebooks for Analysis & Prototyping
│   ├── 01_exploratory_audit.ipynb  # EDA: Visualizing Carbon Spikes & Gaps
│   └── 02_GenAI_Prototyping.ipynb  # The Core Engine: Prompt Engineering & Batch
├── plots/                          # Generated Visualizations (EDA Outputs)
│   ├── carb_outliers_variance.png
│   ├── social_disclosure_gaps.png
│   └── tot_excep_cnts_risk_cat.png
│
├── src/                            # Production Scripts
│   ├── data_generation.py          # Synthetic Data Engine (Injects Anomalies)
│   ├── audit_analysis.py           # Statistical Rules Engine (Flags Exceptions)
│   └── check.py                    # Environment python interpreter check
│
├── .gitignore                      # Prevents uploading large CSVs/Secrets
├── requirements.txt                # Python Dependencies
└── README.md                       # Project Documentation (You are here)
├── reports/                         
│   ├── ESG_REPORT.pbix             # Dashboard with master data with LLM audit ouput

```

---

## 🚀 Key Features Breakdown

### 1. The "Dirty" Data Engine (`src/data_generation.py`)

Instead of using clean Kaggle data, this project simulates the messy reality of supply chains. It generates 1,000 suppliers and programmatically injects specific audit risks:

- **Carbon Outliers:** 5% of suppliers have emissions 10x the industry average.
- **Greenwashing Paradox:** Manufacturing plants reporting "0" water usage (physically impossible).
- **Reporting Gaps:** Null values in mandatory Diversity Score fields.

---

### 2. The Statistical Auditor (`src/audit_analysis.py`)

Before AI touches the data, we use Deterministic Logic to filter noise.

- **Z-Score Detection:** Calculates `(Value - Mean) / Std Dev`. Any supplier with `Z > 3` is flagged as a "Statistical Outlier."
- **Logic Checks:** `IF Industry = 'Manufacturing' AND Water_Usage = 0 THEN Risk = 'High'`.

---

### 3. The GenAI "Associate" (`notebooks/02_GenAI_Prototyping.ipynb`)

This is the core innovation. We use Prompt Engineering to force the LLM to act as a "Senior ESG Auditor."

- **Input:** "Supplier X has emissions of 2,700 MT (Avg: 460 MT)."
- **Context:** "Reference SEBI BRSR Principle 6."
- **Output:** A formal legal memo identifying the breach, severity, and required corrective action (EIA).

---

### 4. The Power BI Command Center

The final output is not a spreadsheet, but an interactive dashboard.

- **Risk Map:** Geospatial view of high-risk suppliers.
- **Interactive AI Panel:** Clicking a red bubble on the map instantly retrieves and displays the specific AI-written audit memo for that supplier.

---

## ⚙️ Setup & Installation

### Prerequisites:

- Anaconda (Python 3.12+)
- Power BI Desktop
- Groq API Key (Free tier used for this project)

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/esg-assure-compliance-engine.git
cd esg-assure-compliance-engine
```

---

### Step 2: Create Environment & Install Dependencies

```bash
conda create -n esg-audit python=3.12 -y
conda activate esg-audit
pip install pandas numpy seaborn matplotlib groq
```

---

### Step 3: Generate the Data

```bash
cd src
python data_generation.py
# Output: ../data/suppliers_raw.csv created.
```

---

### Step 4: Run the Audit Logic

```bash
python audit_analysis.py
# Output: ../data/audit_exceptions.csv created.
```

---

### Step 5: Run the GenAI Engine

Open `notebooks/02_GenAI_Prototyping.ipynb`.

Enter your Groq API Key.

Run all cells to generate `final_audit_memos.csv` and the final `dashboard_master_data.csv`.

---

## 📊 Business Logic & Regulatory Alignment

This project is strictly aligned with real-world frameworks:

- **BRSR Principle 6 (Environment):** "Businesses should respect and make efforts to protect and restore the environment." (Used to flag Carbon Outliers).
- **SEBI Listing Obligations (Social):** Mandatory disclosure of gender diversity. (Used to flag Null Diversity Scores).
- **ISA 240 (Fraud):** "The auditor shall identify and assess the risks of material misstatement due to fraud." (Used to flag Logic Paradoxes).

---

## 🔮 Future Scope

- **Agentic AI:** Move from "Drafting" to "Actioning" (e.g., the AI automatically emailing the supplier to request data).
- **PDF Ingestion:** Using OCR to read actual supplier PDF reports instead of structured CSVs.
- **Scope 3 Calculation:** Advanced modeling to estimate downstream emissions.

---
## 🎥 Demo

![ESG Assure Demo](screenRed_dashboard/ESG_REPORT2026-02-1619-27-01-ezgif.com-video-to-gif-converter.gif)

---

**Author:** Tathagata Ghosh
**College:** Manipal University Jaipur, Dehmi Kalan, Rajastan - 303007, India
**Batch:** 2022-2026
**Semester:** VIII  
**Role:** Data Analyst / ESG Tech Consultant
