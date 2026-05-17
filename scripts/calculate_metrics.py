import pandas as pd
import numpy as np
import os
import re

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR       = os.path.join(BASE_DIR, "data", "raw")
MERGED_FILE   = os.path.join(BASE_DIR, "data", "merged", "merged_raw_jobs.csv")
CLEAN_FILE    = os.path.join(BASE_DIR, "data", "processed", "clean_ai_ml_data_jobs.csv")
OUTPUT_FILE   = os.path.join(BASE_DIR, "data", "processed", "metrics_summary.csv")

RAW_FILES = {
    "Arbeitnow":      os.path.join(RAW_DIR, "raw_arbeitnow_jobs.csv"),
    "RemoteOK":       os.path.join(RAW_DIR, "raw_remoteok_jobs.csv"),
    "Himalayas":      os.path.join(RAW_DIR, "raw_himalayas_jobs.csv"),
    "RemoteJobs.org": os.path.join(RAW_DIR, "raw_remotejobs_jobs.csv"),
}

# ── Load Data ─────────────────────────────────────────────────────────────────
def load_data():
    clean = pd.read_csv(CLEAN_FILE, dtype=str)

    # Fix salary — replace zeros with NaN
    for col in ["salary_min_usd", "salary_max_usd", "salary_mid_usd"]:
        if col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce").replace(0, np.nan)

    # Fix numeric columns
    for col in ["experience_years_min", "experience_years_max"]:
        if col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce")

    return clean

# ── Metric 1: Jobs Per Source Before and After Filtering ──────────────────────
def jobs_per_source(clean):
    print("\n── 1. JOBS PER SOURCE ──")

    before = {}
    for source, path in RAW_FILES.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            before[source] = len(df)
        else:
            before[source] = 0

    after = clean["source"].value_counts().to_dict()

    rows = []
    for source in RAW_FILES.keys():
        b   = before.get(source, 0)
        a   = after.get(source, 0)
        pct = (a / b * 100) if b > 0 else 0
        rows.append({
            "metric":        "jobs_per_source",
            "category":      source,
            "before_filter": b,
            "after_filter":  a,
            "percentage":    round(pct, 1)
        })
        print(f"  {source:<20} Before: {b:>5}  After: {a:>4}  ({pct:.1f}%)")

    return pd.DataFrame(rows)

# ── Metric 2: Remote vs On-site vs Hybrid ────────────────────────────────────
def remote_ratio(clean):
    print("\n── 2. REMOTE VS ON-SITE VS HYBRID ──")
    counts = clean["remote_status"].value_counts()
    total  = len(clean)
    rows   = []
    for status, count in counts.items():
        pct = count / total * 100
        rows.append({
            "metric":     "remote_ratio",
            "category":   status,
            "count":      count,
            "percentage": round(pct, 1)
        })
        print(f"  {status:<15} {count:>4} ({pct:.1f}%)")
    return pd.DataFrame(rows)

# ── Metric 3: Experience Bracket Distribution ─────────────────────────────────
def experience_distribution(clean):
    print("\n── 3. EXPERIENCE BRACKET DISTRIBUTION ──")
    clean["experience_bracket"] = clean["experience_bracket"].fillna("Not mentioned")
    clean.loc[
        clean["experience_bracket"].str.strip() == "", "experience_bracket"
    ] = "Not mentioned"
    counts = clean["experience_bracket"].value_counts()
    total  = len(clean)
    rows   = []
    for bracket, count in counts.items():
        pct = count / total * 100
        rows.append({
            "metric":     "experience_distribution",
            "category":   bracket,
            "count":      count,
            "percentage": round(pct, 1)
        })
        print(f"  {bracket:<15} {count:>4} ({pct:.1f}%)")
    return pd.DataFrame(rows)

# ── Metric 4: Count of 0-1 Year Jobs ─────────────────────────────────────────
def entry_level_jobs(clean):
    print("\n── 4. ENTRY LEVEL JOBS (0-1 years) ──")
    count = (clean["experience_bracket"] == "0-1").sum()
    total = len(clean)
    pct   = count / total * 100
    print(f"  0-1 year jobs: {count} ({pct:.1f}%)")
    return pd.DataFrame([{
        "metric":     "entry_level_jobs",
        "category":   "0-1 years",
        "count":      count,
        "percentage": round(pct, 1)
    }])

# ── Metric 5: Average Salary Overall ─────────────────────────────────────────
def avg_salary_overall(clean):
    print("\n── 5. AVERAGE SALARY (USD) ──")
    salary_data = clean["salary_mid_usd"].dropna()
    if len(salary_data) == 0:
        print("  No salary data available")
        return pd.DataFrame([{
            "metric":   "avg_salary_usd",
            "category": "overall",
            "value":    None,
            "count":    0
        }])
    avg = salary_data.mean()
    print(f"  Average salary: ${avg:,.0f} (from {len(salary_data)} jobs)")
    return pd.DataFrame([{
        "metric":   "avg_salary_usd",
        "category": "overall",
        "value":    round(avg, 2),
        "count":    len(salary_data)
    }])

