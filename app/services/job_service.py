"""In-process progress registry for long-running dataset jobs.

Jobs live in memory only: a restart loses progress, and a single process is
assumed (development server). Progress counts come from the real worker loop.
"""
import threading
import time
from uuid import uuid4

_jobs = {}
_lock = threading.Lock()
MAX_JOBS = 200


def create_job(kind, dataset_id):
    job_id = uuid4().hex
    with _lock:
        if len(_jobs) >= MAX_JOBS:
            oldest = sorted(_jobs.values(), key=lambda item: item["started"])[:50]
            for item in oldest:
                _jobs.pop(item["id"], None)
        _jobs[job_id] = {
            "id": job_id,
            "kind": kind,
            "dataset_id": dataset_id,
            "status": "queued",
            "done": 0,
            "total": 0,
            "message": "Menunggu antrean",
            "started": time.time(),
        }
    return job_id


def update_job(job_id, **fields):
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.update(fields)


def get_job(job_id):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def progress_callback(job_id):
    def report(done, total):
        update_job(job_id, done=done, total=total, status="running",
                   message=f"Memproses {done} dari {total}")
    return report


def run_in_background(app, job_id, work):
    """Run work() with its own app context; failures are recorded, not raised."""
    def runner():
        with app.app_context():
            update_job(job_id, status="running", message="Mulai memproses")
            try:
                result = work()
                update_job(job_id, status="completed", message="Selesai", result=result)
            except Exception:
                app.logger.exception("Background job failed: %s", job_id)
                update_job(job_id, status="failed", message="Gagal memproses, periksa log server")

    thread = threading.Thread(target=runner, daemon=True, name=f"job-{job_id[:8]}")
    thread.start()
    return thread
