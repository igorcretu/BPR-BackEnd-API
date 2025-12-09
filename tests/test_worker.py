"""Tests for worker module functions."""
import pytest
from unittest.mock import Mock, patch
from app.worker import _ensure_predictor, _mark_job_failed
from app.models import PredictionJob
from datetime import datetime


class TestWorkerFunctions:
    """Test worker helper functions."""
    
    def test_ensure_predictor_returns_predictor(self, app):
        """Test _ensure_predictor returns a predictor instance."""
        with app.app_context():
            predictor = _ensure_predictor()
            assert predictor is not None
    
    def test_mark_job_failed(self, app):
        """Test marking a job as failed."""
        with app.app_context():
            from app.models import db
            
            # Create a test job
            job = PredictionJob(
                payload={'brand': 'Test', 'model': 'Car', 'year': 2020},
                priority=100,
                status='processing'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id
            
            # Mark it as failed
            _mark_job_failed(job, error='Test error')
            
            # Verify the job was marked as failed
            failed_job = db.session.get(PredictionJob, job_id)
            assert failed_job.status == 'failed'
            assert 'Test error' in failed_job.error_message
            assert failed_job.completed_at is not None
    
    def test_fetch_next_job(self, app):
        """Test fetching next pending job."""
        from app.worker import _fetch_next_job
        from app.models import db
        
        with app.app_context():
            # Create two jobs with different priorities
            job1 = PredictionJob(
                payload={'brand': 'Test1', 'model': 'Car1', 'year': 2020},
                priority=200,
                status='pending'
            )
            job2 = PredictionJob(
                payload={'brand': 'Test2', 'model': 'Car2', 'year': 2021},
                priority=100,  # Lower priority = higher importance
                status='pending'
            )
            db.session.add(job1)
            db.session.add(job2)
            db.session.commit()
            
            # Fetch next job should return the one with lower priority number
            next_job = _fetch_next_job()
            assert next_job is not None
            # Should be job2 because it has lower priority number (100 < 200)
            assert next_job.priority == 100
    
    def test_process_job_success(self, app):
        """Test processing a job successfully."""
        from app.worker import _process_job
        from app.models import db
        
        with app.app_context():
            # Create a test job
            job = PredictionJob(
                payload={
                    'brand': 'Toyota',
                    'model': 'Corolla',
                    'year': 2020,
                    'mileage': 45000,
                    'fuel_type': 'Benzin',
                    'transmission': 'Automatisk',
                    'body_type': 'Sedan'
                },
                priority=100,
                status='pending'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id
            
            # Process the job
            _process_job(job)
            
            # Refresh job from database
            processed_job = db.session.get(PredictionJob, job_id)
            # Job should be completed
            assert processed_job.status in ['completed', 'failed']
            assert processed_job.started_at is not None
    
    def test_mark_job_failed_with_long_error(self, app):
        """Test marking job as failed with a very long error message."""
        with app.app_context():
            from app.models import db
            
            job = PredictionJob(
                payload={'brand': 'Test', 'model': 'Car', 'year': 2020},
                priority=100,
                status='processing'
            )
            db.session.add(job)
            db.session.commit()
            
            # Create an error longer than 4000 characters
            long_error = 'A' * 5000
            _mark_job_failed(job, error=long_error)
            
            # Error should be truncated to 4000 characters
            assert len(job.error_message) <= 4000
            assert job.status == 'failed'
    
    def test_process_job_with_predictor_failure(self, app):
        """Test processing job when predictor fails."""
        from app.worker import _process_job
        from app.models import db
        from unittest.mock import patch
        
        with app.app_context():
            job = PredictionJob(
                payload={
                    'brand': 'Toyota',
                    'model': 'Corolla',
                    'year': 2020,
                    'mileage': 45000,
                    'fuel_type': 'Benzin',
                    'transmission': 'Automatisk',
                    'body_type': 'Sedan'
                },
                priority=100,
                status='pending',
                attempts=0
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id
            
            # Mock predictor to raise an exception
            with patch('app.worker._ensure_predictor') as mock_predictor:
                mock_instance = Mock()
                mock_instance.predict.side_effect = RuntimeError("Prediction failed")
                mock_predictor.return_value = mock_instance
                
                _process_job(job)
                
                # Job should be marked as pending for retry (first attempt)
                processed_job = db.session.get(PredictionJob, job_id)
                assert processed_job.status == 'pending'
                assert processed_job.attempts == 1
                assert processed_job.error_message is not None
    
    def test_process_job_max_attempts_exceeded(self, app):
        """Test processing job when max attempts exceeded."""
        from app.worker import _process_job, MAX_ATTEMPTS
        from app.models import db
        from unittest.mock import patch
        
        with app.app_context():
            job = PredictionJob(
                payload={
                    'brand': 'Toyota',
                    'model': 'Corolla',
                    'year': 2020,
                    'mileage': 45000,
                    'fuel_type': 'Benzin',
                    'transmission': 'Automatisk',
                    'body_type': 'Sedan'
                },
                priority=100,
                status='pending',
                attempts=MAX_ATTEMPTS - 1  # Set to one less than max
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id
            
            # Mock predictor to raise an exception
            with patch('app.worker._ensure_predictor') as mock_predictor:
                mock_instance = Mock()
                mock_instance.predict.side_effect = RuntimeError("Prediction failed")
                mock_predictor.return_value = mock_instance
                
                _process_job(job)
                
                # Job should be marked as failed after max attempts
                processed_job = db.session.get(PredictionJob, job_id)
                assert processed_job.status == 'failed'
                assert processed_job.attempts == MAX_ATTEMPTS


class TestPredictionQueueService:
    """Test prediction queue service functions."""
    
    def test_enqueue_and_get_job(self, app):
        """Test enqueueing and retrieving a job."""
        from app.services.prediction_queue import enqueue_job, get_job
        from app.models import db
        
        with app.app_context():
            # Enqueue a job
            job = enqueue_job(
                payload={'brand': 'BMW', 'model': 'X5', 'year': 2021},
                priority=50
            )
            assert job is not None
            assert job.status == 'pending'
            
            # Retrieve the job
            retrieved_job = get_job(job.id)
            assert retrieved_job is not None
            assert retrieved_job.id == job.id
