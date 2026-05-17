import pandas as pd
import os
import sys

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR      = os.path.join(BASE_DIR, "data", "raw")
MERGED_DIR   = os.path.join(BASE_DIR, "data", "merged")
PROCESSED_DIR= os.path.join(BASE_DIR, "data", "processed")

RAW_FILES = [
    os.path.join(RAW_DIR, "raw_arbeitnow_jobs.csv"),
    os.path.join(RAW_DIR, "raw_remoteok_jobs.csv"),
    os.path.join(RAW_DIR, "raw_himalayas_jobs.csv"),
    os.path.join(RAW_DIR, "raw_remotejobs_jobs.csv"),
]

MERGED_FILE  = os.path.join(MERGED_DIR, "merged_raw_jobs.csv")
CLEAN_FILE   = os.path.join(PROCESSED_DIR, "clean_ai_ml_data_jobs.csv")

MANDATORY_COLUMNS = [
    "source", "job_id", "title", "company_name", "location_raw",
    "remote_status", "job_url", "description", "scrape_date",
    "job_category_clean", "experience_bracket"
]

VALID_REMOTE_VALUES  = {"Remote", "On-site", "Hybrid"}
VALID_EXP_BRACKETS   = {"0-1", "1-3", "3-5", "5-8", "8+", "Not mentioned", ""}

# ── Helpers ───────────────────────────────────────────────────────────────────
passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ PASS — {label}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {label}" + (f": {detail}" if detail else ""))
        failed += 1

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ── Check 1: Raw Files ────────────────────────────────────────────────────────
section("1. RAW FILES")
raw_frames = {}
for filepath in RAW_FILES:
    name = os.path.basename(filepath)
    exists = os.path.exists(filepath)
    check(f"{name} exists", exists)
    if exists:
        df = pd.read_csv(filepath)
        check(f"{name} is non-empty", len(df) > 0, f"rows={len(df)}")
        raw_frames[name] = df
        print(f"     → {len(df)} rows")

# ── Check 2: Merged File ──────────────────────────────────────────────────────
section("2. MERGED FILE")
check("merged_raw_jobs.csv exists", os.path.exists(MERGED_FILE))
if os.path.exists(MERGED_FILE):
    merged = pd.read_csv(MERGED_FILE)
    check("merged_raw_jobs.csv is non-empty", len(merged) > 0)
    print(f"     → {len(merged)} rows")

    # Duplicate count
    dup_url   = merged.duplicated(subset=["job_url"]).sum()
    dup_title = merged.duplicated(subset=["title", "company_name", "source"]).sum()
    print(f"\n  Duplicate job_url: {dup_url}")
    print(f"  Duplicate title+company+source: {dup_title}")

# ── Check 3: Clean File ───────────────────────────────────────────────────────
section("3. CLEAN FILE (AI/ML/Data Jobs)")
check("clean_ai_ml_data_jobs.csv exists", os.path.exists(CLEAN_FILE))

if os.path.exists(CLEAN_FILE):
    clean = pd.read_csv(CLEAN_FILE)
    check("clean_ai_ml_data_jobs.csv is non-empty", len(clean) > 0)
    print(f"     → {len(clean)} rows")

    # Row count comparison
    if os.path.exists(MERGED_FILE):
        print(f"\n  Rows before AI/ML filter (merged): {len(merged)}")
        print(f"  Rows after  AI/ML filter (clean):  {len(clean)}")
        print(f"  Filter kept {len(clean)/len(merged)*100:.1f}% of jobs")

    # ── Check 4: Mandatory Columns ────────────────────────────────────────────
    section("4. MANDATORY COLUMNS")
    for col in MANDATORY_COLUMNS:
        check(f"Column '{col}' exists", col in clean.columns)

    # ── Check 5: Missing Values ───────────────────────────────────────────────
    section("5. MISSING VALUE PERCENTAGES (key columns)")
    key_cols = ["title", "company_name", "job_url", "description",
                "remote_status", "job_category_clean", "experience_bracket",
                "salary_mid_usd"]
    for col in key_cols:
        if col in clean.columns:
            missing = clean[col].isna().sum() + (clean[col].astype(str).str.strip() == "").sum()
            pct     = (missing / len(clean)) * 100
            print(f"  {col:<25} {missing:>4} missing ({pct:>5.1f}%)")

    # ── Check 6: Remote Status Values ────────────────────────────────────────
    section("6. REMOTE STATUS VALIDATION")
    if "remote_status" in clean.columns:
        actual_values = set(clean["remote_status"].dropna().unique())
        invalid       = actual_values - VALID_REMOTE_VALUES
        check("All remote_status values are valid",
              len(invalid) == 0,
              f"Invalid values found: {invalid}")
        print(f"\n  Remote status breakdown:")
        print(clean["remote_status"].value_counts().to_string())

    # ── Check 7: Salary Zeros ────────────────────────────────────────────────
    section("7. SALARY ZERO TREATMENT")
    if "salary_mid_usd" in clean.columns:
        # Replace zeros with NaN for accurate reporting
        clean["salary_mid_usd"] = pd.to_numeric(
            clean["salary_mid_usd"], errors="coerce"
        ).replace(0, pd.NA)

        zeros    = (clean["salary_mid_usd"] == 0).sum()
        non_null = clean["salary_mid_usd"].notna().sum()
        check("No zero salary values (zeros treated as null)", zeros == 0)
        print(f"  Non-null salary_mid_usd: {non_null} rows ({non_null/len(clean)*100:.1f}%)")

    # ── Check 8: Experience Brackets ────────────────────────────────────────
    section("8. EXPERIENCE BRACKET VALIDATION")
    if "experience_bracket" in clean.columns:
        actual_brackets = set(clean["experience_bracket"].fillna("").unique())
        invalid_brackets = actual_brackets - VALID_EXP_BRACKETS
        check("All experience_bracket values are valid",
              len(invalid_brackets) == 0,
              f"Invalid values: {invalid_brackets}")
        print(f"\n  Experience bracket breakdown:")
        print(clean["experience_bracket"].value_counts().to_string())

    # ── Check 9: Job Category Distribution ───────────────────────────────────
    section("9. JOB CATEGORY DISTRIBUTION")
    if "job_category_clean" in clean.columns:
        print(clean["job_category_clean"].value_counts().to_string())

    # ── Check 10: Source Distribution ────────────────────────────────────────
    section("10. SOURCE DISTRIBUTION")
    if "source" in clean.columns:
        print(clean["source"].value_counts().to_string())

# ── Final Summary ─────────────────────────────────────────────────────────────
section("VALIDATION SUMMARY")
total = passed + failed
print(f"  Passed: {passed}/{total}")
print(f"  Failed: {failed}/{total}")

if failed == 0:
    print("\n  ✅ All checks passed. Pipeline output is valid.")
else:
    print(f"\n  ⚠️  {failed} check(s) failed. Review output above.")
    sys.exit(1)