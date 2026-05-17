import requests
import pandas as pd
from datetime import date
import os

# ── Config ──────────────────────────────────────────────────────────────────
SOURCE      = "RemoteOK"
API_URL     = "https://remoteok.com/api"
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_remoteok_jobs.csv")
SCRAPE_DATE = str(date.today())

# ── Fetch ────────────────────────────────────────────────────────────────────
def fetch_jobs():
    print(f"[{SOURCE}] Starting fetch...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}  # RemoteOK requires a user-agent
        response = requests.get(API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[{SOURCE}] Error: {e}")
        return []

    # First item is a legal notice object, not a job — skip it
    jobs = [item for item in data if item.get("id") and item.get("position")]
    print(f"[{SOURCE}] Total fetched: {len(jobs)} jobs")
    return jobs

# ── Map to Standard Schema ───────────────────────────────────────────────────
def map_to_schema(jobs):
    rows = []
    for j in jobs:
        # Salary fields
        salary_min = j.get("salary_min", None)
        salary_max = j.get("salary_max", None)
        salary_mid = None
        if salary_min and salary_max:
            try:
                salary_mid = (float(salary_min) + float(salary_max)) / 2
            except:
                pass

        rows.append({
            "source":               SOURCE,
            "job_id":               str(j.get("id", "")),
            "title":                j.get("position", ""),
            "company_name":         j.get("company", ""),
            "location_raw":         j.get("location", "Worldwide"),
            "remote_status":        "Remote",  # RemoteOK is remote-only
            "job_type":             "",
            "category_raw":         "",
            "tags_raw":             ", ".join(j.get("tags", [])),
            "description":          j.get("description", ""),
            "publication_date":     j.get("date", ""),
            "job_url":              j.get("url", ""),
            "salary_text_raw":      f"{salary_min}-{salary_max}" if salary_min and salary_max else "",
            "salary_min_raw":       salary_min,
            "salary_max_raw":       salary_max,
            "currency_raw":         "USD",
            "salary_min_usd":       salary_min,
            "salary_max_usd":       salary_max,
            "salary_mid_usd":       salary_mid,
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