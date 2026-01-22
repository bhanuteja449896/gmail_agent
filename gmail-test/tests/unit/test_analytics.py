"""Tests for analytics module."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.analytics import (
    EmailAnalytics, ReportGenerator, EmailTrendAnalyzer,
    ReportFormatter, PerformanceMonitor, EmailMetrics
)


class TestEmailMetrics:
    """Test suite for EmailMetrics."""
    
    def test_metrics_creation(self):
        """Test metrics creation."""
        metrics = EmailMetrics(
            total_emails=100,
            total_threads=50
        )
        assert metrics.total_emails == 100
        assert metrics.total_threads == 50


class TestEmailAnalytics:
    """Test suite for EmailAnalytics."""
    
    @pytest.fixture
    def analytics(self):
        """Create analytics engine."""
        return EmailAnalytics()
    
    @pytest.fixture
    def sample_emails(self):
        """Create sample emails."""
        return [
            {
                "from": "alice@example.com",
                "to": ["bob@example.com"],
                "body": "Hello World",
                "is_read": True,
                "is_starred": False
            },
            {
                "from": "bob@example.com",
                "to": ["alice@example.com"],
                "body": "Hi there, how are you?",
                "is_read": False,
                "is_starred": True
            },
            {
                "from": "alice@example.com",
                "to": ["bob@example.com"],
                "body": "I'm doing great, thanks for asking!",
                "is_read": True,
                "is_starred": False
            }
        ]
    
    def test_analytics_initialization(self, analytics):
        """Test analytics initialization."""
        assert analytics.max_history == 10000
        assert len(analytics.email_history) == 0
    
    def test_analyze_emails(self, analytics, sample_emails):
        """Test analyzing emails."""
        metrics = analytics.analyze_emails(sample_emails)
        assert metrics.total_emails == 3
        assert metrics.unread_count == 1
        assert metrics.starred_count == 1
    
    def test_get_sender_stats(self, analytics, sample_emails):
        """Test getting sender statistics."""
        analytics.analyze_emails(sample_emails)
        stats = analytics.get_sender_stats(5)
        assert len(stats) > 0
    
    def test_generate_summary_report(self, analytics, sample_emails):
        """Test generating summary report."""
        analytics.analyze_emails(sample_emails)
        report = analytics.generate_summary_report()
        assert "total_emails_analyzed" in report
        assert report["total_emails_analyzed"] == 3


class TestReportGenerator:
    """Test suite for ReportGenerator."""
    
    @pytest.fixture
    def report_gen(self):
        """Create report generator."""
        analytics = EmailAnalytics()
        return ReportGenerator(analytics)
    
    def test_generate_daily_report(self, report_gen):
        """Test generating daily report."""
        from datetime import datetime
        report = report_gen.generate_daily_report(datetime.now())
        assert report["report_type"] == "daily"
    
    def test_generate_weekly_report(self, report_gen):
        """Test generating weekly report."""
        from datetime import datetime
        report = report_gen.generate_weekly_report(datetime.now())
        assert report["report_type"] == "weekly"
    
    def test_generate_sender_report(self, report_gen):
        """Test generating sender report."""
        report = report_gen.generate_sender_report()
        assert report["report_type"] == "sender_analysis"


class TestEmailTrendAnalyzer:
    """Test suite for EmailTrendAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create trend analyzer."""
        return EmailTrendAnalyzer()
    
    def test_analyze_response_patterns(self, analyzer):
        """Test analyzing response patterns."""
        emails = [{"from": "test@example.com"}]
        result = analyzer.analyze_response_patterns(emails)
        assert result["email_count"] == 1
    
    def test_analyze_sender_patterns(self, analyzer):
        """Test analyzing sender patterns."""
        emails = [
            {"from": "alice@example.com"},
            {"from": "bob@example.com"},
            {"from": "alice@example.com"}
        ]
        result = analyzer.analyze_sender_patterns(emails)
        assert result["unique_senders"] == 2
    
    def test_predict_email_volume(self, analyzer):
        """Test predicting email volume."""
        emails = [{"from": "test@example.com"}] * 10
        result = analyzer.predict_email_volume(emails)
        assert "prediction" in result


class TestReportFormatter:
    """Test suite for ReportFormatter."""
    
    def test_format_as_text(self):
        """Test formatting as text."""
        report = {"key1": "value1", "key2": "value2"}
        text = ReportFormatter.format_as_text(report)
        assert "key1" in text
        assert "value1" in text
    
    def test_format_as_json(self):
        """Test formatting as JSON."""
        report = {"key1": "value1"}
        json_data = ReportFormatter.format_as_json(report)
        assert json_data == report
    
    def test_format_as_html(self):
        """Test formatting as HTML."""
        report = {"key1": "value1"}
        html = ReportFormatter.format_as_html(report)
        assert "<html>" in html
        assert "<table>" in html


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor."""
        return PerformanceMonitor()
    
    def test_timer_operations(self, monitor):
        """Test timer operations."""
        monitor.start_timer("operation")
        import time
        time.sleep(0.01)
        elapsed = monitor.end_timer("operation")
        assert elapsed > 0
    
    def test_get_average_time(self, monitor):
        """Test getting average time."""
        import time
        
        for _ in range(3):
            monitor.start_timer("test_op")
            time.sleep(0.001)
            monitor.end_timer("test_op")
        
        avg = monitor.get_average_time("test_op")
        assert avg > 0
    
    def test_get_statistics(self, monitor):
        """Test getting statistics."""
        import time
        
        monitor.start_timer("op1")
        time.sleep(0.001)
        monitor.end_timer("op1")
        
        stats = monitor.get_statistics()
        assert "op1" in stats
        assert "avg" in stats["op1"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
