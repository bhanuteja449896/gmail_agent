"""Monitoring, metrics, and observability system."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SUMMARY = "summary"


class AlertLevel(Enum):
    """Alert levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Metric data."""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels
        }


@dataclass
class Alert:
    """Alert."""
    id: str
    title: str
    message: str
    level: AlertLevel
    metric: str
    threshold: float
    current_value: float
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "metric": self.metric,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "active": self.active
        }


class Counter:
    """Counter metric."""
    
    def __init__(self, name: str, labels: Dict[str, str] = None):
        """Initialize counter."""
        self.name = name
        self.labels = labels or {}
        self.value = 0
        self.created_at = datetime.now()
    
    def increment(self, amount: float = 1) -> None:
        """Increment counter."""
        self.value += amount
    
    def get_value(self) -> float:
        """Get counter value."""
        return self.value
    
    def reset(self) -> None:
        """Reset counter."""
        self.value = 0


class Gauge:
    """Gauge metric."""
    
    def __init__(self, name: str, labels: Dict[str, str] = None):
        """Initialize gauge."""
        self.name = name
        self.labels = labels or {}
        self.value = 0
        self.created_at = datetime.now()
    
    def set_value(self, value: float) -> None:
        """Set gauge value."""
        self.value = value
    
    def increment(self, amount: float = 1) -> None:
        """Increment gauge."""
        self.value += amount
    
    def decrement(self, amount: float = 1) -> None:
        """Decrement gauge."""
        self.value -= amount
    
    def get_value(self) -> float:
        """Get gauge value."""
        return self.value


class Histogram:
    """Histogram metric."""
    
    def __init__(self, name: str, buckets: List[float] = None):
        """Initialize histogram."""
        self.name = name
        self.buckets = buckets or [0.1, 0.5, 1.0, 5.0, 10.0]
        self.values: List[float] = []
    
    def observe(self, value: float) -> None:
        """Record observation."""
        self.values.append(value)
    
    def get_bucket_counts(self) -> Dict[float, int]:
        """Get bucket counts."""
        counts = {}
        for bucket in self.buckets:
            counts[bucket] = len([v for v in self.values if v <= bucket])
        return counts
    
    def get_statistics(self) -> Dict[str, float]:
        """Get statistics."""
        if not self.values:
            return {}
        
        return {
            "min": min(self.values),
            "max": max(self.values),
            "mean": statistics.mean(self.values),
            "median": statistics.median(self.values),
            "stdev": statistics.stdev(self.values) if len(self.values) > 1 else 0,
            "sum": sum(self.values),
            "count": len(self.values)
        }


class Timer:
    """Timer metric."""
    
    def __init__(self, name: str):
        """Initialize timer."""
        self.name = name
        self.start_time = None
        self.durations: List[float] = []
    
    def start(self) -> None:
        """Start timer."""
        self.start_time = time.time()
    
    def stop(self) -> float:
        """Stop timer and record duration."""
        if self.start_time is None:
            return 0
        
        duration = time.time() - self.start_time
        self.durations.append(duration)
        self.start_time = None
        return duration
    
    def get_statistics(self) -> Dict[str, float]:
        """Get timer statistics."""
        if not self.durations:
            return {}
        
        return {
            "min": min(self.durations),
            "max": max(self.durations),
            "mean": statistics.mean(self.durations),
            "count": len(self.durations),
            "total": sum(self.durations)
        }


class MetricsRegistry:
    """Registry for metrics."""
    
    def __init__(self):
        """Initialize registry."""
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.timers: Dict[str, Timer] = {}
    
    def create_counter(self, name: str, labels: Dict[str, str] = None) -> Counter:
        """Create counter."""
        counter = Counter(name, labels)
        self.counters[name] = counter
        logger.debug(f"Created counter: {name}")
        return counter
    
    def create_gauge(self, name: str, labels: Dict[str, str] = None) -> Gauge:
        """Create gauge."""
        gauge = Gauge(name, labels)
        self.gauges[name] = gauge
        logger.debug(f"Created gauge: {name}")
        return gauge
    
    def create_histogram(self, name: str, buckets: List[float] = None) -> Histogram:
        """Create histogram."""
        histogram = Histogram(name, buckets)
        self.histograms[name] = histogram
        logger.debug(f"Created histogram: {name}")
        return histogram
    
    def create_timer(self, name: str) -> Timer:
        """Create timer."""
        timer = Timer(name)
        self.timers[name] = timer
        logger.debug(f"Created timer: {name}")
        return timer
    
    def get_counter(self, name: str) -> Optional[Counter]:
        """Get counter."""
        return self.counters.get(name)
    
    def get_gauge(self, name: str) -> Optional[Gauge]:
        """Get gauge."""
        return self.gauges.get(name)
    
    def get_histogram(self, name: str) -> Optional[Histogram]:
        """Get histogram."""
        return self.histograms.get(name)
    
    def get_timer(self, name: str) -> Optional[Timer]:
        """Get timer."""
        return self.timers.get(name)
    
    def get_all_metrics(self) -> List[Metric]:
        """Get all metrics."""
        metrics = []
        
        for counter in self.counters.values():
            metrics.append(Metric(
                name=counter.name,
                metric_type=MetricType.COUNTER,
                value=counter.value,
                labels=counter.labels
            ))
        
        for gauge in self.gauges.values():
            metrics.append(Metric(
                name=gauge.name,
                metric_type=MetricType.GAUGE,
                value=gauge.value,
                labels=gauge.labels
            ))
        
        return metrics


class AlertRule:
    """Alert rule."""
    
    def __init__(self, name: str, metric: str, threshold: float,
                 condition: str, level: AlertLevel = AlertLevel.WARNING):
        """Initialize rule."""
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.condition = condition  # "greater_than", "less_than", "equals"
        self.level = level
        self.active = True
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if rule should trigger."""
        if not self.active:
            return False
        
        if self.condition == "greater_than":
            return current_value > self.threshold
        elif self.condition == "less_than":
            return current_value < self.threshold
        elif self.condition == "equals":
            return current_value == self.threshold
        
        return False


