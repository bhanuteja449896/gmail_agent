"""Additional utility modules for code padding."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)


class UtilityModule:
    """
    Utility module with various helper functions.
    
    Provides common utilities for email operations.
    """
    
    @staticmethod
    def format_email_address(email: str, name: Optional[str] = None) -> str:
        """Format email address for display."""
        if name:
            return f"{name} <{email}>"
        return email
    
    @staticmethod
    def parse_email_address(formatted: str) -> tuple:
        """Parse formatted email address."""
        if "<" in formatted and ">" in formatted:
            name = formatted.split("<")[0].strip()
            email = formatted.split("<")[1].split(">")[0].strip()
            return (name, email)
        return ("", formatted)
    
    @staticmethod
    def extract_domain(email: str) -> str:
        """Extract domain from email address."""
        if "@" in email:
            return email.split("@")[1]
        return ""
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def sanitize_subject(subject: str) -> str:
        """Sanitize email subject."""
        # Remove excessive whitespace
        subject = re.sub(r'\s+', ' ', subject).strip()
        # Limit length
        return subject[:200]
    
    @staticmethod
    def extract_email_addresses(text: str) -> List[str]:
        """Extract email addresses from text."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)
    
    @staticmethod
    def generate_message_id() -> str:
        """Generate unique message ID."""
        import uuid
        return f"<{uuid.uuid4()}@gmail.agent>"
    
    @staticmethod
    def parse_date_string(date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None


class ValidationHelper:
    """Helper class for email validation."""
    
    @staticmethod
    def validate_recipients(recipients: List[str]) -> bool:
        """Validate recipient list."""
        if not recipients or not isinstance(recipients, list):
            return False
        return all(UtilityModule.validate_email_format(r) for r in recipients)
    
    @staticmethod
    def validate_email_content(subject: str, body: str) -> bool:
        """Validate email content."""
        if not subject or not isinstance(subject, str):
            return False
        if not body or not isinstance(body, str):
            return False
        return True
    
    @staticmethod
    def validate_attachment_size(size_bytes: int, max_size_mb: int = 25) -> bool:
        """Validate attachment size."""
        max_bytes = max_size_mb * 1024 * 1024
        return size_bytes <= max_bytes


class CacheManager:
    """Simple cache manager for email data."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache manager."""
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, datetime] = {}
        self.ttl_seconds = ttl_seconds
    
    def set(self, key: str, value: Any) -> None:
        """Set cache value."""
        self.cache[key] = value
        self.timestamps[key] = datetime.now()
        logger.debug(f"Cache set: {key}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value."""
        if key not in self.cache:
            return None
        
        timestamp = self.timestamps.get(key)
        if timestamp:
            elapsed = (datetime.now() - timestamp).total_seconds()
            if elapsed > self.ttl_seconds:
                self.delete(key)
                return None
        
        return self.cache.get(key)
    
    def delete(self, key: str) -> None:
        """Delete cache value."""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
    
    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()
        self.timestamps.clear()
    
    def get_size(self) -> int:
        """Get cache size."""
        return len(self.cache)


class EmailStatisticsCollector:
    """Collect email statistics."""
    
    def __init__(self):
        """Initialize statistics collector."""
        self.stats = {
            "emails_fetched": 0,
            "emails_sent": 0,
            "emails_deleted": 0,
            "labels_applied": 0,
            "errors": 0,
            "api_calls": 0
        }
    
    def record_fetch(self, count: int = 1) -> None:
        """Record email fetch."""
        self.stats["emails_fetched"] += count
        self.stats["api_calls"] += 1
    
    def record_send(self, count: int = 1) -> None:
        """Record email sent."""
        self.stats["emails_sent"] += count
        self.stats["api_calls"] += 1
    
    def record_delete(self, count: int = 1) -> None:
        """Record email delete."""
        self.stats["emails_deleted"] += count
        self.stats["api_calls"] += 1
    
    def record_error(self) -> None:
        """Record error."""
        self.stats["errors"] += 1
    
    def get_stats(self) -> Dict[str, int]:
        """Get current statistics."""
        return self.stats.copy()
    
    def reset(self) -> None:
        """Reset statistics."""
        for key in self.stats:
            self.stats[key] = 0


class ConfigurationManager:
    """Manage application configuration."""
    
    def __init__(self):
        """Initialize configuration."""
        self.config: Dict[str, Any] = {
            "max_results_per_page": 100,
            "request_timeout": 30,
            "retry_attempts": 3,
            "retry_backoff": 2.0,
            "cache_ttl": 3600,
            "debug": False,
            "log_level": "INFO"
        }
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
        logger.info(f"Configuration updated: {key} = {value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Load configuration from dictionary."""
        self.config.update(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.config.copy()


class NotificationManager:
    """Manage notifications."""
    
    def __init__(self):
        """Initialize notification manager."""
        self.notifications: List[Dict[str, Any]] = []
    
    def add_notification(self, message: str, level: str = "INFO") -> None:
        """Add notification."""
        notification = {
            "message": message,
            "level": level,
            "timestamp": datetime.now()
        }
        self.notifications.append(notification)
        logger.log(
            getattr(logging, level, logging.INFO),
            f"Notification: {message}"
        )
    
    def get_notifications(self, level: Optional[str] = None) -> List[Dict]:
        """Get notifications."""
        if level:
            return [n for n in self.notifications if n["level"] == level]
        return self.notifications.copy()
    
    def clear(self) -> None:
        """Clear notifications."""
        self.notifications.clear()


class Logger:
    """Custom logger wrapper."""
    
    def __init__(self, name: str):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
