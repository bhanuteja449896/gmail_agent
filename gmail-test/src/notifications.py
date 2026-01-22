"""Notification service for email agents."""

import logging
import json
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import queue

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class NotificationType(Enum):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    LOG = "log"
    DATABASE = "database"
    PUSH = "push"
    CHAT = "chat"


class NotificationChannel(Enum):
    """Notification channels."""
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"


@dataclass
class Notification:
    """Notification data class."""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    recipient: str
    channel: Optional[NotificationChannel] = None
    data: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed: bool = False
    error: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        """Post initialization."""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "recipient": self.recipient,
            "channel": self.channel.value if self.channel else None,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "failed": self.failed,
            "error": self.error,
            "retry_count": self.retry_count
        }


class NotificationHandler(ABC):
    """Abstract notification handler."""
    
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """Send notification."""
        pass
    
    @abstractmethod
    def supports_channel(self, channel: NotificationChannel) -> bool:
        """Check if handler supports channel."""
        pass


class EmailNotificationHandler(NotificationHandler):
    """Email notification handler."""
    
    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 587):
        """Initialize email handler."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
    
    def send(self, notification: Notification) -> bool:
        """Send email notification."""
        try:
            # Simulate email sending
            logger.info(f"Sending email to {notification.recipient}: {notification.title}")
            notification.sent_at = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            notification.failed = True
            notification.error = str(e)
            return False
    
    def supports_channel(self, channel: NotificationChannel) -> bool:
        """Check if supports channel."""
        return channel in [NotificationChannel.SENDGRID, NotificationChannel.MAILGUN]


class SMSNotificationHandler(NotificationHandler):
    """SMS notification handler."""
    
    def __init__(self, api_key: str = ""):
        """Initialize SMS handler."""
        self.api_key = api_key
    
    def send(self, notification: Notification) -> bool:
        """Send SMS notification."""
        try:
            logger.info(f"Sending SMS to {notification.recipient}: {notification.message}")
            notification.sent_at = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            notification.failed = True
            notification.error = str(e)
            return False
    
    def supports_channel(self, channel: NotificationChannel) -> bool:
        """Check if supports channel."""
        return channel == NotificationChannel.TWILIO


class WebhookNotificationHandler(NotificationHandler):
    """Webhook notification handler."""
    
    def __init__(self, base_url: str = "http://localhost"):
        """Initialize webhook handler."""
        self.base_url = base_url
    
    def send(self, notification: Notification) -> bool:
        """Send webhook notification."""
        try:
            logger.info(f"Sending webhook to {notification.recipient}")
            notification.sent_at = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            notification.failed = True
            notification.error = str(e)
            return False
    
    def supports_channel(self, channel: NotificationChannel) -> bool:
        """Check if supports channel."""
        return True


class LogNotificationHandler(NotificationHandler):
    """Log notification handler."""
    
    def __init__(self, logger_instance: logging.Logger = None):
        """Initialize log handler."""
        self.logger = logger_instance or logger
    
    def send(self, notification: Notification) -> bool:
        """Send log notification."""
        try:
            level_map = {
                NotificationPriority.LOW: logging.DEBUG,
                NotificationPriority.MEDIUM: logging.INFO,
                NotificationPriority.HIGH: logging.WARNING,
                NotificationPriority.CRITICAL: logging.CRITICAL,
            }
            log_level = level_map.get(notification.priority, logging.INFO)
            self.logger.log(log_level, f"{notification.title}: {notification.message}")
            notification.sent_at = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
            return False
    
    def supports_channel(self, channel: NotificationChannel) -> bool:
        """Check if supports channel."""
        return True


class NotificationService:
    """Main notification service."""
    
    def __init__(self, max_retries: int = 3):
        """Initialize notification service."""
        self.handlers: Dict[NotificationType, NotificationHandler] = {}
        self.notification_queue: queue.Queue = queue.Queue()
        self.sent_notifications: List[Notification] = []
        self.failed_notifications: List[Notification] = []
        self.max_retries = max_retries
        self.running = False
        self.worker_thread = None
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default handlers."""
        self.handlers[NotificationType.EMAIL] = EmailNotificationHandler()
        self.handlers[NotificationType.SMS] = SMSNotificationHandler()
        self.handlers[NotificationType.WEBHOOK] = WebhookNotificationHandler()
        self.handlers[NotificationType.LOG] = LogNotificationHandler()
    
    def register_handler(self, notification_type: NotificationType, handler: NotificationHandler) -> None:
        """Register notification handler."""
        self.handlers[notification_type] = handler
        logger.info(f"Registered handler for {notification_type.value}")
    
    def send(self, notification: Notification) -> bool:
        """Send notification."""
        handler = self.handlers.get(notification.type)
        
        if not handler:
            logger.warning(f"No handler for notification type: {notification.type}")
            notification.failed = True
            notification.error = "No handler available"
            self.failed_notifications.append(notification)
            return False
        
        try:
            result = handler.send(notification)
            if result:
                self.sent_notifications.append(notification)
                logger.info(f"Notification sent: {notification.id}")
            else:
                self.failed_notifications.append(notification)
            return result
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            notification.failed = True
            notification.error = str(e)
            self.failed_notifications.append(notification)
            return False
    
    def queue_notification(self, notification: Notification) -> None:
        """Queue notification for async sending."""
        self.notification_queue.put(notification)
    
    def start_worker(self) -> None:
        """Start worker thread for async notifications."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Notification worker started")
    
    def stop_worker(self) -> None:
        """Stop worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Notification worker stopped")
    
    def _worker(self) -> None:
        """Worker thread for processing notifications."""
        while self.running:
            try:
                notification = self.notification_queue.get(timeout=1)
                self.send(notification)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def get_sent_notifications(self) -> List[Notification]:
        """Get sent notifications."""
        return self.sent_notifications.copy()
    
    def get_failed_notifications(self) -> List[Notification]:
        """Get failed notifications."""
        return self.failed_notifications.copy()
    
    def retry_failed_notifications(self) -> None:
        """Retry failed notifications."""
        failed = self.failed_notifications.copy()
        self.failed_notifications.clear()
        
        for notification in failed:
            if notification.retry_count < self.max_retries:
                notification.retry_count += 1
                self.send(notification)
    
    def clear_history(self) -> None:
        """Clear notification history."""
        self.sent_notifications.clear()
        self.failed_notifications.clear()


