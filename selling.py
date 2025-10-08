import threading
import time
import uuid
from typing import Dict, List, Any

from utils import logger
from security import SecurityConfig


_sell_jobs: Dict[str, Dict[str, Any]] = {}
_sell_jobs_lock = threading.Lock()


def list_supported_platforms() -> List[str]:
    """Return the supported platforms that can be posted to."""
    return ["facebook", "craigslist", "ksl"]


def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, str):
            sanitized[key] = SecurityConfig.sanitize_input(value)
        else:
            sanitized[key] = value
    return sanitized


def create_sell_job(details: Dict[str, Any], platforms: List[str]) -> str:
    """Create a selling job and start background processing.

    Returns the job_id for status polling.
    """
    allowed = set(list_supported_platforms())
    selected = [p for p in platforms if p in allowed]
    if not selected:
        raise ValueError("No valid platforms selected")

    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "status": "queued",
        "platforms": {p: {"status": "queued", "message": None} for p in selected},
        "details": _sanitize_details(details),
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    with _sell_jobs_lock:
        _sell_jobs[job_id] = job

    t = threading.Thread(target=_process_sell_job, args=(job_id,), daemon=True, name=f"sell_job_{job_id}")
    t.start()

    logger.info(f"Created sell job {job_id} for platforms: {', '.join(selected)}")
    return job_id


def get_job_status(job_id: str) -> Dict[str, Any]:
    with _sell_jobs_lock:
        job = _sell_jobs.get(job_id)
        if not job:
            return {"error": "job_not_found"}
        # Return a shallow copy to avoid external mutation
        return {
            "id": job["id"],
            "status": job["status"],
            "platforms": job["platforms"],
            "error": job["error"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        }


def _process_sell_job(job_id: str) -> None:
    """Background worker to process a selling job across platforms."""
    with _sell_jobs_lock:
        job = _sell_jobs.get(job_id)
    if not job:
        return

    try:
        _update_job(job_id, status="in_progress")
        details = job["details"]
        for platform, state in job["platforms"].items():
            _update_platform(job_id, platform, status="in_progress", message="Posting...")
            try:
                # Stubbed platform posting - replace with real integrations
                success, message = _post_to_platform(platform, details)
                if success:
                    _update_platform(job_id, platform, status="completed", message=message)
                else:
                    _update_platform(job_id, platform, status="failed", message=message)
            except Exception as e:  # pragma: no cover - defensive
                logger.error(f"Error posting to {platform} for job {job_id}: {e}")
                _update_platform(job_id, platform, status="failed", message=str(e))

        # Determine overall status
        with _sell_jobs_lock:
            plat_statuses = [pstate["status"] for pstate in _sell_jobs[job_id]["platforms"].values()]
        if all(s == "completed" for s in plat_statuses):
            _update_job(job_id, status="completed")
        elif any(s == "completed" for s in plat_statuses):
            _update_job(job_id, status="partial")
        else:
            _update_job(job_id, status="failed")

    except Exception as e:  # pragma: no cover - defensive
        logger.error(f"Sell job {job_id} failed: {e}")
        _update_job(job_id, status="failed", error=str(e))


def _update_job(job_id: str, *, status: str | None = None, error: str | None = None) -> None:
    with _sell_jobs_lock:
        job = _sell_jobs.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if error is not None:
            job["error"] = error
        job["updated_at"] = time.time()


def _update_platform(job_id: str, platform: str, *, status: str | None = None, message: str | None = None) -> None:
    with _sell_jobs_lock:
        job = _sell_jobs.get(job_id)
        if not job:
            return
        platform_state = job["platforms"].get(platform)
        if not platform_state:
            return
        if status is not None:
            platform_state["status"] = status
        if message is not None:
            platform_state["message"] = message
        job["updated_at"] = time.time()


def _post_to_platform(platform: str, details: Dict[str, Any]) -> tuple[bool, str]:
    """Stub posting implementation for a platform.

    Replace with real API or browser automation per platform.
    """
    title = details.get("title") or "Listing"
    price = details.get("price")
    logger.info(f"Posting '{title}' (${price}) to {platform}...")
    # Simulate work
    time.sleep(1.5)
    # Simulate success
    return True, f"Posted to {platform}"

