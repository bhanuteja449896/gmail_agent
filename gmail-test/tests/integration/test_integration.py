"""Integration tests for Gmail agent."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.core.gmail_client import GmailClient
from src.core.email_processor import EmailProcessor
from src.services.filter_service import FilterService, FilterOperator, FilterAction
from src.models.email import Email, EmailAddress


class TestGmailClientIntegration:
    """Integration tests for Gmail client."""
    
    @pytest.fixture
    def client(self):
        """Create authenticated Gmail client."""
        client = GmailClient()
        client._authenticated = True
        return client
    
    def test_full_email_workflow(self, client):
        """Test complete email workflow."""
        # Fetch emails
        emails, _ = client.fetch_emails(max_results=5)
        assert len(emails) > 0
        
        # Get first email details
        if emails:
            email = client.fetch_email_by_id(emails[0]["id"])
            assert email is not None
            assert "payload" in email
    
    def test_email_management_workflow(self, client):
        """Test email management workflow."""
        # Send email
        msg_id = client.send_email(
            to=["test@example.com"],
            subject="Integration Test",
            body="This is an integration test"
        )
        assert msg_id is not None
        
        # Star the email
        result = client.star_email(msg_id)
        assert result is True
        
        # Mark as read
        result = client.mark_as_read(msg_id)
        assert result is True


class TestEmailProcessorIntegration:
    """Integration tests for email processor."""
    
    @pytest.fixture
    def processor(self):
        """Create email processor."""
        return EmailProcessor()
    
    @pytest.fixture
    def sample_emails(self):
        """Create sample emails."""
        return [
            {
                "id": f"msg_{i}",
                "threadId": f"thread_{i}",
                "headers": {
                    "Subject": f"Email {i}",
                    "From": f"sender{i}@example.com"
                },
                "labelIds": ["INBOX"]
            }
            for i in range(10)
        ]
    
    def test_batch_processing_workflow(self, processor, sample_emails):
        """Test batch processing workflow."""
        # Process batch
        results = processor.process_batch(sample_emails)
        assert len(results) == 10
        
        # Check statistics
        stats = processor.get_statistics()
        assert stats["total_processed"] == 10


class TestFilteringIntegration:
    """Integration tests for filtering."""
    
    @pytest.fixture
    def filter_service(self):
        """Create filter service."""
        return FilterService()
    
    @pytest.fixture
    def sample_email(self):
        """Create sample email."""
        return {
            "id": "msg_123",
            "from": "important@example.com",
            "subject": "URGENT: Action Required",
            "headers": {
                "Subject": "URGENT: Action Required",
                "From": "important@example.com"
            }
        }
    
    def test_multi_condition_filtering(self, filter_service, sample_email):
        """Test filtering with multiple conditions."""
        # Create filter
        filter_obj = filter_service.create_filter("Critical")
        filter_obj.add_condition("subject", FilterOperator.CONTAINS, "URGENT")
        filter_obj.add_condition("from", FilterOperator.CONTAINS, "important")
        filter_obj.add_action(FilterAction.STAR)
        filter_obj.add_action(FilterAction.LABEL)
        filter_service.enable_filter("Critical")
        
        # Apply filter
        actions = filter_service.apply_filters(sample_email)
        assert len(actions) > 0


class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    def test_email_fetch_and_process(self):
        """Test fetching and processing emails."""
        # Create components
        client = GmailClient()
        client._authenticated = True
        processor = EmailProcessor()
        
        # Fetch emails
        emails, _ = client.fetch_emails(max_results=5)
        
        # Process them
        if emails:
            results = processor.process_batch(emails)
            assert len(results) == len(emails)
    
    def test_filter_and_label_workflow(self):
        """Test filtering and labeling emails."""
        client = GmailClient()
        client._authenticated = True
        filter_service = FilterService()
        
        # Create filter
        filter_obj = filter_service.create_filter("Work")
        filter_obj.add_condition("from", FilterOperator.CONTAINS, "work")
        filter_obj.add_action(FilterAction.LABEL)
        filter_service.enable_filter("Work")
        
        # Get emails and apply filter
        emails, _ = client.fetch_emails(max_results=5)
        if emails:
            for email in emails:
                actions = filter_service.apply_filters(email)
                if FilterAction.LABEL in actions:
                    client.apply_label(email["id"], "WORK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