class NotificationFilter:
    """Filter notifications based on criteria."""
    
    def __init__(self):
        """Initialize filter."""
        self.priority_threshold = NotificationPriority.LOW
        self.include_types: List[NotificationType] = []
        self.exclude_types: List[NotificationType] = []
    
    def should_send(self, notification: Notification) -> bool:
        """Check if notification should be sent."""
        # Check priority
        if notification.priority.value < self.priority_threshold.value:
            return False
        
        # Check include types
        if self.include_types and notification.type not in self.include_types:
            return False
        
        # Check exclude types
        if notification.type in self.exclude_types:
            return False
        
        return True
    
    def set_priority_threshold(self, priority: NotificationPriority) -> None:
        """Set priority threshold."""
        self.priority_threshold = priority
    
    def add_include_type(self, notification_type: NotificationType) -> None:
        """Add include type."""
        if notification_type not in self.include_types:
            self.include_types.append(notification_type)
    
    def add_exclude_type(self, notification_type: NotificationType) -> None:
        """Add exclude type."""
        if notification_type not in self.exclude_types:
            self.exclude_types.append(notification_type)


class NotificationTemplate:
    """Notification template."""
    
    def __init__(self, name: str, title: str, message: str):
        """Initialize template."""
        self.name = name
        self.title = title
        self.message = message
    
    def render(self, context: Dict[str, Any]) -> tuple:
        """Render template with context."""
        title = self.title.format(**context)
        message = self.message.format(**context)
        return title, message


class NotificationTemplateRegistry:
    """Registry for notification templates."""
    
    def __init__(self):
        """Initialize registry."""
        self.templates: Dict[str, NotificationTemplate] = {}
        self._register_default_templates()
    
    def _register_default_templates(self) -> None:
        """Register default templates."""
        self.templates["welcome"] = NotificationTemplate(
            "welcome",
            "Welcome to Gmail Agent",
            "Welcome {username}! You have {email_count} emails."
        )
        self.templates["error"] = NotificationTemplate(
            "error",
            "Error: {error_type}",
            "An error occurred: {error_message}"
        )
        self.templates["success"] = NotificationTemplate(
            "success",
            "Operation Successful",
            "{operation} completed successfully"
        )
    
    def register(self, template: NotificationTemplate) -> None:
        """Register template."""
        self.templates[template.name] = template
    
    def get(self, name: str) -> Optional[NotificationTemplate]:
        """Get template."""
        return self.templates.get(name)
    
    def render(self, name: str, context: Dict[str, Any]) -> Optional[tuple]:
        """Render template."""
        template = self.get(name)
        if template:
            return template.render(context)
        return None


class NotificationBatch:
    """Batch process notifications."""
    
    def __init__(self, batch_size: int = 10):
        """Initialize batch."""
        self.batch_size = batch_size
        self.notifications: List[Notification] = []
    
    def add(self, notification: Notification) -> None:
        """Add notification to batch."""
        self.notifications.append(notification)
    
    def is_full(self) -> bool:
        """Check if batch is full."""
        return len(self.notifications) >= self.batch_size
    
    def get_batch(self) -> List[Notification]:
        """Get batch."""
        batch = self.notifications[:self.batch_size]
        self.notifications = self.notifications[self.batch_size:]
        return batch
    
    def clear(self) -> None:
        """Clear batch."""
        self.notifications.clear()


class NotificationScheduler:
    """Schedule notifications for later."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduled: List[tuple] = []  # (datetime, notification)
    
    def schedule(self, notification: Notification, send_at: datetime) -> None:
        """Schedule notification."""
        self.scheduled.append((send_at, notification))
    
    def get_ready_notifications(self, now: datetime = None) -> List[Notification]:
        """Get ready notifications."""
        if now is None:
            now = datetime.now()
        
        ready = []
        remaining = []
        
        for send_at, notification in self.scheduled:
            if send_at <= now:
                ready.append(notification)
            else:
                remaining.append((send_at, notification))
        
        self.scheduled = remaining
        return ready
    
    def clear(self) -> None:
        """Clear scheduled notifications."""
        self.scheduled.clear()
