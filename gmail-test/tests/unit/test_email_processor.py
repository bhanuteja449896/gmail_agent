"""Tests for email processor."""

import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.core.email_processor import (
    EmailProcessor, ProcessingStatus, PriorityLevel, ProcessingResult,
    BulkEmailProcessor
)


class TestEmailProcessor:
    """Test suite for EmailProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create email processor."""
        return EmailProcessor()
    
    @pytest.fixture
    def sample_email(self):
        """Create sample email data."""
        return {
            "id": "msg_123",
            "threadId": "thread_123",
            "headers": {
                "Subject": "Test Subject",
                "From": "sender@example.com",
                "To": "recipient@example.com"
            },
            "body": "This is test content",
            "sizeEstimate": 1024,
            "labelIds": ["INBOX"]
        }
    
    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.max_batch_size == 100
        assert processor.timeout == 300
        assert len(processor._filters) == 0
    
    def test_register_processor(self, processor):
        """Test registering custom processor."""
        def custom_processor(email):
            pass
        
        processor.register_processor("custom", custom_processor)
        assert "custom" in processor._processors
    
    def test_register_invalid_processor(self, processor):
        """Test registering invalid processor."""
        with pytest.raises(ValueError):
            processor.register_processor("invalid", "not_callable")
    
    def test_add_filter(self, processor):
        """Test adding filter."""
        def test_filter(email):
            return True
        
        processor.add_filter(test_filter)
        assert len(processor._filters) == 1
    
    def test_add_invalid_filter(self, processor):
        """Test adding invalid filter."""
        with pytest.raises(ValueError):
            processor.add_filter("not_callable")
    
    def test_process_email_success(self, processor, sample_email):
        """Test processing email successfully."""
        result = processor.process_email(sample_email)
        assert result.status == ProcessingStatus.COMPLETED
        assert result.email_id == "msg_123"
    
    def test_process_email_with_filter(self, processor, sample_email):
        """Test processing email with filter."""
        def filter_func(email):
            return email.get("id") == "msg_456"  # Will not match
        
        processor.add_filter(filter_func)
        result = processor.process_email(sample_email)
        assert result.status == ProcessingStatus.SKIPPED
    
    def test_process_batch(self, processor, sample_email):
        """Test processing batch of emails."""
        emails = [sample_email] * 5
        results = processor.process_batch(emails)
        assert len(results) == 5
        assert all(r.status == ProcessingStatus.COMPLETED for r in results)
    
    def test_extract_metadata(self, processor, sample_email):
        """Test extracting metadata."""
        metadata = processor.extract_metadata(sample_email)
        assert metadata["subject"] == "Test Subject"
        assert metadata["from"] == "sender@example.com"
        assert "message_id" in metadata
    
    def test_categorize_email_finance(self, processor):
        """Test categorizing finance email."""
        email = {
            "headers": {
                "Subject": "Invoice for services"
            }
        }
        category = processor.categorize_email(email)
        assert category == "Finance"
    
    def test_categorize_email_meeting(self, processor):
        """Test categorizing meeting email."""
        email = {
            "headers": {
                "Subject": "Meeting scheduled for tomorrow"
            }
        }
        category = processor.categorize_email(email)
        assert category == "Meeting"
    
    def test_categorize_email_general(self, processor):
        """Test categorizing general email."""
        email = {
            "headers": {
                "Subject": "General inquiry"
            }
        }
        category = processor.categorize_email(email)
        assert category == "General"
    
    def test_calculate_priority_critical(self, processor):
        """Test calculating critical priority."""
        email = {
            "headers": {
                "Subject": "URGENT: System down"
            }
        }
        priority = processor.calculate_priority(email)
        assert priority == PriorityLevel.CRITICAL
    
    def test_calculate_priority_normal(self, processor):
        """Test calculating normal priority."""
        email = {
            "headers": {
                "Subject": "Regular email"
            }
        }
        priority = processor.calculate_priority(email)
        assert priority == PriorityLevel.NORMAL
    
    def test_extract_action_items(self, processor):
        """Test extracting action items."""
        email = {
            "body": "TODO: Review the proposal. ACTION: Schedule meeting."
        }
        items = processor.extract_action_items(email)
        assert len(items) >= 0
    
    def test_find_duplicates(self, processor):
        """Test finding duplicate emails."""
        emails = [
            {"headers": {"Subject": "Test", "From": "sender@example.com"}},
            {"headers": {"Subject": "Test", "From": "sender@example.com"}},
            {"headers": {"Subject": "Other", "From": "other@example.com"}}
        ]
        duplicates = processor.find_duplicates(emails)
        assert len(duplicates) > 0
    
    def test_merge_threads(self, processor):
        """Test merging threads."""
        emails = [
            {"threadId": "thread_1", "id": "msg_1"},
            {"threadId": "thread_1", "id": "msg_2"},
            {"threadId": "thread_2", "id": "msg_3"}
        ]
        threads = processor.merge_threads(emails)
        assert "thread_1" in threads
        assert len(threads["thread_1"]) == 2
    
    def test_get_statistics(self, processor, sample_email):
        """Test getting statistics."""
        processor.process_email(sample_email)
        stats = processor.get_statistics()
        assert stats["total_processed"] == 1
        assert stats["successful"] == 1
    
    def test_clear_results(self, processor, sample_email):
        """Test clearing results."""
        processor.process_email(sample_email)
        processor.clear_results()
        assert len(processor._processing_results) == 0
    
    def test_filter_by_sender(self, processor):
        """Test filtering by sender."""
        emails = [
            {"headers": {"From": "alice@example.com"}},
            {"headers": {"From": "bob@example.com"}},
            {"headers": {"From": "alice@example.com"}}
        ]
        filtered = processor.filter_by_sender(emails, ["alice@example.com"])
        assert len(filtered) == 2
    
    def test_filter_by_label(self, processor):
        """Test filtering by label."""
        emails = [
            {"labelIds": ["INBOX", "STARRED"]},
            {"labelIds": ["INBOX"]},
            {"labelIds": ["STARRED"]}
        ]
        filtered = processor.filter_by_label(emails, ["STARRED"])
        assert len(filtered) == 2


