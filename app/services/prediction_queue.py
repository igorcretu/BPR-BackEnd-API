"""Helpers for managing asynchronous prediction jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from sqlalchemy import and_, func, or_

from app.models import PredictionJob, db

PENDING_STATUSES: Tuple[str, ...] = ("pending", "processing")


@dataclass(frozen=True)
class QueueDecision:
    mode: str
    reason: str


def enqueue_job(payload: dict, *, priority: int = 100) -> PredictionJob:
    job = PredictionJob()
    job.priority = priority
    job.payload = payload
    db.session.add(job)
    db.session.commit()
    return job


def get_job(job_id: str) -> Optional[PredictionJob]:
    if not job_id:
        return None
    return db.session.get(PredictionJob, job_id)


def _pending_status_filter(query, *, include_processing: bool = True):
    statuses: Tuple[str, ...]
    if include_processing:
        statuses = PENDING_STATUSES
    else:
        statuses = ("pending",)
    if len(statuses) == 1:
        return query.filter(PredictionJob.status == statuses[0])
    return query.filter(PredictionJob.status.in_(statuses))


def count_pending_jobs(*, include_processing: bool = True) -> int:
    query = db.session.query(func.count(PredictionJob.id))
    query = _pending_status_filter(query, include_processing=include_processing)
    return query.scalar() or 0


def calculate_position(job: PredictionJob) -> Optional[int]:
    if job.status not in PENDING_STATUSES:
        return None

    ahead = (
        db.session.query(func.count(PredictionJob.id))
        .filter(PredictionJob.status.in_(tuple(PENDING_STATUSES)))
        .filter(
            or_(
                PredictionJob.priority < job.priority,
                and_(
                    PredictionJob.priority == job.priority,
                    PredictionJob.created_at < job.created_at,
                ),
            )
        )
        .scalar()
    )
    return int(ahead or 0)


def decide_dispatch_mode(
    *,
    queue_mode: str,
    requested_mode: Optional[str],
    queue_threshold: int,
) -> QueueDecision:
    normalized_request = (requested_mode or "").strip().lower()
    if normalized_request in {"queue", "async"}:
        return QueueDecision(mode="queue", reason="client_force_queue")
    if normalized_request == "sync":
        return QueueDecision(mode="sync", reason="client_force_sync")

    normalized_default = queue_mode.lower()
    if normalized_default == "queue":
        return QueueDecision(mode="queue", reason="default_queue_mode")
    if normalized_default == "sync":
        return QueueDecision(mode="sync", reason="default_sync_mode")

    # Hybrid mode: inspect backlog size
    backlog = count_pending_jobs()
    if backlog >= queue_threshold:
        return QueueDecision(mode="queue", reason=f"backlog_{backlog}")
    return QueueDecision(mode="sync", reason="backlog_ok")
