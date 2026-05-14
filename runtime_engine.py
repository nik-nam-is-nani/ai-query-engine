"""
Runtime Engine - Async query execution with worker threads
"""
import uuid
import threading
import time
import queue
from datetime import datetime

# Thread-safe stores
JOB_STORE = {}
JOB_LOCK = threading.Lock()

# Worker queue
JOB_QUEUE = queue.Queue()

# Number of worker threads
NUM_WORKERS = 3


def submit_job(sql, source_id, connection_data=None):
    """Submit a job to the queue and return job_id"""
    job_id = str(uuid.uuid4())

    with JOB_LOCK:
        JOB_STORE[job_id] = {
            "status": "queued",
            "sql": sql,
            "source_id": source_id,
            "result": None,
            "execution_time_ms": None,
            "rows_scanned": None,
            "rows_returned": None,
            "memory_used_kb": None,
            "guardrail_events": [],
            "timestamp_start": None,
            "timestamp_end": None,
            "error": None,
            "cancelled": False
        }

    # Add to queue
    JOB_QUEUE.put(job_id)

    return job_id


def get_job(job_id):
    """Get job details"""
    with JOB_LOCK:
        return JOB_STORE.get(job_id, {}).copy()


def cancel_job(job_id):
    """Cancel a running job"""
    with JOB_LOCK:
        if job_id in JOB_STORE:
            JOB_STORE[job_id]["cancelled"] = True
            JOB_STORE[job_id]["status"] = "cancelled"
            return True
    return False


def worker_thread():
    """Worker thread that processes jobs from queue"""
    from connector_manager import get_connector, SESSION_STORE, SESSION_LOCK

    while True:
        try:
            job_id = JOB_QUEUE.get(timeout=1)
        except queue.Empty:
            continue

        # Get job details
        with JOB_LOCK:
            job = JOB_STORE.get(job_id)
            if not job:
                JOB_QUEUE.task_done()
                continue

        # Check if cancelled
        if job.get("cancelled"):
            JOB_QUEUE.task_done()
            continue

        # Update status to running
        with JOB_LOCK:
            JOB_STORE[job_id]["status"] = "running"
            JOB_STORE[job_id]["timestamp_start"] = datetime.now().isoformat()

        start_time = time.time()

        try:
            # Get connector from session store
            source_id = job["source_id"]

            # Handle CSV sources (in-memory)
            if source_id.startswith("csv-"):
                from csv_analyzer import analyze_csv
                # CSV connections are stored differently
                with SESSION_LOCK:
                    session = SESSION_STORE.get(source_id)
                    if session and "connector" in session:
                        connector = session["connector"]
                        cursor = connector.cursor()
                        cursor.execute(job["sql"])
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            results = cursor.fetchall()
                            result = [dict(zip(columns, row)) for row in results]
                        else:
                            result = []
                        cursor.close()
                    else:
                        raise Exception("CSV source not found")
            else:
                # Regular database connection
                with SESSION_LOCK:
                    session = SESSION_STORE.get(source_id)
                    if session and "connector" in session:
                        connector = session["connector"]
                        result = connector.run_query(job["sql"])
                    else:
                        raise Exception("Connection not found")

            # Check if cancelled during execution
            with JOB_LOCK:
                if JOB_STORE[job_id].get("cancelled"):
                    JOB_QUEUE.task_done()
                    continue

            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)

            # Update job with results
            with JOB_LOCK:
                JOB_STORE[job_id].update({
                    "status": "done",
                    "result": result,
                    "execution_time_ms": execution_time_ms,
                    "rows_scanned": len(result) if result else 0,
                    "rows_returned": len(result) if result else 0,
                    "memory_used_kb": 0,  # Simplified
                    "timestamp_end": datetime.now().isoformat()
                })

        except Exception as e:
            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000) if start_time else 0

            with JOB_LOCK:
                JOB_STORE[job_id].update({
                    "status": "error",
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                    "timestamp_end": datetime.now().isoformat()
                })

        JOB_QUEUE.task_done()


def start_workers():
    """Start the worker thread pool"""
    for i in range(NUM_WORKERS):
        t = threading.Thread(target=worker_thread, daemon=True, name=f"Worker-{i}")
        t.start()
        print(f"Started worker thread: {t.name}")


def get_stream_generator(job_id):
    """Generate SSE stream data for a job"""
    import time
    import json

    while True:
        job = get_job(job_id)

        if not job:
            yield "data: {\"error\": \"Job not found\"}\n\n"
            break

        status = job.get("status", "unknown")

        # Send status update
        payload = {
            "status": status,
            "job_id": job_id,
            "sql": job.get("sql"),
            "execution_time_ms": job.get("execution_time_ms"),
            "rows_scanned": job.get("rows_scanned"),
            "rows_returned": job.get("rows_returned")
        }

        if status == "done":
            payload["result"] = job.get("result")
            yield f"data: {json.dumps(payload)}\n\n"
            break

        elif status == "error":
            payload["error"] = job.get("error")
            yield f"data: {json.dumps(payload)}\n\n"
            break

        elif status == "cancelled":
            payload["error"] = "Query cancelled by user"
            yield f"data: {json.dumps(payload)}\n\n"
            break

        # Send running status
        yield f"data: {json.dumps(payload)}\n\n"

        # Check for termination
        if status in ["done", "error", "cancelled"]:
            break

        # Wait before next poll
        time.sleep(0.2)