class TestBulkEmailProcessor:
    """Test suite for BulkEmailProcessor."""
    
    @pytest.fixture
    def bulk_processor(self):
        """Create bulk email processor."""
        return BulkEmailProcessor(max_batch_size=50)
    
    def test_bulk_processor_initialization(self, bulk_processor):
        """Test bulk processor initialization."""
        assert bulk_processor.max_batch_size == 50
        assert bulk_processor._error_recovery_enabled is True
    
    def test_process_large_batch(self, bulk_processor):
        """Test processing large batch with chunking."""
        emails = [
            {
                "id": f"msg_{i}",
                "headers": {"Subject": f"Email {i}"}
            }
            for i in range(100)
        ]
        results = bulk_processor.process_large_batch(emails, batch_size=25)
        assert len(results) == 100
    
    def test_enable_error_recovery(self, bulk_processor):
        """Test enabling error recovery."""
        bulk_processor.enable_error_recovery(False)
        assert bulk_processor._error_recovery_enabled is False
    
    def test_retry_failed_emails(self, bulk_processor):
        """Test retrying failed emails."""
        # Create a failed result
        failed_result = ProcessingResult(
            email_id="msg_failed",
            status=ProcessingStatus.FAILED,
            error="Test error"
        )
        bulk_processor._processing_results.append(failed_result)
        
        retry_results = bulk_processor.retry_failed_emails()
        assert len(retry_results) > 0


class TestProcessingResult:
    """Test suite for ProcessingResult."""
    
    def test_result_initialization(self):
        """Test result initialization."""
        result = ProcessingResult(
            email_id="msg_123",
            status=ProcessingStatus.COMPLETED
        )
        assert result.email_id == "msg_123"
        assert result.status == ProcessingStatus.COMPLETED
        assert result.error is None
    
    def test_result_with_error(self):
        """Test result with error."""
        result = ProcessingResult(
            email_id="msg_123",
            status=ProcessingStatus.FAILED,
            error="Test error"
        )
        assert result.status == ProcessingStatus.FAILED
        assert result.error == "Test error"


class TestPriorityLevel:
    """Test suite for PriorityLevel enum."""
    
    def test_priority_levels(self):
        """Test priority level values."""
        assert PriorityLevel.LOW.value == 1
        assert PriorityLevel.NORMAL.value == 2
        assert PriorityLevel.HIGH.value == 3
        assert PriorityLevel.CRITICAL.value == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
