"""Test fixtures."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from datetime import datetime
from src.core.gmail_client import GmailClient
from src.core.email_processor import EmailProcessor
from src.services.filter_service import FilterService, EmailFilter
from src.models.email import Email, EmailAddress, EmailThread


@pytest.fixture
def gmail_client():
    """Provide Gmail client instance."""
    client = GmailClient()
    client._authenticated = True
    return client


@pytest.fixture
def email_processor():
    """Provide email processor instance."""
    return EmailProcessor()


@pytest.fixture
def filter_service():
    """Provide filter service instance."""
    return FilterService()


@pytest.fixture
def sample_email():
    """Provide sample email data."""
    return {
        "id": "msg_sample_123",
        "threadId": "thread_sample_123",
        "subject": "Sample Email",
        "from": "sender@example.com",
        "to": ["recipient@example.com"],
        "body": "This is a sample email for testing",
        "headers": {
            "Subject": "Sample Email",
            "From": "sender@example.com",
            "To": "recipient@example.com"
        },
        "labelIds": ["INBOX", "UNREAD"]
    }


@pytest.fixture
def email_model():
    """Provide email model instance."""
    return Email(
        message_id="msg_123",
        thread_id="thread_123",
        subject="Test Email",
        from_address=EmailAddress("sender@example.com", "Sender"),
        to_addresses=[EmailAddress("recipient@example.com", "Recipient")],
        body="This is test content",
        timestamp=datetime.now(),
        is_read=False,
        is_starred=False
    )


@pytest.fixture
def email_thread(email_model):
    """Provide email thread instance."""
    thread = EmailThread(
        thread_id="thread_123",
        subject="Test Thread",
        emails=[email_model]
    )
    return thread


@pytest.fixture
def batch_emails(sample_email):
    """Provide batch of sample emails."""
    return [
        {**sample_email, "id": f"msg_{i}", "threadId": f"thread_{i}"}
        for i in range(10)
    ]
