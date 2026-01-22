"""Tests for monitoring and metrics system."""

import pytest
import time
import statistics
from datetime import datetime
from src.monitoring import (
    MetricType, AlertLevel, Metric, Alert, Counter, Gauge, Histogram,
    Timer, MetricsRegistry, AlertRule, AlertManager, HealthCheck,
    HealthCheckManager, PerformanceMonitor, MonitoringService
)


class TestMetricType:
    """Test MetricType enum."""
    
    def test_metric_types(self):
        """Test metric types."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"


class TestAlertLevel:
    """Test AlertLevel enum."""
    
    def test_alert_levels(self):
        """Test alert levels."""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.CRITICAL.value == "critical"


class TestMetric:
    """Test Metric class."""
    
    def test_creation(self):
        """Test metric creation."""
        metric = Metric(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            value=10.0
        )
        assert metric.name == "test_metric"
        assert metric.value == 10.0
    
    def test_to_dict(self):
        """Test converting to dict."""
        metric = Metric(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            value=10.0
        )
        data = metric.to_dict()
        assert data["name"] == "test_metric"
        assert data["type"] == "counter"


class TestAlert:
    """Test Alert class."""
    
    def test_creation(self):
        """Test alert creation."""
        alert = Alert(
            id="alert_1",
            title="High Load",
            message="CPU usage is high",
            level=AlertLevel.CRITICAL,
            metric="cpu_usage",
            threshold=80.0,
            current_value=85.0
        )
        assert alert.id == "alert_1"
        assert alert.active is True
    
    def test_to_dict(self):
        """Test converting to dict."""
        alert = Alert(
            id="alert_1",
            title="High Load",
            message="CPU usage is high",
            level=AlertLevel.CRITICAL,
            metric="cpu_usage",
            threshold=80.0,
            current_value=85.0
        )
        data = alert.to_dict()
        assert data["id"] == "alert_1"
        assert data["level"] == "critical"


class TestCounter:
    """Test Counter metric."""
    
    def test_increment(self):
        """Test incrementing counter."""
        counter = Counter("requests")
        counter.increment()
        assert counter.get_value() == 1
    
    def test_increment_by_amount(self):
        """Test incrementing by amount."""
        counter = Counter("requests")
        counter.increment(5)
        assert counter.get_value() == 5
    
    def test_reset(self):
        """Test resetting counter."""
        counter = Counter("requests")
        counter.increment(10)
        counter.reset()
        assert counter.get_value() == 0


class TestGauge:
    """Test Gauge metric."""
    
    def test_set_value(self):
        """Test setting gauge value."""
        gauge = Gauge("temperature")
        gauge.set_value(72.5)
        assert gauge.get_value() == 72.5
    
    def test_increment(self):
        """Test incrementing gauge."""
        gauge = Gauge("connections")
        gauge.set_value(10)
        gauge.increment(5)
        assert gauge.get_value() == 15
    
    def test_decrement(self):
        """Test decrementing gauge."""
        gauge = Gauge("connections")
        gauge.set_value(10)
        gauge.decrement(3)
        assert gauge.get_value() == 7


class TestHistogram:
    """Test Histogram metric."""
    
    def test_observe(self):
        """Test recording observations."""
        histogram = Histogram("latency")
        histogram.observe(0.5)
        histogram.observe(1.2)
        histogram.observe(0.8)
        
        assert len(histogram.values) == 3
    
    def test_get_bucket_counts(self):
        """Test getting bucket counts."""
        histogram = Histogram("latency", buckets=[1.0, 5.0, 10.0])
        histogram.observe(0.5)
        histogram.observe(2.0)
        histogram.observe(8.0)
        
        counts = histogram.get_bucket_counts()
        assert counts[1.0] == 1  # Only 0.5 <= 1.0
        assert counts[5.0] == 2  # 0.5 and 2.0 <= 5.0
        assert counts[10.0] == 3  # All <= 10.0
    
    def test_get_statistics(self):
        """Test getting statistics."""
        histogram = Histogram("latency")
        histogram.observe(1.0)
        histogram.observe(2.0)
        histogram.observe(3.0)
        
        stats = histogram.get_statistics()
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["mean"] == 2.0


class TestTimer:
    """Test Timer metric."""
    
    def test_timing(self):
        """Test timing operation."""
        timer = Timer("operation")
        
        timer.start()
        time.sleep(0.01)
        duration = timer.stop()
        
        assert duration > 0.01
        assert len(timer.durations) == 1
    
    def test_get_statistics(self):
        """Test getting timer statistics."""
        timer = Timer("operation")
        
        for _ in range(3):
            timer.start()
            time.sleep(0.01)
            timer.stop()
        
        stats = timer.get_statistics()
        assert stats["count"] == 3
        assert stats["min"] > 0


class TestMetricsRegistry:
    """Test MetricsRegistry."""
    
    def test_create_counter(self):
        """Test creating counter."""
        registry = MetricsRegistry()
        counter = registry.create_counter("requests")
        
        assert counter is not None
        assert registry.get_counter("requests") is counter
    
    def test_create_gauge(self):
        """Test creating gauge."""
        registry = MetricsRegistry()
        gauge = registry.create_gauge("temperature")
        
        assert gauge is not None
        assert registry.get_gauge("temperature") is gauge
    
    def test_create_histogram(self):
        """Test creating histogram."""
        registry = MetricsRegistry()
        histogram = registry.create_histogram("latency")
        
        assert histogram is not None
        assert registry.get_histogram("latency") is histogram
    
    def test_create_timer(self):
        """Test creating timer."""
        registry = MetricsRegistry()
        timer = registry.create_timer("operation")
        
        assert timer is not None
        assert registry.get_timer("operation") is timer
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        registry = MetricsRegistry()
        registry.create_counter("requests")
        registry.create_gauge("connections")
        
        metrics = registry.get_all_metrics()
        assert len(metrics) >= 2


class TestAlertRule:
    """Test AlertRule."""
    
    def test_greater_than_condition(self):
        """Test greater than condition."""
        rule = AlertRule("High Load", "cpu_usage", 80.0, "greater_than")
        
        assert rule.should_trigger(85.0) is True
        assert rule.should_trigger(75.0) is False
    
    def test_less_than_condition(self):
        """Test less than condition."""
        rule = AlertRule("Low Memory", "memory_available", 1000.0, "less_than")
        
        assert rule.should_trigger(500.0) is True
        assert rule.should_trigger(2000.0) is False
    
    def test_equals_condition(self):
        """Test equals condition."""
        rule = AlertRule("Status Check", "status_code", 500.0, "equals")
        
        assert rule.should_trigger(500.0) is True
        assert rule.should_trigger(200.0) is False


class TestAlertManager:
    """Test AlertManager."""
    
    def test_add_rule(self):
        """Test adding rule."""
        manager = AlertManager()
        rule = AlertRule("High Load", "cpu_usage", 80.0, "greater_than")
        
        manager.add_rule(rule)
        assert "High Load" in manager.rules
    
    def test_check_rules(self):
        """Test checking rules."""
        manager = AlertManager()
        registry = MetricsRegistry()
        
        # Create metric
        counter = registry.create_counter("cpu_usage")
        counter.increment(85)
        
        # Add rule
        rule = AlertRule("High Load", "counter:cpu_usage", 80.0, "greater_than")
        manager.add_rule(rule)
        
        # Check rules
        alerts = manager.check_rules(registry)
        assert len(alerts) > 0
    
    def test_resolve_alert(self):
        """Test resolving alert."""
        manager = AlertManager()
        alert = Alert(
            id="alert_1",
            title="Test",
            message="Test",
            level=AlertLevel.WARNING,
            metric="test",
            threshold=1.0,
            current_value=2.0
        )
        
        manager.alerts["alert_1"] = alert
        manager.resolve_alert("alert_1")
        
        assert alert.active is False
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        
        alert1 = Alert(
            id="alert_1",
            title="Test 1",
            message="Test",
            level=AlertLevel.WARNING,
            metric="test",
            threshold=1.0,
            current_value=2.0,
            active=True
        )
        
        alert2 = Alert(
            id="alert_2",
            title="Test 2",
            message="Test",
            level=AlertLevel.INFO,
            metric="test",
            threshold=1.0,
            current_value=2.0,
            active=False
        )
        
        manager.alerts["alert_1"] = alert1
        manager.alerts["alert_2"] = alert2
        
        active = manager.get_active_alerts()
        assert len(active) == 1


class TestHealthCheck:
    """Test HealthCheck."""
    
    def test_successful_check(self):
        """Test successful health check."""
        def check_func():
            return True
        
        check = HealthCheck("service_alive", check_func)
        result = check.run()
        
        assert result is True
        assert check.status is True
    
    def test_failed_check(self):
        """Test failed health check."""
        def check_func():
            return False
        
        check = HealthCheck("service_alive", check_func)
        result = check.run()
        
        assert result is False
        assert check.status is False
    
    def test_error_in_check(self):
        """Test error in health check."""
        def check_func():
            raise Exception("Check failed")
        
        check = HealthCheck("service_alive", check_func)
        result = check.run()
        
        assert result is False
        assert check.error_message is not None


class TestHealthCheckManager:
    """Test HealthCheckManager."""
    
    def test_register(self):
        """Test registering health check."""
        manager = HealthCheckManager()
        manager.register("service", lambda: True)
        
        assert "service" in manager.checks
    
    def test_run_all(self):
        """Test running all checks."""
        manager = HealthCheckManager()
        manager.register("check1", lambda: True)
        manager.register("check2", lambda: True)
        
        results = manager.run_all()
        assert len(results) == 2
        assert all(results.values())
    
    def test_get_status(self):
        """Test getting status."""
        manager = HealthCheckManager()
        manager.register("check1", lambda: True)
        
        status = manager.get_status()
        assert status["healthy"] is True


class TestPerformanceMonitor:
    """Test PerformanceMonitor."""
    
    def test_record_operation(self):
        """Test recording operation."""
        monitor = PerformanceMonitor()
        monitor.record_operation("query", 0.5)
        monitor.record_operation("query", 0.3)
        
        assert "query" in monitor.timers
        assert len(monitor.timers["query"]) == 2
    
    def test_get_statistics(self):
        """Test getting statistics."""
        monitor = PerformanceMonitor()
        monitor.record_operation("query", 1.0)
        monitor.record_operation("query", 2.0)
        monitor.record_operation("query", 3.0)
        
        stats = monitor.get_statistics("query")
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["mean"] == 2.0
    
    def test_get_all_statistics(self):
        """Test getting all statistics."""
        monitor = PerformanceMonitor()
        monitor.record_operation("query", 1.0)
        monitor.record_operation("cache", 0.1)
        
        all_stats = monitor.get_all_statistics()
        assert "query" in all_stats
        assert "cache" in all_stats


class TestMonitoringService:
    """Test MonitoringService."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = MonitoringService()
        assert service.metrics_registry is not None
        assert service.alert_manager is not None
    
    def test_get_dashboard_data(self):
        """Test getting dashboard data."""
        service = MonitoringService()
        
        # Add some data
        counter = service.metrics_registry.create_counter("requests")
        counter.increment(10)
        
        dashboard = service.get_dashboard_data()
        assert "metrics" in dashboard
        assert "alerts" in dashboard
        assert "health" in dashboard
        assert "timestamp" in dashboard


class TestMonitoringIntegration:
    """Integration tests for monitoring."""
    
    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        service = MonitoringService()
        
        # Create metrics
        cpu_gauge = service.metrics_registry.create_gauge("cpu_usage")
        cpu_gauge.set_value(85)
        
        # Add alert rule
        rule = AlertRule(
            "High CPU",
            "gauge:cpu_usage",
            80.0,
            "greater_than",
            AlertLevel.CRITICAL
        )
        service.alert_manager.add_rule(rule)
        
        # Check rules
        alerts = service.alert_manager.check_rules(service.metrics_registry)
        assert len(alerts) > 0
        
        # Register health check
        service.health_check_manager.register("system", lambda: True)
        
        # Get dashboard
        dashboard = service.get_dashboard_data()
        assert dashboard["health"]["healthy"] is True
