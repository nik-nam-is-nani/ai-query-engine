"""
Realtime Monitor - Background thread tracking session metrics
"""
import threading
import time
from datetime import datetime, timedelta

# Module-level metrics storage
SESSION_METRICS = {
    "total_queries": 0,
    "avg_execution_time_ms": 0,
    "slowest_query_ms": 0,
    "fastest_query_ms": 0,
    "error_rate_pct": 0,
    "total_rows_processed": 0,
    "most_used_source": None,
    "most_queried_table": None,
    "last_updated": None
}

METRICS_LOCK = threading.Lock()


def update_metrics():
    """Update session metrics from job and session stores"""
    from runtime_engine import JOB_STORE, JOB_LOCK
    from connector_manager import SESSION_STORE, SESSION_LOCK

    with JOB_LOCK:
        jobs = list(JOB_STORE.values())

    with SESSION_LOCK:
        sources = list(SESSION_STORE.keys())

    if not jobs:
        return

    # Calculate metrics
    completed_jobs = [j for j in jobs if j.get("status") == "done"]
    error_jobs = [j for j in jobs if j.get("status") == "error"]
    total_jobs = len(jobs)

    total_queries = len(completed_jobs)
    total_rows = sum(j.get("rows_returned", 0) or 0 for j in completed_jobs)
    total_time = sum(j.get("execution_time_ms", 0) or 0 for j in completed_jobs)

    execution_times = [j.get("execution_time_ms", 0) or 0 for j in completed_jobs if j.get("execution_time_ms")]

    with METRICS_LOCK:
        SESSION_METRICS["total_queries"] = total_queries
        SESSION_METRICS["total_rows_processed"] = total_rows

        if execution_times:
            SESSION_METRICS["avg_execution_time_ms"] = int(total_time / len(execution_times))
            SESSION_METRICS["slowest_query_ms"] = max(execution_times)
            SESSION_METRICS["fastest_query_ms"] = min(execution_times)

        if total_jobs > 0:
            SESSION_METRICS["error_rate_pct"] = round((len(error_jobs) / total_jobs) * 100, 1)
        else:
            SESSION_METRICS["error_rate_pct"] = 0

        if sources:
            # Find most used source
            source_counts = {}
            for job in jobs:
                sid = job.get("source_id", "unknown")
                source_counts[sid] = source_counts.get(sid, 0) + 1

            most_used = max(source_counts.items(), key=lambda x: x[1])
            with SESSION_LOCK:
                for sid, name in SESSION_STORE.items():
                    if sid == most_used[0]:
                        SESSION_METRICS["most_used_source"] = name.get("nickname", sid)
                        break

        SESSION_METRICS["last_updated"] = datetime.now().isoformat()


def monitor_loop():
    """Background loop that updates metrics every 5 seconds"""
    while True:
        try:
            update_metrics()
        except Exception as e:
            print(f"Error updating metrics: {e}")

        time.sleep(5)


def start_monitor():
    """Start the background monitor thread"""
    t = threading.Thread(target=monitor_loop, daemon=True, name="MetricsMonitor")
    t.start()
    print("Started realtime monitor thread")


def get_metrics():
    """Get current session metrics"""
    with METRICS_LOCK:
        return SESSION_METRICS.copy()