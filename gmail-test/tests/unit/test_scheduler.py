"""Tests for job scheduling and background tasks."""

import pytest
import time
from datetime import datetime, timedelta
from src.scheduler import (
    Job, JobResult, JobStatus, JobType, RecurrenceType,
    JobExecutor, Scheduler, JobMonitor, JobRetry, JobHistory,
    CronJobScheduler
)


class TestJobStatus:
    """Test JobStatus enum."""
    
    def test_status_values(self):
        """Test status values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"


class TestJobType:
    """Test JobType enum."""
    
    def test_job_types(self):
        """Test job types."""
        assert JobType.SYNC.value == "sync"
        assert JobType.EXPORT.value == "export"
        assert JobType.BACKUP.value == "backup"


class TestRecurrenceType:
    """Test RecurrenceType enum."""
    
    def test_recurrence_types(self):
        """Test recurrence types."""
        assert RecurrenceType.ONCE.value == "once"
        assert RecurrenceType.DAILY.value == "daily"
        assert RecurrenceType.WEEKLY.value == "weekly"


class TestJobResult:
    """Test JobResult class."""
    
    def test_creation(self):
        """Test result creation."""
        result = JobResult(
            job_id="123",
            status=JobStatus.COMPLETED
        )
        assert result.job_id == "123"
        assert result.status == JobStatus.COMPLETED
    
    def test_to_dict(self):
        """Test converting to dict."""
        result = JobResult(
            job_id="123",
            status=JobStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        data = result.to_dict()
        assert data["job_id"] == "123"
        assert data["status"] == "completed"
    
    def test_with_error(self):
        """Test result with error."""
        result = JobResult(
            job_id="123",
            status=JobStatus.FAILED,
            error="Test error"
        )
        assert result.error == "Test error"


class TestJob:
    """Test Job class."""
    
    def test_creation(self):
        """Test job creation."""
        def dummy_func():
            return "result"
        
        job = Job(
            id="123",
            name="Test Job",
            job_type=JobType.SYNC,
            func=dummy_func
        )
        assert job.id == "123"
        assert job.name == "Test Job"
        assert job.status == JobStatus.PENDING
    
    def test_is_ready(self):
        """Test job ready check."""
        def dummy_func():
            pass
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func
        )
        assert job.is_ready() is True
    
    def test_is_ready_disabled(self):
        """Test disabled job not ready."""
        def dummy_func():
            pass
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func,
            enabled=False
        )
        assert job.is_ready() is False
    
    def test_is_ready_future_scheduled(self):
        """Test future scheduled job not ready."""
        def dummy_func():
            pass
        
        future_time = datetime.now() + timedelta(hours=1)
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func,
            scheduled_for=future_time
        )
        assert job.is_ready() is False


class TestJobExecutor:
    """Test JobExecutor."""
    
    def test_execute_success(self):
        """Test successful execution."""
        def dummy_func():
            return {"result": "success"}
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func
        )
        
        executor = JobExecutor()
        result = executor.execute(job)
        
        assert result.status == JobStatus.COMPLETED
        assert result.job_id == "123"
        assert result.duration_seconds >= 0
    
    def test_execute_failure(self):
        """Test execution failure."""
        def failing_func():
            raise ValueError("Test error")
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=failing_func
        )
        
        executor = JobExecutor()
        result = executor.execute(job)
        
        assert result.status == JobStatus.FAILED
        assert result.error is not None
    
    def test_execute_with_args(self):
        """Test execution with arguments."""
        def add_func(a, b):
            return {"result": a + b}
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=add_func,
            args=(2, 3)
        )
        
        executor = JobExecutor()
        result = executor.execute(job)
        
        assert result.status == JobStatus.COMPLETED
        assert result.result_data["result"] == 5


class TestScheduler:
    """Test Scheduler."""
    
    def test_add_job(self):
        """Test adding job."""
        def dummy_func():
            pass
        
        scheduler = Scheduler()
        job_id = scheduler.add_job("Test", JobType.SYNC, dummy_func)
        
        assert job_id is not None
        assert scheduler.get_job(job_id) is not None
    
    def test_schedule_job(self):
        """Test scheduling job."""
        def dummy_func():
            pass
        
        scheduler = Scheduler()
        job_id = scheduler.add_job("Test", JobType.SYNC, dummy_func)
        
        future_time = datetime.now() + timedelta(hours=1)
        scheduler.schedule_job(job_id, scheduled_for=future_time)
        
        job = scheduler.get_job(job_id)
        assert job.scheduled_for == future_time
    
    def test_cancel_job(self):
        """Test cancelling job."""
        def dummy_func():
            pass
        
        scheduler = Scheduler()
        job_id = scheduler.add_job("Test", JobType.SYNC, dummy_func)
        
        job = scheduler.get_job(job_id)
        job.status = JobStatus.RUNNING
        
        scheduler.cancel_job(job_id)
        assert job.status == JobStatus.CANCELLED
    
    def test_get_jobs_by_status(self):
        """Test getting jobs by status."""
        def dummy_func():
            pass
        
        scheduler = Scheduler()
        job_id = scheduler.add_job("Test", JobType.SYNC, dummy_func)
        
        pending_jobs = scheduler.get_jobs_by_status(JobStatus.PENDING)
        assert len(pending_jobs) > 0
    
    def test_get_ready_jobs(self):
        """Test getting ready jobs."""
        def dummy_func():
            pass
        
        scheduler = Scheduler()
        job_id = scheduler.add_job("Test", JobType.SYNC, dummy_func)
        
        ready_jobs = scheduler.get_ready_jobs()
        assert len(ready_jobs) > 0
    
    def test_get_results(self):
        """Test getting results."""
        scheduler = Scheduler()
        results = scheduler.get_results()
        assert isinstance(results, list)


class TestJobMonitor:
    """Test JobMonitor."""
    
    def test_collect_metrics(self):
        """Test collecting metrics."""
        def dummy_func():
            return {}
        
        scheduler = Scheduler()
        monitor = JobMonitor(scheduler)
        
        job_id = scheduler.add_job("Test", JobType.SYNC, dummy_func)
        
        metrics = monitor.collect_metrics()
        assert metrics["total_jobs"] >= 1
        assert "pending_jobs" in metrics
        assert "completed_jobs" in metrics
    
    def test_success_rate(self):
        """Test success rate calculation."""
        scheduler = Scheduler()
        monitor = JobMonitor(scheduler)
        
        # Add some results
        result1 = JobResult("1", JobStatus.COMPLETED)
        result2 = JobResult("2", JobStatus.FAILED)
        scheduler.results.append(result1)
        scheduler.results.append(result2)
        
        metrics = monitor.collect_metrics()
        assert metrics["success_rate"] == 50.0


class TestJobRetry:
    """Test JobRetry."""
    
    def test_should_retry_success(self):
        """Test no retry on success."""
        def dummy_func():
            pass
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func
        )
        
        result = JobResult("123", JobStatus.COMPLETED)
        retry = JobRetry()
        
        assert retry.should_retry(result, job) is False
    
    def test_should_retry_failure(self):
        """Test retry on failure."""
        def dummy_func():
            pass
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func
        )
        
        result = JobResult("123", JobStatus.FAILED)
        retry = JobRetry()
        
        assert retry.should_retry(result, job) is True
    
    def test_max_retries_exceeded(self):
        """Test max retries exceeded."""
        def dummy_func():
            pass
        
        job = Job(
            id="123",
            name="Test",
            job_type=JobType.SYNC,
            func=dummy_func,
            max_retries=2
        )
        
        result = JobResult("123", JobStatus.FAILED, retries=2)
        retry = JobRetry()
        
        assert retry.should_retry(result, job) is False
    
    def test_retry_delay(self):
        """Test retry delay calculation."""
        retry = JobRetry(backoff_factor=2.0)
        
        assert retry.get_retry_delay(0) == 1.0
        assert retry.get_retry_delay(1) == 2.0
        assert retry.get_retry_delay(2) == 4.0


class TestJobHistory:
    """Test JobHistory."""
    
    def test_add_result(self):
        """Test adding result to history."""
        history = JobHistory()
        result = JobResult("123", JobStatus.COMPLETED)
        
        history.add(result)
        assert len(history.get_all()) == 1
    
    def test_get_all(self):
        """Test getting all history."""
        history = JobHistory()
        results = [JobResult(str(i), JobStatus.COMPLETED) for i in range(3)]
        
        for r in results:
            history.add(r)
        
        assert len(history.get_all()) == 3
    
    def test_get_by_job_id(self):
        """Test getting history by job ID."""
        history = JobHistory()
        result1 = JobResult("123", JobStatus.COMPLETED)
        result2 = JobResult("124", JobStatus.COMPLETED)
        
        history.add(result1)
        history.add(result2)
        
        job_history = history.get_by_job_id("123")
        assert len(job_history) == 1
    
    def test_get_by_status(self):
        """Test getting history by status."""
        history = JobHistory()
        result1 = JobResult("123", JobStatus.COMPLETED)
        result2 = JobResult("124", JobStatus.FAILED)
        
        history.add(result1)
        history.add(result2)
        
        completed = history.get_by_status(JobStatus.COMPLETED)
        assert len(completed) == 1
    
    def test_max_history(self):
        """Test max history limit."""
        history = JobHistory(max_history=5)
        
        for i in range(10):
            result = JobResult(str(i), JobStatus.COMPLETED)
            history.add(result)
        
        assert len(history.get_all()) == 5


class TestCronJobScheduler:
    """Test CronJobScheduler."""
    
    def test_add_cron_job(self):
        """Test adding cron job."""
        def dummy_func():
            return {}
        
        scheduler = Scheduler()
        cron_scheduler = CronJobScheduler(scheduler)
        
        job_id = cron_scheduler.add_cron_job("Test", dummy_func, "0 * * * *")
        assert job_id is not None
    
    def test_remove_cron_job(self):
        """Test removing cron job."""
        def dummy_func():
            return {}
        
        scheduler = Scheduler()
        cron_scheduler = CronJobScheduler(scheduler)
        
        job_id = cron_scheduler.add_cron_job("Test", dummy_func, "0 * * * *")
        cron_scheduler.remove_cron_job(job_id)
        
        assert job_id not in cron_scheduler.cron_jobs


class TestSchedulerIntegration:
    """Integration tests for scheduler."""
    
    def test_job_execution_flow(self):
        """Test complete job execution flow."""
        execution_count = 0
        
        def test_func():
            nonlocal execution_count
            execution_count += 1
            return {"executed": True}
        
        scheduler = Scheduler(max_workers=1)
        job_id = scheduler.add_job("Test", JobType.SYNC, test_func)
        
        job = scheduler.get_job(job_id)
        executor = JobExecutor()
        result = executor.execute(job)
        
        assert result.status == JobStatus.COMPLETED
        assert execution_count == 1
    
    def test_scheduler_workflow(self):
        """Test scheduler workflow."""
        def dummy_func():
            return {}
        
        scheduler = Scheduler()
        
        # Add multiple jobs
        job_ids = [
            scheduler.add_job(f"Job {i}", JobType.SYNC, dummy_func)
            for i in range(3)
        ]
        
        assert len(scheduler.jobs) == 3
        assert len(scheduler.get_jobs_by_status(JobStatus.PENDING)) == 3
