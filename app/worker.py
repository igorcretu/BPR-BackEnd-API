"""Background worker that processes queued prediction jobs."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

from sqlalchemy import asc
from sqlalchemy.exc import SQLAlchemyError

from app.main import app, predictor  # Reuse configured Flask app & predictor setup
from app.models import PredictionJob, db
from app.ml.predictor import CarPricePredictor

logger = logging.getLogger("prediction_worker")
logging.basicConfig(level=logging.INFO)

POLL_INTERVAL = float(os.getenv("PREDICTION_QUEUE_POLL_INTERVAL", "1.5"))
MAX_ATTEMPTS = int(os.getenv("PREDICTION_QUEUE_MAX_ATTEMPTS", "3"))


def _ensure_predictor():
    global predictor  # reuse if already initialized
    if predictor:
        return predictor
    logger.info("Prediction worker creating ML predictor instance...")
    predictor = CarPricePredictor()
    return predictor


def _fetch_next_job():
    return (
        db.session.query(PredictionJob)
        .filter(PredictionJob.status == 'pending')
        .order_by(asc(PredictionJob.priority), asc(PredictionJob.created_at))
        .with_for_update(skip_locked=True)
        .first()
    )


def _mark_job_failed(job: PredictionJob, *, error: str):
    job.status = 'failed'
    job.error_message = error[:4000]
    job.last_error_at = datetime.utcnow()
    job.completed_at = datetime.utcnow()
    db.session.commit()


def _process_job(job: PredictionJob):
    job.status = 'processing'
    job.started_at = datetime.utcnow()
    job.attempts = (job.attempts or 0) + 1
    db.session.commit()

    predictor_instance = _ensure_predictor()
    if not predictor_instance:
        raise RuntimeError('Predictor instance could not be created')

    try:
        result = predictor_instance.predict(job.payload)
        job.result = result
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.session.commit()
        logger.info("Completed job %s", job.id)
    except Exception as exc:  # noqa: BLE001 - log and flag as failed
        logger.exception("Job %s failed", job.id)
        if job.attempts < MAX_ATTEMPTS:
            job.status = 'pending'
            job.error_message = str(exc)
            job.last_error_at = datetime.utcnow()
            db.session.commit()
        else:
            _mark_job_failed(job, error=str(exc))


def run_worker():
    logger.info("Prediction worker starting with poll interval %.2fs", POLL_INTERVAL)
    with app.app_context():
        while True:
            try:
                job = _fetch_next_job()
                if not job:
                    time.sleep(POLL_INTERVAL)
                    db.session.remove()
                    continue
                _process_job(job)
            except SQLAlchemyError as exc:
                logger.exception("Database error in worker: %s", exc)
                db.session.rollback()
                time.sleep(POLL_INTERVAL)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error in worker: %s", exc)
                time.sleep(POLL_INTERVAL)
            finally:
                db.session.remove()


def main():
    run_worker()


if __name__ == '__main__':
    main()
