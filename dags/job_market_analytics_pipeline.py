from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import shutil
import os
import json

# ── Default Args ──────────────────────────────────────────────────────────────
default_args = {
    "owner":            "airflow",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=2),
}

# ── Paths inside Docker container ─────────────────────────────────────────────
SCRIPTS_DIR = "/opt/airflow/scripts"
DATA_DIR    = "/opt/airflow/data"

# ── DAG Definition ────────────────────────────────────────────────────────────
with DAG(
    dag_id="job_market_analytics_pipeline",
    default_args=default_args,
    description="End-to-end job market analytics pipeline",
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["job_market", "analytics"],
) as dag:

    # ── Task 1a: Extract Arbeitnow ────────────────────────────────────────────
    extract_arbeitnow = BashOperator(
        task_id="extract_arbeitnow",
        bash_command=f"python {SCRIPTS_DIR}/extract_arbeitnow.py",
    )

    # ── Task 1b: Extract RemoteOK ─────────────────────────────────────────────
    extract_remoteok = BashOperator(
        task_id="extract_remoteok",
        bash_command=f"python {SCRIPTS_DIR}/extract_remoteok.py",
    )

    # ── Task 1c: Extract Himalayas ────────────────────────────────────────────
    extract_himalayas = BashOperator(
        task_id="extract_himalayas",
        bash_command=f"python {SCRIPTS_DIR}/extract_himalayas.py",
    )

    # ── Task 1d: Extract RemoteJobs ───────────────────────────────────────────
    extract_remotejobs = BashOperator(
        task_id="extract_remotejobs",
        bash_command=f"python {SCRIPTS_DIR}/extract_remotejobs.py",
    )

    # ── Task 2: Merge Sources ─────────────────────────────────────────────────
    merge_sources = BashOperator(
        task_id="merge_sources",
        bash_command=f"python {SCRIPTS_DIR}/merge_sources.py",
    )

    # ── Task 3: Run KNIME via Flask API ───────────────────────────────────────
    def run_knime_workflow():
        import requests

        # Flask API runs on Windows host
        # From inside Docker use host.docker.internal
        flask_url = "http://host.docker.internal:8005/run-knime"
        headers   = {"X-API-Key": "my-secret-key"}

        print(f"Calling Flask API at {flask_url}")

        try:
            response = requests.post(
                flask_url,
                headers=headers,
                timeout=7200  # 2 hour timeout for KNIME
            )

            print(f"Flask response status: {response.status_code}")
            print(f"Flask response body: {response.text}")

            if response.status_code != 200:
                raise Exception(
                    f"Flask API returned error {response.status_code}: {response.text}"
                )

            result = response.json()
            if result.get("status") != "success":
                raise Exception(
                    f"KNIME workflow failed: {result.get('message')}"
                )

            print("KNIME workflow completed successfully via Flask API")

        except requests.exceptions.ConnectionError:
            raise Exception(
                "Cannot connect to Flask API at host.docker.internal:8005. "
                "Make sure knime_flask_api.py is running on Windows."
            )

    run_knime = PythonOperator(
        task_id="run_knime_workflow",
        python_callable=run_knime_workflow,
    )

    # ── Task 4: Validate Outputs ──────────────────────────────────────────────
    validate_outputs = BashOperator(
        task_id="validate_clean_output",
        bash_command=f"python {SCRIPTS_DIR}/validate_outputs.py",
    )

    # ── Task 5: Calculate Metrics ─────────────────────────────────────────────
    calculate_metrics = BashOperator(
        task_id="calculate_metrics",
        bash_command=f"python {SCRIPTS_DIR}/calculate_metrics.py",
    )

    # ── Task 6: Trigger n8n Webhook ───────────────────────────────────────────
    def trigger_n8n(**context):
        import urllib.request
        import json

        metrics_file = f"{DATA_DIR}/processed/metrics_summary.csv"
        clean_file   = f"{DATA_DIR}/processed/clean_ai_ml_data_jobs.csv"

        # Default payload
        payload = {
            "pipeline_status":        "success",
            "total_jobs":             0,
            "jobs_by_source":         "",
            "remote_ratio":           0,
            "remote_count":           0,
            "onsite_count":           0,
            "hybrid_count":           0,
            "entry_level_jobs":       0,
            "salary_mentioned_count": 0,
            "avg_salary_usd":         0,
        }

        try:
            import pandas as pd

            clean   = pd.read_csv(clean_file)
            metrics = pd.read_csv(metrics_file)

            payload["total_jobs"]    = len(clean)
            source_counts            = clean["source"].value_counts().to_dict()
            payload["jobs_by_source"] = ", ".join(
                [f"{k}: {v}" for k, v in source_counts.items()]
            )
            payload["remote_count"]  = int((clean["remote_status"] == "Remote").sum())
            payload["onsite_count"]  = int((clean["remote_status"] == "On-site").sum())
            payload["hybrid_count"]  = int((clean["remote_status"] == "Hybrid").sum())
            payload["remote_ratio"]  = round(
                payload["remote_count"] / len(clean) * 100, 1
            )
            payload["entry_level_jobs"] = int(
                (clean["experience_bracket"] == "0-1").sum()
            )
            salary_col = pd.to_numeric(clean["salary_mid_usd"], errors="coerce")
            payload["salary_mentioned_count"] = int(salary_col.notna().sum())

            salary_row = metrics[metrics["metric"] == "avg_salary_usd"]
            if not salary_row.empty and pd.notna(salary_row.iloc[0]["value"]):
                payload["avg_salary_usd"] = float(salary_row.iloc[0]["value"])

        except Exception as e:
            print(f"Warning: Could not build full payload: {e}")
            payload["pipeline_status"] = f"success_with_warning: {str(e)}"

        # Send to n8n
        n8n_url = "http://host.docker.internal:5678/webhook/job-market-alert"
        print(f"Sending payload to n8n: {json.dumps(payload, indent=2)}")

        try:
            data = json.dumps(payload).encode("utf-8")
            req  = urllib.request.Request(
                n8n_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                print(f"n8n response: {response.status} {response.read().decode()}")
        except Exception as e:
            print(f"Warning: n8n webhook failed: {e}")
            print("Pipeline completed successfully. n8n notification skipped.")

    trigger_n8n_workflow = PythonOperator(
        task_id="trigger_n8n_workflow",
        python_callable=trigger_n8n,
        provide_context=True,
    )

    # ── Task 7: Archive Outputs ───────────────────────────────────────────────
    def archive_outputs():
        from datetime import date
        timestamp   = date.today().strftime("%Y%m%d")
        archive_dir = f"{DATA_DIR}/archive/{timestamp}"
        os.makedirs(archive_dir, exist_ok=True)

        files_to_archive = [
            f"{DATA_DIR}/merged/merged_raw_jobs.csv",
            f"{DATA_DIR}/processed/clean_ai_ml_data_jobs.csv",
            f"{DATA_DIR}/processed/metrics_summary.csv",
        ]

        for filepath in files_to_archive:
            if os.path.exists(filepath):
                filename = os.path.basename(filepath)
                dest     = os.path.join(archive_dir, filename)
                shutil.copy2(filepath, dest)
                print(f"Archived: {filename} → {archive_dir}")
            else:
                print(f"Warning: File not found: {filepath}")

        print(f"Archive complete → {archive_dir}")

    archive_task = PythonOperator(
        task_id="archive_outputs",
        python_callable=archive_outputs,
    )

    # ── Task Dependencies ─────────────────────────────────────────────────────
    [
        extract_arbeitnow,
        extract_remoteok,
        extract_himalayas,
        extract_remotejobs,
    ] >> merge_sources

    merge_sources >> run_knime >> validate_outputs >> calculate_metrics >> trigger_n8n_workflow >> archive_task