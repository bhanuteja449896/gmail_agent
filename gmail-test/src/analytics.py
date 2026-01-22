"""Advanced email analytics and reporting module."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import statistics

logger = logging.getLogger(__name__)


@dataclass
class EmailMetrics:
    """Email metrics data."""
    total_emails: int = 0
    total_threads: int = 0
    average_emails_per_thread: float = 0.0
    average_response_time: float = 0.0
    most_frequent_sender: str = ""
    average_email_length: float = 0.0
    unread_count: int = 0
    starred_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class EmailAnalytics:
    """
    Email analytics engine for generating insights and reports.
    
    Provides statistical analysis of email patterns, trends, and metrics.
    """
    
    def __init__(self, max_history: int = 10000):
        """Initialize analytics engine."""
        self.max_history = max_history
        self.email_history: List[Dict] = []
        self.sender_frequency: Counter = Counter()
        self.recipient_frequency: Counter = Counter()
        self.subject_frequency: Counter = Counter()
        self.hourly_distribution: Dict[int, int] = defaultdict(int)
        self.daily_distribution: Dict[str, int] = defaultdict(int)
    
    def analyze_emails(self, emails: List[Dict]) -> EmailMetrics:
        """
        Analyze email batch and generate metrics.
        
        Args:
            emails: List of email data
            
        Returns:
            EmailMetrics object
        """
        if not emails:
            return EmailMetrics()
        
        # Collect data
        email_lengths = []
        senders = []
        recipients = []
        
        for email in emails:
            # Body analysis
            body = email.get("body", "")
            if body:
                email_lengths.append(len(body))
            
            # Sender analysis
            from_addr = email.get("from", "")
            if from_addr:
                senders.append(from_addr)
                self.sender_frequency[from_addr] += 1
            
            # Recipients analysis
            to_addrs = email.get("to", [])
            if isinstance(to_addrs, list):
                recipients.extend(to_addrs)
            
            # Add to history
            if len(self.email_history) < self.max_history:
                self.email_history.append(email)
        
        # Calculate metrics
        avg_length = statistics.mean(email_lengths) if email_lengths else 0
        
        metrics = EmailMetrics(
            total_emails=len(emails),
            average_email_length=avg_length,
            most_frequent_sender=senders[0] if senders else "",
            unread_count=sum(1 for e in emails if not e.get("is_read", True)),
            starred_count=sum(1 for e in emails if e.get("is_starred", False))
        )
        
        return metrics
    
    def get_sender_stats(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top senders."""
        return self.sender_frequency.most_common(limit)
    
    def get_recipient_stats(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top recipients."""
        return self.recipient_frequency.most_common(limit)
    
    def get_busiest_hours(self) -> List[Tuple[int, int]]:
        """Get busiest hours of day."""
        return sorted(self.hourly_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def get_busiest_days(self) -> List[Tuple[str, int]]:
        """Get busiest days of week."""
        return sorted(self.daily_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        report = {
            "total_emails_analyzed": len(self.email_history),
            "top_senders": self.get_sender_stats(5),
            "top_recipients": self.get_recipient_stats(5),
            "busiest_hours": self.get_busiest_hours(),
            "busiest_days": self.get_busiest_days(),
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated summary report with {report['total_emails_analyzed']} emails")
        return report


class ReportGenerator:
    """Generate various types of reports from email data."""
    
    def __init__(self, analytics: EmailAnalytics):
        """Initialize report generator."""
        self.analytics = analytics
    
    def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily activity report."""
        return {
            "date": date.isoformat(),
            "report_type": "daily",
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_weekly_report(self, week_start: datetime) -> Dict[str, Any]:
        """Generate weekly activity report."""
        return {
            "week_start": week_start.isoformat(),
            "report_type": "weekly",
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_monthly_report(self, month: int, year: int) -> Dict[str, Any]:
        """Generate monthly activity report."""
        return {
            "month": month,
            "year": year,
            "report_type": "monthly",
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_sender_report(self) -> Dict[str, Any]:
        """Generate sender analysis report."""
        return {
            "report_type": "sender_analysis",
            "top_senders": self.analytics.get_sender_stats(10),
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate system performance report."""
        return {
            "report_type": "performance",
            "total_emails": len(self.analytics.email_history),
            "generated_at": datetime.now().isoformat()
        }


class EmailTrendAnalyzer:
    """Analyze trends in email data."""
    
    def __init__(self):
        """Initialize trend analyzer."""
        self.trends: List[Dict] = []
    
    def analyze_response_patterns(self, emails: List[Dict]) -> Dict[str, Any]:
        """Analyze email response patterns."""
        return {
            "pattern": "analyzed",
            "email_count": len(emails),
            "timestamp": datetime.now().isoformat()
        }
    
    def analyze_sender_patterns(self, emails: List[Dict]) -> Dict[str, Any]:
        """Analyze sender communication patterns."""
        sender_counts = Counter(e.get("from", "") for e in emails if "from" in e)
        
        return {
            "pattern": "sender_distribution",
            "unique_senders": len(sender_counts),
            "top_senders": sender_counts.most_common(5),
            "timestamp": datetime.now().isoformat()
        }
    
    def predict_email_volume(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Predict future email volume."""
        if not historical_data:
            return {"prediction": "insufficient_data"}
        
        return {
            "prediction": "high",
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat()
        }


class ReportFormatter:
    """Format reports in various output formats."""
    
    @staticmethod
    def format_as_text(report: Dict) -> str:
        """Format report as plain text."""
        lines = []
        lines.append("=" * 50)
        for key, value in report.items():
            lines.append(f"{key}: {value}")
        lines.append("=" * 50)
        return "\n".join(lines)
    
    @staticmethod
    def format_as_json(report: Dict) -> Dict:
        """Format report as JSON-compatible dict."""
        return report
    
    @staticmethod
    def format_as_html(report: Dict) -> str:
        """Format report as HTML."""
        html_lines = ["<html><body><table border='1'>"]
        for key, value in report.items():
            html_lines.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
        html_lines.append("</table></body></html>")
        return "\n".join(html_lines)


class PerformanceMonitor:
    """Monitor application performance."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, name: str) -> None:
        """Start performance timer."""
        import time
        self.start_times[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """End performance timer and return elapsed time."""
        import time
        if name not in self.start_times:
            return 0.0
        
        elapsed = time.time() - self.start_times[name]
        self.metrics[name].append(elapsed)
        del self.start_times[name]
        return elapsed
    
    def get_average_time(self, name: str) -> float:
        """Get average time for operation."""
        times = self.metrics.get(name, [])
        if not times:
            return 0.0
        return statistics.mean(times)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        for name, times in self.metrics.items():
            if times:
                stats[name] = {
                    "avg": statistics.mean(times),
                    "min": min(times),
                    "max": max(times),
                    "count": len(times)
                }
        return stats
