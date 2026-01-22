"""Tests for utility modules."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.utils.helpers import (
    UtilityModule, ValidationHelper, CacheManager,
    EmailStatisticsCollector, ConfigurationManager, NotificationManager
)


class TestUtilityModule:
    """Test suite for UtilityModule."""
    
    def test_format_email_address_with_name(self):
        """Test formatting email with name."""
        result = UtilityModule.format_email_address("user@example.com", "John Doe")
        assert result == "John Doe <user@example.com>"
    
    def test_format_email_address_without_name(self):
        """Test formatting email without name."""
        result = UtilityModule.format_email_address("user@example.com")
        assert result == "user@example.com"
    
    def test_parse_email_address(self):
        """Test parsing formatted email."""
        name, email = UtilityModule.parse_email_address("John Doe <user@example.com>")
        assert name == "John Doe"
        assert email == "user@example.com"
    
    def test_parse_email_address_plain(self):
        """Test parsing plain email."""
        name, email = UtilityModule.parse_email_address("user@example.com")
        assert name == ""
        assert email == "user@example.com"
    
    def test_extract_domain(self):
        """Test extracting domain."""
        domain = UtilityModule.extract_domain("user@example.com")
        assert domain == "example.com"
    
    def test_validate_email_format_valid(self):
        """Test validating valid email."""
        assert UtilityModule.validate_email_format("user@example.com") is True
        assert UtilityModule.validate_email_format("user.name@example.co.uk") is True
    
    def test_validate_email_format_invalid(self):
        """Test validating invalid email."""
        assert UtilityModule.validate_email_format("invalid") is False
        assert UtilityModule.validate_email_format("@example.com") is False
    
    def test_sanitize_subject(self):
        """Test sanitizing subject."""
        result = UtilityModule.sanitize_subject("  Multiple   spaces  ")
        assert result == "Multiple spaces"
    
    def test_extract_email_addresses(self):
        """Test extracting emails from text."""
        text = "Contact user1@example.com or user2@example.com"
        emails = UtilityModule.extract_email_addresses(text)
        assert len(emails) == 2
        assert "user1@example.com" in emails
    
    def test_generate_message_id(self):
        """Test generating message ID."""
        msg_id = UtilityModule.generate_message_id()
        assert "<" in msg_id
        assert "@gmail.agent>" in msg_id


class TestValidationHelper:
    """Test suite for ValidationHelper."""
    
    def test_validate_recipients_valid(self):
        """Test validating valid recipients."""
        recipients = ["user1@example.com", "user2@example.com"]
        assert ValidationHelper.validate_recipients(recipients) is True
    
    def test_validate_recipients_invalid(self):
        """Test validating invalid recipients."""
        assert ValidationHelper.validate_recipients([]) is False
        assert ValidationHelper.validate_recipients(["invalid"]) is False
        assert ValidationHelper.validate_recipients(None) is False
    
    def test_validate_email_content_valid(self):
        """Test validating valid email content."""
        assert ValidationHelper.validate_email_content("Subject", "Body") is True
    
    def test_validate_email_content_empty_subject(self):
        """Test validating with empty subject."""
        assert ValidationHelper.validate_email_content("", "Body") is False
    
    def test_validate_email_content_empty_body(self):
        """Test validating with empty body."""
        assert ValidationHelper.validate_email_content("Subject", "") is False
    
    def test_validate_attachment_size_valid(self):
        """Test validating attachment size."""
        # 20 MB < 25 MB limit
        assert ValidationHelper.validate_attachment_size(20 * 1024 * 1024) is True
    
    def test_validate_attachment_size_invalid(self):
        """Test validating oversized attachment."""
        # 30 MB > 25 MB limit
        assert ValidationHelper.validate_attachment_size(30 * 1024 * 1024) is False


class TestCacheManager:
    """Test suite for CacheManager."""
    
    @pytest.fixture
    def cache(self):
        """Create cache manager."""
        return CacheManager(ttl_seconds=3600)
    
    def test_cache_set_and_get(self, cache):
        """Test setting and getting cache."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_delete(self, cache):
        """Test deleting cache entry."""
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_cache_clear(self, cache):
        """Test clearing cache."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get_size() == 0
    
    def test_cache_get_size(self, cache):
        """Test getting cache size."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.get_size() == 2


class TestEmailStatisticsCollector:
    """Test suite for EmailStatisticsCollector."""
    
    @pytest.fixture
    def collector(self):
        """Create statistics collector."""
        return EmailStatisticsCollector()
    
    def test_record_fetch(self, collector):
        """Test recording fetch."""
        collector.record_fetch(5)
        stats = collector.get_stats()
        assert stats["emails_fetched"] == 5
        assert stats["api_calls"] == 1
    
    def test_record_send(self, collector):
        """Test recording send."""
        collector.record_send(3)
        stats = collector.get_stats()
        assert stats["emails_sent"] == 3
    
    def test_record_delete(self, collector):
        """Test recording delete."""
        collector.record_delete(2)
        stats = collector.get_stats()
        assert stats["emails_deleted"] == 2
    
    def test_record_error(self, collector):
        """Test recording error."""
        collector.record_error()
        stats = collector.get_stats()
        assert stats["errors"] == 1
    
    def test_reset(self, collector):
        """Test resetting statistics."""
        collector.record_fetch(5)
        collector.reset()
        stats = collector.get_stats()
        assert stats["emails_fetched"] == 0


class TestConfigurationManager:
    """Test suite for ConfigurationManager."""
    
    @pytest.fixture
    def config(self):
        """Create configuration manager."""
        return ConfigurationManager()
    
    def test_config_set_and_get(self, config):
        """Test setting and getting config."""
        config.set("custom_key", "custom_value")
        assert config.get("custom_key") == "custom_value"
    
    def test_config_get_default(self, config):
        """Test getting config with default."""
        result = config.get("nonexistent", "default")
        assert result == "default"
    
    def test_config_load_from_dict(self, config):
        """Test loading config from dict."""
        new_config = {"key1": "value1", "key2": "value2"}
        config.load_from_dict(new_config)
        assert config.get("key1") == "value1"
    
    def test_config_to_dict(self, config):
        """Test converting config to dict."""
        config.set("test", "value")
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "test" in config_dict


class TestNotificationManager:
    """Test suite for NotificationManager."""
    
    @pytest.fixture
    def notifier(self):
        """Create notification manager."""
        return NotificationManager()
    
    def test_add_notification(self, notifier):
        """Test adding notification."""
        notifier.add_notification("Test message", "INFO")
        notifications = notifier.get_notifications()
        assert len(notifications) == 1
    
    def test_get_notifications_by_level(self, notifier):
        """Test getting notifications by level."""
        notifier.add_notification("Info", "INFO")
        notifier.add_notification("Error", "ERROR")
        errors = notifier.get_notifications("ERROR")
        assert len(errors) == 1
    
    def test_clear_notifications(self, notifier):
        """Test clearing notifications."""
        notifier.add_notification("Test", "INFO")
        notifier.clear()
        assert len(notifier.get_notifications()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
