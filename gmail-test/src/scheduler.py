"""Job scheduling and background task management."""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Job types."""
    SYNC = "sync"
    EXPORT = "export"
    IMPORT = "import"
    CLEANUP = "cleanup"
    BACKUP = "backup"
    ANALYTICS = "analytics"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


class RecurrenceType(Enum):
    """Recurrence types."""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class JobResult:
    """Job execution result."""
    job_id: str
    status: JobStatus
    started_at: datetime = None
    completed_at: datetime = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    exception: Optional[Exception] = None
    duration_seconds: float = 0.0
    retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_data": self.result_data,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "retries": self.retries
        }


@dataclass
class Job:
    """Job definition."""
    id: str
    name: str
    job_type: JobType
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    recurrence: RecurrenceType = RecurrenceType.ONCE
    recurrence_interval: int = 1
    max_retries: int = 3
    timeout: int = 3600
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def is_ready(self) -> bool:
        """Check if job is ready to run."""
        if not self.enabled:
            return False
        
        if self.status not in [JobStatus.PENDING, JobStatus.COMPLETED, JobStatus.FAILED]:
            return False
        
        now = datetime.now()
        if self.scheduled_for and self.scheduled_for > now:
            return False
        
        return True


class JobExecutor:
    """Execute jobs."""
    
    def __init__(self, max_retries: int = 3):
        """Initialize executor."""
        self.max_retries = max_retries
    
    def execute(self, job: Job) -> JobResult:
        """Execute job."""
        result = JobResult(
            job_id=job.id,
            status=JobStatus.RUNNING,
            started_at=datetime.now()
        )
        
        try:
            job.status = JobStatus.RUNNING
            
            # Execute the job function
            result_data = job.func(*job.args, **job.kwargs)
            
            result.status = JobStatus.COMPLETED
            result.result_data = result_data if isinstance(result_data, dict) else {}
            job.status = JobStatus.COMPLETED
            job.last_run = datetime.now()
            
            logger.info(f"Job {job.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            result.status = JobStatus.FAILED
            result.error = str(e)
            result.exception = e
            job.status = JobStatus.FAILED
        
        finally:
            result.completed_at = datetime.now()
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
        
        return result


class Scheduler:
    """Schedule and manage jobs."""
    
    def __init__(self, max_workers: int = 5):
        """Initialize scheduler."""
        self.jobs: Dict[str, Job] = {}
        self.results: List[JobResult] = []
        self.executor = JobExecutor()
        self.max_workers = max_workers
        self.running = False
        self.worker_threads: List[threading.Thread] = []
        self.job_queue: List[Job] = []
        self.lock = threading.Lock()
    
    def add_job(self, name: str, job_type: JobType, func: Callable,
                args: tuple = None, kwargs: Dict = None) -> str:
        """Add job to scheduler."""
        job_id = str(uuid.uuid4())
        
        job = Job(
            id=job_id,
            name=name,
            job_type=job_type,
            func=func,
            args=args or (),
            kwargs=kwargs or {}
        )
        
        with self.lock:
            self.jobs[job_id] = job
        
        logger.info(f"Added job: {job_id} - {name}")
        return job_id
    
    def schedule_job(self, job_id: str, scheduled_for: datetime = None,
                    recurrence: RecurrenceType = RecurrenceType.ONCE) -> None:
        """Schedule job."""
        with self.lock:
            if job_id not in self.jobs:
                raise ValueError(f"Job not found: {job_id}")
            
            job = self.jobs[job_id]
            job.scheduled_for = scheduled_for or datetime.now()
            job.recurrence = recurrence
            job.next_run = job.scheduled_for
        
        logger.info(f"Scheduled job: {job_id}")
    
    def cancel_job(self, job_id: str) -> None:
        """Cancel job."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.CANCELLED
                    logger.info(f"Cancelled job: {job_id}")
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job."""
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs by status."""
        with self.lock:
            return [j for j in self.jobs.values() if j.status == status]
    
    def get_ready_jobs(self) -> List[Job]:
        """Get jobs ready to run."""
        with self.lock:
            return [j for j in self.jobs.values() if j.is_ready()]
    
    def start(self) -> None:
        """Start scheduler."""
        if self.running:
            return
        
        self.running = True
        for _ in range(self.max_workers):
            thread = threading.Thread(target=self._worker, daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        logger.info(f"Scheduler started with {self.max_workers} workers")
    
    def stop(self) -> None:
        """Stop scheduler."""
        self.running = False
        for thread in self.worker_threads:
            thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _worker(self) -> None:
        """Worker thread."""
        while self.running:
            try:
                ready_jobs = self.get_ready_jobs()
                if ready_jobs:
                    job = ready_jobs[0]
                    result = self.executor.execute(job)
                    
                    with self.lock:
                        self.results.append(result)
                    
                    # Schedule next run if recurrent
                    self._schedule_next_run(job)
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def _schedule_next_run(self, job: Job) -> None:
        """Schedule next run for recurrent job."""
        if job.recurrence == RecurrenceType.ONCE:
            return
        
        interval_map = {
            RecurrenceType.HOURLY: timedelta(hours=job.recurrence_interval),
            RecurrenceType.DAILY: timedelta(days=job.recurrence_interval),
            RecurrenceType.WEEKLY: timedelta(weeks=job.recurrence_interval),
            RecurrenceType.MONTHLY: timedelta(days=30 * job.recurrence_interval),
        }
        
        if job.recurrence in interval_map:
            job.next_run = datetime.now() + interval_map[job.recurrence]
            job.status = JobStatus.PENDING
    
    def get_results(self) -> List[JobResult]:
        """Get execution results."""
        with self.lock:
            return self.results.copy()
    
    def get_results_for_job(self, job_id: str) -> List[JobResult]:
        """Get results for specific job."""
        with self.lock:
            return [r for r in self.results if r.job_id == job_id]
    
    def clear_results(self) -> None:
        """Clear results."""
        with self.lock:
            self.results.clear()


class JobMonitor:
    """Monitor job execution."""
    
    def __init__(self, scheduler: Scheduler):
        """Initialize monitor."""
        self.scheduler = scheduler
        self.metrics: Dict[str, Any] = {}
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics."""
        jobs = self.scheduler.jobs
        results = self.scheduler.results
        
        metrics = {
            "total_jobs": len(jobs),
            "pending_jobs": len(self.scheduler.get_jobs_by_status(JobStatus.PENDING)),
            "running_jobs": len(self.scheduler.get_jobs_by_status(JobStatus.RUNNING)),
            "completed_jobs": len(self.scheduler.get_jobs_by_status(JobStatus.COMPLETED)),
            "failed_jobs": len(self.scheduler.get_jobs_by_status(JobStatus.FAILED)),
            "total_executions": len(results),
            "success_rate": self._calculate_success_rate(results),
            "average_duration": self._calculate_average_duration(results)
        }
        
        self.metrics = metrics
        return metrics
    
    def _calculate_success_rate(self, results: List[JobResult]) -> float:
        """Calculate success rate."""
        if not results:
            return 0.0
        
        completed = len([r for r in results if r.status == JobStatus.COMPLETED])
        return (completed / len(results)) * 100
    
    def _calculate_average_duration(self, results: List[JobResult]) -> float:
        """Calculate average duration."""
        if not results:
            return 0.0
        
        total_duration = sum(r.duration_seconds for r in results)
        return total_duration / len(results)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics.copy()


class JobRetry:
    """Handle job retries."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """Initialize retry handler."""
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def should_retry(self, result: JobResult, job: Job) -> bool:
        """Check if job should be retried."""
        if result.status == JobStatus.COMPLETED:
            return False
        
        if result.retries >= job.max_retries:
            return False
        
        return True
    
    def get_retry_delay(self, retry_count: int) -> float:
        """Get retry delay in seconds."""
        return (self.backoff_factor ** retry_count)


class JobHistory:
    """Maintain job history."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize history."""
        self.max_history = max_history
        self.history: List[JobResult] = []
    
    def add(self, result: JobResult) -> None:
        """Add result to history."""
        self.history.append(result)
        
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_all(self) -> List[JobResult]:
        """Get all history."""
        return self.history.copy()
    
    def get_by_job_id(self, job_id: str) -> List[JobResult]:
        """Get history for job."""
        return [r for r in self.history if r.job_id == job_id]
    
    def get_by_status(self, status: JobStatus) -> List[JobResult]:
        """Get history by status."""
        return [r for r in self.history if r.status == status]
    
    def clear(self) -> None:
        """Clear history."""
        self.history.clear()


class CronJobScheduler:
    """Schedule jobs using cron-like syntax."""
    
    def __init__(self, scheduler: Scheduler):
        """Initialize cron scheduler."""
        self.scheduler = scheduler
        self.cron_jobs: Dict[str, Job] = {}
    
    def add_cron_job(self, name: str, func: Callable, cron_expression: str) -> str:
        """Add cron job."""
        # Parse cron expression (simplified)
        job_id = self.scheduler.add_job(name, JobType.CUSTOM, func)
        self.cron_jobs[job_id] = self.scheduler.jobs[job_id]
        
        logger.info(f"Added cron job: {name} with expression: {cron_expression}")
        return job_id
    
    def remove_cron_job(self, job_id: str) -> None:
        """Remove cron job."""
        self.scheduler.cancel_job(job_id)
        if job_id in self.cron_jobs:
            del self.cron_jobs[job_id]