# ── Metric 6: Average Salary by Job Category ─────────────────────────────────
def avg_salary_by_category(clean):
    print("\n── 6. AVERAGE SALARY BY JOB CATEGORY ──")
    rows = []
    for cat, group in clean.groupby("job_category_clean"):
        salary_data = group["salary_mid_usd"].dropna()
        if len(salary_data) > 0:
            avg = salary_data.mean()
            print(f"  {cat:<25} ${avg:>10,.0f} (n={len(salary_data)})")
            rows.append({
                "metric":   "avg_salary_by_category",
                "category": cat,
                "value":    round(avg, 2),
                "count":    len(salary_data)
            })
        else:
            print(f"  {cat:<25} No salary data")
            rows.append({
                "metric":   "avg_salary_by_category",
                "category": cat,
                "value":    None,
                "count":    0
            })
    return pd.DataFrame(rows)

# ── Metric 7: Average Salary by Experience Bracket ───────────────────────────
def avg_salary_by_experience(clean):
    print("\n── 7. AVERAGE SALARY BY EXPERIENCE BRACKET ──")
    rows          = []
    bracket_order = ["0-1", "1-3", "3-5", "5-8", "8+", "Not mentioned"]
    for bracket in bracket_order:
        group       = clean[clean["experience_bracket"] == bracket]
        salary_data = group["salary_mid_usd"].dropna()
        if len(salary_data) > 0:
            avg = salary_data.mean()
            print(f"  {bracket:<15} ${avg:>10,.0f} (n={len(salary_data)})")
            rows.append({
                "metric":   "avg_salary_by_experience",
                "category": bracket,
                "value":    round(avg, 2),
                "count":    len(salary_data)
            })
        else:
            print(f"  {bracket:<15} No salary data")
            rows.append({
                "metric":   "avg_salary_by_experience",
                "category": bracket,
                "value":    None,
                "count":    0
            })
    return pd.DataFrame(rows)

# ── Metric 8: Top 10 Most Frequent Skills ────────────────────────────────────
def top_skills(clean):
    print("\n── 8. TOP 10 MOST FREQUENT SKILLS ──")

    SKILL_KEYWORDS = [
        "python", "sql", "spark", "hadoop", "tensorflow", "pytorch",
        "scikit-learn", "pandas", "airflow", "kafka", "dbt", "tableau",
        "power bi", "excel", "azure", "aws", "gcp", "docker", "kubernetes",
        "nlp", "llm", "mlops", "scala", "java", "mongodb", "postgresql",
        "mysql", "redis", "elasticsearch", "deep learning", "machine learning",
        "data engineering", "data science", "numpy", "matplotlib", "flask",
        "fastapi", "pyspark", "hive", "redshift", "snowflake"
    ]

    skill_counts = {}
    text_cols    = ["title", "tags_raw", "description", "extracted_skills"]

    for _, row in clean.iterrows():
        combined = " ".join([
            str(row.get(col, "")) for col in text_cols
        ]).lower()

        for skill in SKILL_KEYWORDS:
            # Use word boundary matching to avoid partial matches like 'r' in 'engineer'
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, combined):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1

    top10 = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    rows  = []
    for rank, (skill, count) in enumerate(top10, 1):
        pct = count / len(clean) * 100
        print(f"  {rank:>2}. {skill:<20} {count:>4} jobs ({pct:.1f}%)")
        rows.append({
            "metric":     "top_skills",
            "category":   skill,
            "count":      count,
            "percentage": round(pct, 1)
        })
    return pd.DataFrame(rows)

# ── Metric 9: Top Companies ───────────────────────────────────────────────────
def top_companies(clean):
    print("\n── 9. TOP COMPANIES POSTING AI/ML/DATA JOBS ──")
    counts = (
        clean["company_name"]
        .dropna()
        .value_counts()
        .head(10)
    )
    rows = []
    for rank, (company, count) in enumerate(counts.items(), 1):
        print(f"  {rank:>2}. {company:<35} {count:>3} jobs")
        rows.append({
            "metric":   "top_companies",
            "category": company,
            "count":    count
        })
    return pd.DataFrame(rows)

# ── Save All Metrics ──────────────────────────────────────────────────────────
def save_metrics(all_frames):
    combined = pd.concat(all_frames, ignore_index=True)

    for col in ["before_filter", "after_filter", "percentage", "value", "count"]:
        if col not in combined.columns:
            combined[col] = None

    combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"\n✅ Metrics saved → {OUTPUT_FILE}")
    print(f"   Total metric rows: {len(combined)}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading clean dataset...")
    clean = load_data()
    print(f"Loaded {len(clean)} rows from clean_ai_ml_data_jobs.csv")

    frames = []
    frames.append(jobs_per_source(clean))
    frames.append(remote_ratio(clean))
    frames.append(experience_distribution(clean))
    frames.append(entry_level_jobs(clean))
    frames.append(avg_salary_overall(clean))
    frames.append(avg_salary_by_category(clean))
    frames.append(avg_salary_by_experience(clean))
    frames.append(top_skills(clean))
    frames.append(top_companies(clean))

    save_metrics(frames)

if __name__ == "__main__":
    main()