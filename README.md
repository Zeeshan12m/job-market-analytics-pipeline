# 🔍 Job Market Analytics Pipeline

An end-to-end automated data engineering pipeline that extracts, cleans, transforms, and analyzes AI/ML/Data job listings from multiple public APIs — orchestrated with Apache Airflow, processed in KNIME, and notified via n8n.

---

## 📌 Project Overview

This project was built as part of a university data engineering assignment. It demonstrates a complete production-style pipeline covering data extraction, transformation, validation, metrics calculation, orchestration, and automated notifications.

The pipeline answers key questions about the AI/ML/Data job market:
- Which skills are most in demand?
- What is the remote vs on-site ratio?
- Which companies hire the most data professionals?
- What are the salary trends?

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Apache Airflow DAG                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │Arbeitnow │  │ RemoteOK │  │Himalayas │  │Remote  │  │
│  │  Extract │  │  Extract │  │  Extract │  │Jobs    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       └─────────────┴─────────────┴─────────────┘       │
│                          │                               │
│                   ┌──────▼──────┐                        │
│                   │   Merge     │                        │
│                   │  Sources    │                        │
│                   └──────┬──────┘                        │
│                          │                               │
│                   ┌──────▼──────┐                        │
│                   │    KNIME    │  ← Clean, Filter,      │
│                   │  Workflow   │    Transform           │
│                   └──────┬──────┘                        │
│                          │                               │
│              ┌───────────┼───────────┐                   │
│       ┌──────▼─────┐ ┌───▼────┐ ┌───▼──────┐            │
│       │  Validate  │ │Metrics │ │  Trigger │            │
│       │  Outputs   │ │  Calc  │ │   n8n    │            │
│       └────────────┘ └────────┘ └───┬──────┘            │
│                                     │                   │
│                              ┌──────▼──────┐            │
│                              │   Archive   │            │
│                              │   Outputs   │            │
│                              └─────────────┘            │
└─────────────────────────────────────────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │     n8n     │  ← Email
                              │  Workflow   │    Notification
                              └─────────────┘
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3.x** | Extraction, merging, validation, metrics scripts |
| **Apache Airflow 2.8.1** | Pipeline orchestration (DAG) |
| **KNIME 5.8.3 LTS** | Data cleaning, filtering, transformation |
| **n8n** | Webhook-triggered email notifications |
| **Docker Desktop** | Containerized Airflow and n8n |
| **pandas** | Data manipulation |
| **Flask** | Bridge API between Airflow (Docker) and KNIME (Windows) |

---

## 📂 Project Structure

```
job_market_project/
├── dags/
│   └── job_market_analytics_pipeline.py    # Airflow DAG
├── scripts/
│   ├── extract_arbeitnow.py                # Arbeitnow API extraction
│   ├── extract_remoteok.py                 # RemoteOK API extraction
│   ├── extract_himalayas.py                # Himalayas API extraction
│   ├── extract_remotejobs.py               # RemoteJobs.org API extraction
│   ├── merge_sources.py                    # Merge all raw CSVs
│   ├── validate_outputs.py                 # Validate pipeline outputs
│   └── calculate_metrics.py               # Calculate analytics metrics
├── data/
│   ├── raw/                                # Raw API responses (CSV)
│   ├── merged/                             # Combined merged dataset
│   ├── processed/                          # Cleaned AI/ML jobs + metrics
│   └── archive/                            # Timestamped backups
├── knime_workflow/
│   └── job_market_cleaning_workflow/       # KNIME workflow files
├── n8n/
│   └── job_market_alert_workflow.json      # n8n workflow export
├── report/
│   └── job_market_charts.html              # Analytics dashboard
├── screenshots/                            # Pipeline screenshots
├── docker-compose.yml                      # Airflow + PostgreSQL setup
└── requirements.txt                        # Python dependencies
```

---

## 📊 Data Sources

All sources are free public APIs — no API keys required:

| Source | URL | Jobs Fetched |
|---|---|---|
| Arbeitnow | `https://www.arbeitnow.com/api/job-board-api` | ~1,000 |
| RemoteOK | `https://remoteok.com/api` | ~99 |
| Himalayas | `https://himalayas.app/jobs/api/search` | ~17 |
| RemoteJobs.org | `https://remotejobs.org/api/v1/jobs` | ~27 |

---

## 📋 Standard Schema

All sources are mapped to a unified 25-column schema:

```
source, job_id, title, company_name, location_raw, remote_status,
job_type, category_raw, tags_raw, description, publication_date,
job_url, salary_text_raw, salary_min_raw, salary_max_raw, currency_raw,
salary_min_usd, salary_max_usd, salary_mid_usd, experience_years_min,
experience_years_max, experience_bracket, extracted_skills,
job_category_clean, scrape_date
```

---

## 📈 Key Results

| Metric | Value |
|---|---|
| Total raw jobs collected | 1,146 |
| After deduplication | 1,029 |
| AI/ML/Data jobs identified | 45 |
| Top location | Berlin (26.7%) |
| Remote jobs | 24.4% |
| Average salary (USD) | $232,400 (2 jobs with data) |
| Top skill | Python, Docker, SQL |
| Top hiring company | BRÜGGEN Engineering & Flix |

---

## ⚙️ How to Run

### Prerequisites

- Windows 10/11
- Docker Desktop installed and running
- Python 3.9+
- KNIME 5.8.3 LTS
- VS Code (recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/YOURUSERNAME/job-market-analytics-pipeline.git
cd job-market-analytics-pipeline
```

### 2. Set Up Python Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Start Docker Containers

```powershell
docker compose up -d
```

This starts:
- Airflow webserver at `http://localhost:8080`
- Airflow scheduler
- PostgreSQL database
- n8n at `http://localhost:5678`

### 4. Start the KNIME Flask Bridge

```powershell
python C:\knime-airflow\knime_flask_api.py
```

### 5. Run Scripts Manually (Optional Test)

```powershell
python scripts\extract_arbeitnow.py
python scripts\extract_remoteok.py
python scripts\extract_himalayas.py
python scripts\extract_remotejobs.py
python scripts\merge_sources.py
python scripts\validate_outputs.py
python scripts\calculate_metrics.py
```

### 6. Trigger the Airflow DAG

- Open `http://localhost:8080`
- Login: `admin` / `admin`
- Find `job_market_analytics_pipeline`
- Click the ▶ trigger button

### 7. View Results

- Clean jobs: `data/processed/clean_ai_ml_data_jobs.csv`
- Metrics: `data/processed/metrics_summary.csv`
- Dashboard: open `report/job_market_charts.html` in browser

---

## 🔄 Airflow DAG Tasks

```
extract_arbeitnow ──┐
extract_remoteok  ──┤
                    ├──► merge_sources ──► run_knime ──► validate ──► metrics ──► n8n ──► archive
extract_himalayas ──┤
extract_remotejobs──┘
```

| Task | Type | Description |
|---|---|---|
| `extract_*` | BashOperator | Fetch jobs from each API in parallel |
| `merge_sources` | BashOperator | Combine and deduplicate all raw CSVs |
| `run_knime_workflow` | PythonOperator | Call Flask API to run KNIME headless |
| `validate_clean_output` | BashOperator | Run 26 validation checks |
| `calculate_metrics` | BashOperator | Generate analytics metrics |
| `trigger_n8n_workflow` | PythonOperator | POST webhook to n8n |
| `archive_outputs` | PythonOperator | Timestamp and archive outputs |

---

## 📧 n8n Email Notification

When the pipeline completes, n8n automatically sends an email report:

```
Job Market Pipeline Report
--------------------------
Pipeline Status: success
Total AI/ML/Data Jobs: 45
Jobs by Source: Arbeitnow: 38, RemoteOK: 3, RemoteJobs.org: 4
Remote Jobs: 11
On-site Jobs: 34
Entry Level Jobs: 0
Jobs with Salary Info: 3
```

---

## ⚠️ Known Limitations

- **Experience extraction** — regex-based extraction failed due to inconsistent formats in job descriptions. A production system would use NLP for this.
- **Salary data scarcity** — only 4.4% of jobs had structured salary data. Most European job postings don't include salary in API responses.
- **Small dataset** — 45 jobs is a small sample for statistical analysis. More sources or broader keyword filters would improve this.
- **Geographic bias** — Arbeitnow (84.4% of results) focuses on European markets, explaining the high on-site ratio.

---

## 🎓 Academic Context

This project was built as Assignment 3 for a Data Engineering course. It demonstrates:

- API data extraction and pagination
- Data schema standardization
- ETL pipeline design
- Workflow orchestration with Apache Airflow
- Visual workflow tools (KNIME)
- Event-driven notifications (n8n webhooks)
- Docker containerization
- Data validation and quality checks

---

## 👤 Author

**Zeeshan Zahid**
- LinkedIn: [your linkedin URL]
- GitHub: [your github URL]

---

## 📄 License

This project is for educational purposes only. Job data is sourced from public APIs under their respective terms of service.
