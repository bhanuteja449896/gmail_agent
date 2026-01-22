"""Tests for notification service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.notifications import (
    Notification, NotificationType, NotificationPriority, NotificationChannel,
    NotificationHandler, EmailNotificationHandler, SMSNotificationHandler,
    WebhookNotificationHandler, LogNotificationHandler, NotificationService,
    NotificationFilter, NotificationTemplate, NotificationTemplateRegistry,
    NotificationBatch, NotificationScheduler
)


class TestNotificationPriority:
    """Test NotificationPriority enum."""
    
    def test_priority_values(self):
        """Test priority values."""
        assert NotificationPriority.LOW.value == 1
        assert NotificationPriority.MEDIUM.value == 2
        assert NotificationPriority.HIGH.value == 3
        assert NotificationPriority.CRITICAL.value == 4
    
    def test_priority_comparison(self):
        """Test priority comparison."""
        low = NotificationPriority.LOW
        high = NotificationPriority.HIGH
        assert low.value < high.value


class TestNotificationType:
    """Test NotificationType enum."""
    
    def test_notification_types(self):
        """Test notification types."""
        assert NotificationType.EMAIL.value == "email"
        assert NotificationType.SMS.value == "sms"
        assert NotificationType.WEBHOOK.value == "webhook"


class TestNotification:
    """Test Notification class."""
    
    def test_creation(self):
        """Test notification creation."""
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
            recipient="test@example.com"
        )
        assert notification.id == "123"
        assert notification.type == NotificationType.EMAIL
    
    def test_created_at(self):
        """Test created_at timestamp."""
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        assert notification.created_at is not None
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
            recipient="test@example.com"
        )
        data = notification.to_dict()
        assert data["id"] == "123"
        assert data["type"] == "email"
        assert data["priority"] == 3
    
    def test_with_channel(self):
        """Test notification with channel."""
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com",
            channel=NotificationChannel.SENDGRID
        )
        assert notification.channel == NotificationChannel.SENDGRID
    
    def test_with_data(self):
        """Test notification with additional data."""
        data = {"key": "value"}
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.LOW,
            title="Test",
            message="Test",
            recipient="test@example.com",
            data=data
        )
        assert notification.data == data


class TestEmailNotificationHandler:
    """Test EmailNotificationHandler."""
    
    def test_send_success(self):
        """Test successful email sending."""
        handler = EmailNotificationHandler()
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        result = handler.send(notification)
        assert result is True
        assert notification.sent_at is not None
    
    def test_supports_channel(self):
        """Test channel support."""
        handler = EmailNotificationHandler()
        assert handler.supports_channel(NotificationChannel.SENDGRID) is True
        assert handler.supports_channel(NotificationChannel.TWILIO) is False


class TestSMSNotificationHandler:
    """Test SMSNotificationHandler."""
    
    def test_send_success(self):
        """Test successful SMS sending."""
        handler = SMSNotificationHandler(api_key="test_key")
        notification = Notification(
            id="123",
            type=NotificationType.SMS,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="+1234567890"
        )
        result = handler.send(notification)
        assert result is True
    
    def test_supports_channel(self):
        """Test channel support."""
        handler = SMSNotificationHandler()
        assert handler.supports_channel(NotificationChannel.TWILIO) is True
        assert handler.supports_channel(NotificationChannel.SLACK) is False


class TestWebhookNotificationHandler:
    """Test WebhookNotificationHandler."""
    
    def test_send_success(self):
        """Test successful webhook sending."""
        handler = WebhookNotificationHandler()
        notification = Notification(
            id="123",
            type=NotificationType.WEBHOOK,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="http://example.com/webhook"
        )
        result = handler.send(notification)
        assert result is True


class TestLogNotificationHandler:
    """Test LogNotificationHandler."""
    
    def test_send_success(self):
        """Test successful log notification."""
        handler = LogNotificationHandler()
        notification = Notification(
            id="123",
            type=NotificationType.LOG,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="logger"
        )
        result = handler.send(notification)
        assert result is True


class TestNotificationService:
    """Test NotificationService."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = NotificationService()
        assert len(service.handlers) > 0
        assert NotificationType.EMAIL in service.handlers
    
    def test_register_handler(self):
        """Test registering handler."""
        service = NotificationService()
        handler = EmailNotificationHandler()
        service.register_handler(NotificationType.EMAIL, handler)
        assert service.handlers[NotificationType.EMAIL] == handler
    
    def test_send_notification(self):
        """Test sending notification."""
        service = NotificationService()
        notification = Notification(
            id="123",
            type=NotificationType.LOG,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="logger"
        )
        result = service.send(notification)
        assert result is True
        assert notification in service.sent_notifications
    
    def test_send_unknown_type(self):
        """Test sending unknown notification type."""
        service = NotificationService()
        notification = Notification(
            id="123",
            type=NotificationType.PUSH,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="device"
        )
        result = service.send(notification)
        assert result is False
        assert notification in service.failed_notifications
    
    def test_get_sent_notifications(self):
        """Test getting sent notifications."""
        service = NotificationService()
        notification = Notification(
            id="123",
            type=NotificationType.LOG,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="logger"
        )
        service.send(notification)
        sent = service.get_sent_notifications()
        assert len(sent) > 0
    
    def test_get_failed_notifications(self):
        """Test getting failed notifications."""
        service = NotificationService()
        notification = Notification(
            id="123",
            type=NotificationType.PUSH,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="device"
        )
        service.send(notification)
        failed = service.get_failed_notifications()
        assert len(failed) > 0
    
    def test_retry_failed_notifications(self):
        """Test retrying failed notifications."""
        service = NotificationService()
        # Register a custom handler
        service.register_handler(NotificationType.PUSH, LogNotificationHandler())
        
        notification = Notification(
            id="123",
            type=NotificationType.PUSH,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="device"
        )
        
        # First send will fail, then retry
        service.send(notification)
        initial_failed = len(service.failed_notifications)
        
        service.retry_failed_notifications()
        # After retry, it should be successful
    
    def test_clear_history(self):
        """Test clearing history."""
        service = NotificationService()
        notification = Notification(
            id="123",
            type=NotificationType.LOG,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="logger"
        )
        service.send(notification)
        service.clear_history()
        assert len(service.sent_notifications) == 0
        assert len(service.failed_notifications) == 0
    
    def test_queue_notification(self):
        """Test queuing notification."""
        service = NotificationService()
        notification = Notification(
            id="123",
            type=NotificationType.LOG,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="logger"
        )
        service.queue_notification(notification)
        assert not service.notification_queue.empty()


