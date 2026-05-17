import requests
import pandas as pd
from datetime import date
import os

# ── Config ──────────────────────────────────────────────────────────────────
SOURCE      = "Arbeitnow"
API_URL     = "https://www.arbeitnow.com/api/job-board-api"
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_arbeitnow_jobs.csv")
SCRAPE_DATE = str(date.today())

# ── Fetch ────────────────────────────────────────────────────────────────────
def fetch_jobs():
    jobs = []
    page = 1
    print(f"[{SOURCE}] Starting fetch...")

    while True:
        try:
            response = requests.get(API_URL, params={"page": page}, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{SOURCE}] Error on page {page}: {e}")
            break

        batch = data.get("data", [])
        if not batch:
            break

        jobs.extend(batch)
        print(f"[{SOURCE}] Page {page}: fetched {len(batch)} jobs (total so far: {len(jobs)})")

        # Arbeitnow paginates — stop if no next page signal
        if not data.get("links", {}).get("next"):
            break

        page += 1

    print(f"[{SOURCE}] Total fetched: {len(jobs)} jobs")
    return jobs

# ── Map to Standard Schema ───────────────────────────────────────────────────
def map_to_schema(jobs):
    rows = []
    for j in jobs:
        rows.append({
            "source":               SOURCE,
            "job_id":               str(j.get("slug", "")),
            "title":                j.get("title", ""),
            "company_name":         j.get("company_name", ""),
            "location_raw":         j.get("location", ""),
            "remote_status":        "Remote" if j.get("remote", False) else "On-site",
            "job_type":             j.get("job_types", [""])[0] if j.get("job_types") else "",
            "category_raw":         "",
            "tags_raw":             ", ".join(j.get("tags", [])),
            "description":          j.get("description", ""),
            "publication_date":     j.get("created_at", ""),
            "job_url":              j.get("url", ""),
            "salary_text_raw":      "",
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