import requests
import pandas as pd
from datetime import date
import os
import time

# ── Config ──────────────────────────────────────────────────────────────────
SOURCE      = "Himalayas"
BASE_URL    = "https://himalayas.app/jobs/api/search"
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_himalayas_jobs.csv")
SCRAPE_DATE = str(date.today())
MAX_PAGES   = 5  # Safety cap — increase if you want more results

# ── Fetch ────────────────────────────────────────────────────────────────────
def fetch_jobs():
    jobs  = []
    page  = 1
    print(f"[{SOURCE}] Starting fetch...")

    while page <= MAX_PAGES:
        params = {"q": "data", "sort": "recent", "page": page}
        try:
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{SOURCE}] Error on page {page}: {e}")
            break

        batch = data.get("jobs", [])
        if not batch:
            print(f"[{SOURCE}] No more results at page {page}. Stopping.")
            break

        jobs.extend(batch)
        print(f"[{SOURCE}] Page {page}: fetched {len(batch)} jobs (total: {len(jobs)})")

        # Check if more pages exist
        total_pages = data.get("pagination", {}).get("totalPages", 1)
        if page >= total_pages:
            break

        page += 1
        time.sleep(0.5)  # Be polite to the API

    print(f"[{SOURCE}] Total fetched: {len(jobs)} jobs")
    return jobs

# ── Map to Standard Schema ───────────────────────────────────────────────────
def map_to_schema(jobs):
    rows = []
    for j in jobs:
        # Location
        location = j.get("location", "")
        if isinstance(location, dict):
            location = location.get("name", "")

        # Salary
        salary_min = j.get("salaryMin", None)
        salary_max = j.get("salaryMax", None)
        currency   = j.get("salaryCurrency", "")
        salary_mid = None
        if salary_min and salary_max:
            try:
                salary_mid = (float(salary_min) + float(salary_max)) / 2
            except:
                pass

        rows.append({
            "source":               SOURCE,
            "job_id":               str(j.get("id", j.get("slug", ""))),
            "title":                j.get("title", ""),
            "company_name":         j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else j.get("company", ""),
            "location_raw":         location,
            "remote_status":        "Remote" if j.get("isRemote", False) else "On-site",
            "job_type":             j.get("employmentType", ""),
            "category_raw":         j.get("category", ""),
            "tags_raw":             ", ".join(j.get("tags", [])) if isinstance(j.get("tags"), list) else "",
            "description":          j.get("description", ""),
            "publication_date":     j.get("publishedAt", ""),
            "job_url":              j.get("applicationUrl", j.get("url", "")),
            "salary_text_raw":      f"{salary_min}-{salary_max} {currency}".strip() if salary_min else "",
            "salary_min_raw":       salary_min,
            "salary_max_raw":       salary_max,
            "currency_raw":         currency,
            "salary_min_usd":       None,  # Currency conversion done in KNIME
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