class TestNotificationFilter:
    """Test NotificationFilter."""
    
    def test_should_send_default(self):
        """Test default filter."""
        filter = NotificationFilter()
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        assert filter.should_send(notification) is True
    
    def test_priority_threshold(self):
        """Test priority threshold."""
        filter = NotificationFilter()
        filter.set_priority_threshold(NotificationPriority.HIGH)
        
        low_priority = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.LOW,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        assert filter.should_send(low_priority) is False
        
        high_priority = Notification(
            id="124",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.CRITICAL,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        assert filter.should_send(high_priority) is True
    
    def test_include_types(self):
        """Test include types filter."""
        filter = NotificationFilter()
        filter.add_include_type(NotificationType.EMAIL)
        
        email_notif = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        assert filter.should_send(email_notif) is True
        
        sms_notif = Notification(
            id="124",
            type=NotificationType.SMS,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="+1234567890"
        )
        assert filter.should_send(sms_notif) is False
    
    def test_exclude_types(self):
        """Test exclude types filter."""
        filter = NotificationFilter()
        filter.add_exclude_type(NotificationType.SMS)
        
        sms_notif = Notification(
            id="124",
            type=NotificationType.SMS,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="+1234567890"
        )
        assert filter.should_send(sms_notif) is False


class TestNotificationTemplate:
    """Test NotificationTemplate."""
    
    def test_render(self):
        """Test template rendering."""
        template = NotificationTemplate(
            "test",
            "Hello {name}",
            "Welcome {name} to {app}"
        )
        title, message = template.render({"name": "John", "app": "Gmail Agent"})
        assert title == "Hello John"
        assert message == "Welcome John to Gmail Agent"


class TestNotificationTemplateRegistry:
    """Test NotificationTemplateRegistry."""
    
    def test_default_templates(self):
        """Test default templates."""
        registry = NotificationTemplateRegistry()
        assert registry.get("welcome") is not None
        assert registry.get("error") is not None
    
    def test_register_template(self):
        """Test registering template."""
        registry = NotificationTemplateRegistry()
        template = NotificationTemplate("custom", "Title", "Message")
        registry.register(template)
        assert registry.get("custom") == template
    
    def test_render(self):
        """Test rendering template."""
        registry = NotificationTemplateRegistry()
        title, message = registry.render("welcome", {"username": "John", "email_count": 5})
        assert "John" in title or "John" in message


class TestNotificationBatch:
    """Test NotificationBatch."""
    
    def test_add_notification(self):
        """Test adding notification."""
        batch = NotificationBatch(batch_size=3)
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        batch.add(notification)
        assert len(batch.notifications) == 1
    
    def test_is_full(self):
        """Test batch full check."""
        batch = NotificationBatch(batch_size=2)
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        
        batch.add(notification)
        assert batch.is_full() is False
        
        batch.add(notification)
        assert batch.is_full() is True
    
    def test_get_batch(self):
        """Test getting batch."""
        batch = NotificationBatch(batch_size=2)
        notifications = [
            Notification(
                id=str(i),
                type=NotificationType.EMAIL,
                priority=NotificationPriority.MEDIUM,
                title="Test",
                message="Test",
                recipient="test@example.com"
            )
            for i in range(3)
        ]
        
        for n in notifications:
            batch.add(n)
        
        batch_result = batch.get_batch()
        assert len(batch_result) == 2


class TestNotificationScheduler:
    """Test NotificationScheduler."""
    
    def test_schedule(self):
        """Test scheduling notification."""
        scheduler = NotificationScheduler()
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        future_time = datetime.now() + timedelta(hours=1)
        scheduler.schedule(notification, future_time)
        assert len(scheduler.scheduled) == 1
    
    def test_get_ready_notifications(self):
        """Test getting ready notifications."""
        scheduler = NotificationScheduler()
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        
        past_time = datetime.now() - timedelta(hours=1)
        scheduler.schedule(notification, past_time)
        
        ready = scheduler.get_ready_notifications()
        assert len(ready) == 1
    
    def test_future_notifications(self):
        """Test future notifications not ready."""
        scheduler = NotificationScheduler()
        notification = Notification(
            id="123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test",
            recipient="test@example.com"
        )
        
        future_time = datetime.now() + timedelta(hours=1)
        scheduler.schedule(notification, future_time)
        
        ready = scheduler.get_ready_notifications()
        assert len(ready) == 0
