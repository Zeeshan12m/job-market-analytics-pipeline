import pandas as pd
import os
from datetime import date

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR     = os.path.join(BASE_DIR, "data", "raw")
MERGED_DIR  = os.path.join(BASE_DIR, "data", "merged")
OUTPUT_FILE = os.path.join(MERGED_DIR, "merged_raw_jobs.csv")

# All 4 raw files
RAW_FILES = {
    "Arbeitnow":     os.path.join(RAW_DIR, "raw_arbeitnow_jobs.csv"),
    "RemoteOK":      os.path.join(RAW_DIR, "raw_remoteok_jobs.csv"),
    "Himalayas":     os.path.join(RAW_DIR, "raw_himalayas_jobs.csv"),
    "RemoteJobs.org":os.path.join(RAW_DIR, "raw_remotejobs_jobs.csv"),
}

# Standard schema — all columns in final output
STANDARD_COLUMNS = [
    "source", "job_id", "title", "company_name", "location_raw",
    "remote_status", "job_type", "category_raw", "tags_raw", "description",
    "publication_date", "job_url", "salary_text_raw", "salary_min_raw",
    "salary_max_raw", "currency_raw", "salary_min_usd", "salary_max_usd",
    "salary_mid_usd", "experience_years_min", "experience_years_max",
    "experience_bracket", "extracted_skills", "job_category_clean", "scrape_date"
]

# ── Load & Validate ───────────────────────────────────────────────────────────
def load_raw_files():
    frames = []

    for source_name, filepath in RAW_FILES.items():
        if not os.path.exists(filepath):
            print(f"[MERGE] WARNING: File not found for {source_name}: {filepath}")
            continue

        df = pd.read_csv(filepath, dtype=str)  # Read everything as string first

        if df.empty:
            print(f"[MERGE] WARNING: Empty file for {source_name}, skipping.")
            continue

        print(f"[MERGE] Loaded {len(df)} rows from {source_name}")
        frames.append(df)

    return frames

# ── Enforce Standard Schema ───────────────────────────────────────────────────
def enforce_schema(df):
    # Add any missing columns as empty
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Keep only standard columns in correct order
    df = df[STANDARD_COLUMNS]
    return df

# ── Clean Up Basic Issues ─────────────────────────────────────────────────────
def basic_clean(df):
    # Strip whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # Replace empty strings with NaN for numeric columns
    numeric_cols = [
        "salary_min_raw", "salary_max_raw", "salary_min_usd",
        "salary_max_usd", "salary_mid_usd",
        "experience_years_min", "experience_years_max"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize remote_status values
    remote_map = {
        "true":    "Remote",
        "false":   "On-site",
        "remote":  "Remote",
        "on-site": "On-site",
        "onsite":  "On-site",
        "hybrid":  "Hybrid",
    }
    df["remote_status"] = (
        df["remote_status"]
        .str.lower()
        .map(remote_map)
        .fillna(df["remote_status"])  # Keep original if not in map
    )

    # Replace salary zeros with NaN (zero salary = not provided)
    for col in ["salary_min_raw", "salary_max_raw", "salary_min_usd",
                "salary_max_usd", "salary_mid_usd"]:
        if col in df.columns:
            df[col] = df[col].replace(0, pd.NA)

    return df

# ── Deduplication ─────────────────────────────────────────────────────────────
def deduplicate(df):
    before = len(df)

    # Primary dedup: exact job_url match
    df = df.drop_duplicates(subset=["job_url"], keep="first")

    # Secondary dedup: same title + company + source
    df = df.drop_duplicates(subset=["title", "company_name", "source"], keep="first")

    after = len(df)
    print(f"[MERGE] Deduplication: {before} → {after} rows (removed {before - after} duplicates)")
    return df

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(MERGED_DIR, exist_ok=True)

    # Load all raw files
    frames = load_raw_files()

    if not frames:
        print("[MERGE] ERROR: No files loaded. Check that extraction scripts ran successfully.")
        return

    # Combine all into one dataframe
    merged = pd.concat(frames, ignore_index=True)
    print(f"[MERGE] Combined total: {len(merged)} rows from {len(frames)} sources")

    # Enforce schema
    merged = enforce_schema(merged)

    # Basic cleaning
    merged = basic_clean(merged)

    # Deduplicate
    merged = deduplicate(merged)

    # Save
    merged.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"[MERGE] Saved {len(merged)} rows → {OUTPUT_FILE}")

    # Summary
    print("\n── Row counts by source ──")
    print(merged["source"].value_counts().to_string())

    print("\n── Remote status breakdown ──")
    print(merged["remote_status"].value_counts().to_string())

    print("\n── Missing values (key columns) ──")
    key_cols = ["title", "company_name", "job_url", "description", "remote_status"]
    for col in key_cols:
        missing = merged[col].isna().sum() + (merged[col] == "").sum()
        pct = (missing / len(merged)) * 100
        print(f"  {col}: {missing} missing ({pct:.1f}%)")

if __name__ == "__main__":
    main()