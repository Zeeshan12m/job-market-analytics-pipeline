import requests
import pandas as pd
from datetime import date
import os

# ── Config ──────────────────────────────────────────────────────────────────
SOURCE      = "RemoteJobs.org"
API_URL     = "https://remotejobs.org/api/v1/jobs"
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_remotejobs_jobs.csv")
SCRAPE_DATE = str(date.today())

# ── Fetch ────────────────────────────────────────────────────────────────────
def fetch_jobs():
    print(f"[{SOURCE}] Starting fetch...")
    params = {"category": "data-science", "limit": 50}
    try:
        response = requests.get(API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[{SOURCE}] Error: {e}")
        return []

    # Handle both list response and dict with jobs key
    if isinstance(data, list):
        jobs = data
    elif isinstance(data, dict):
        jobs = data.get("jobs", data.get("data", []))
    else:
        jobs = []

    print(f"[{SOURCE}] Total fetched: {len(jobs)} jobs")
    return jobs

# ── Map to Standard Schema ───────────────────────────────────────────────────
def map_to_schema(jobs):
    rows = []
    for j in jobs:
        rows.append({
            "source":               SOURCE,
            "job_id":               str(j.get("id", j.get("job_id", ""))),
            "title":                j.get("title", j.get("job_title", "")),
            "company_name":         j.get("company", j.get("company_name", "")),
            "location_raw":         j.get("location", "Remote"),
            "remote_status":        "Remote",  # RemoteJobs.org is remote-only
            "job_type":             j.get("job_type", j.get("type", "")),
            "category_raw":         j.get("category", "data-science"),
            "tags_raw":             ", ".join(j.get("tags", [])) if isinstance(j.get("tags"), list) else str(j.get("tags", "")),
            "description":          j.get("description", j.get("job_description", "")),
            "publication_date":     j.get("date", j.get("posted_at", j.get("created_at", ""))),
            "job_url":              j.get("url", j.get("job_url", j.get("apply_url", ""))),
            "salary_text_raw":      j.get("salary", ""),
            "salary_min_raw":       None,
            "salary_max_raw":       None,
            "currency_raw":         "",
            "salary_min_usd":       None,
            "salary_max_usd":       None,
            "salary_mid_usd":       None,
            "experience_years_min": None,
            "experience_years_max": None,
            "experience_bracket":   "",
            "extracted_skills":     "",
            "job_category_clean":   "",
            "scrape_date":          SCRAPE_DATE,
        })
    return pd.DataFrame(rows)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    jobs = fetch_jobs()

    if not jobs:
        print(f"[{SOURCE}] No jobs fetched. Saving empty file.")
        df = pd.DataFrame()
    else:
        df = map_to_schema(jobs)

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"[{SOURCE}] Saved {len(df)} rows → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()