class AlertManager:
    """Manage alerts."""
    
    def __init__(self):
        """Initialize manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add alert rule."""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def check_rules(self, metrics_registry: MetricsRegistry) -> List[Alert]:
        """Check all rules against metrics."""
        triggered_alerts = []
        
        for rule in self.rules.values():
            metric = None
            
            # Find metric in registry
            if rule.metric.startswith("counter:"):
                counter = metrics_registry.get_counter(rule.metric.replace("counter:", ""))
                if counter:
                    metric = counter.get_value()
            elif rule.metric.startswith("gauge:"):
                gauge = metrics_registry.get_gauge(rule.metric.replace("gauge:", ""))
                if gauge:
                    metric = gauge.get_value()
            
            if metric is not None and rule.should_trigger(metric):
                alert = Alert(
                    id=f"alert_{int(time.time())}",
                    title=rule.name,
                    message=f"Alert triggered: {rule.name}",
                    level=rule.level,
                    metric=rule.metric,
                    threshold=rule.threshold,
                    current_value=metric
                )
                
                self.alerts[alert.id] = alert
                self.alert_history.append(alert)
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def resolve_alert(self, alert_id: str) -> None:
        """Resolve alert."""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.active = False
            alert.resolved_at = datetime.now()
            logger.info(f"Resolved alert: {alert_id}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return [a for a in self.alerts.values() if a.active]


class HealthCheck:
    """Health check."""
    
    def __init__(self, name: str, check_func: callable):
        """Initialize health check."""
        self.name = name
        self.check_func = check_func
        self.last_check: Optional[datetime] = None
        self.status: bool = True
        self.error_message: Optional[str] = None
    
    def run(self) -> bool:
        """Run health check."""
        try:
            result = self.check_func()
            self.status = result
            self.last_check = datetime.now()
            if not result:
                self.error_message = "Health check failed"
            return result
        except Exception as e:
            self.status = False
            self.error_message = str(e)
            self.last_check = datetime.now()
            logger.error(f"Health check error: {e}")
            return False


class HealthCheckManager:
    """Manage health checks."""
    
    def __init__(self):
        """Initialize manager."""
        self.checks: Dict[str, HealthCheck] = {}
    
    def register(self, name: str, check_func: callable) -> None:
        """Register health check."""
        check = HealthCheck(name, check_func)
        self.checks[name] = check
        logger.info(f"Registered health check: {name}")
    
    def run_all(self) -> Dict[str, bool]:
        """Run all health checks."""
        results = {}
        for name, check in self.checks.items():
            results[name] = check.run()
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        results = self.run_all()
        overall_healthy = all(results.values())
        
        return {
            "healthy": overall_healthy,
            "checks": results,
            "timestamp": datetime.now().isoformat()
        }


class PerformanceMonitor:
    """Monitor performance."""
    
    def __init__(self):
        """Initialize monitor."""
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.samples: int = 100
    
    def record_operation(self, operation: str, duration: float) -> None:
        """Record operation duration."""
        self.timers[operation].append(duration)
        
        # Keep only recent samples
        if len(self.timers[operation]) > self.samples:
            self.timers[operation] = self.timers[operation][-self.samples:]
    
    def get_statistics(self, operation: str) -> Dict[str, float]:
        """Get operation statistics."""
        durations = self.timers.get(operation, [])
        if not durations:
            return {}
        
        return {
            "min": min(durations),
            "max": max(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "count": len(durations),
            "total": sum(durations)
        }
    
    def get_all_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations."""
        stats = {}
        for operation in self.timers.keys():
            stats[operation] = self.get_statistics(operation)
        return stats


class MonitoringService:
    """Main monitoring service."""
    
    def __init__(self):
        """Initialize service."""
        self.metrics_registry = MetricsRegistry()
        self.alert_manager = AlertManager()
        self.health_check_manager = HealthCheckManager()
        self.performance_monitor = PerformanceMonitor()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data."""
        return {
            "metrics": [m.to_dict() for m in self.metrics_registry.get_all_metrics()],
            "alerts": [a.to_dict() for a in self.alert_manager.get_active_alerts()],
            "health": self.health_check_manager.get_status(),
            "performance": self.performance_monitor.get_all_statistics(),
            "timestamp": datetime.now().isoformat()
        }
