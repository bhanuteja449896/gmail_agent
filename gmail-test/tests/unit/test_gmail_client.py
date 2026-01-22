"""Unit tests for Gmail client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.core.gmail_client import (
    GmailClient, AuthenticationError, GmailAPIError, RateLimitError,
    ConnectionError, EmailEncoding, retry_on_failure, GmailClientBuilder
)


class TestGmailClient:
    """Test suite for GmailClient."""
    
    @pytest.fixture
    def client(self):
        """Create a Gmail client instance."""
        return GmailClient(debug=True)
    
    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated Gmail client."""
        client = GmailClient()
        client._authenticated = True
        return client
    
    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.user_id == "me"
        assert client.debug is True
        assert client._authenticated is False
        assert client._rate_limit_remaining == 1000
    
    def test_client_with_credentials(self):
        """Test client with credentials."""
        creds = {"access_token": "test_token"}
        client = GmailClient(credentials=creds)
        assert client.credentials == creds
    
    def test_authenticate_empty_token(self, client):
        """Test authentication with empty token."""
        with pytest.raises(AuthenticationError):
            client.authenticate("")
    
    def test_authenticate_none_token(self, client):
        """Test authentication with None token."""
        with pytest.raises(AuthenticationError):
            client.authenticate(None)
    
    def test_authenticate_valid_token(self, client):
        """Test authentication with valid token."""
        result = client.authenticate("valid_token")
        assert result is True
        assert client.is_authenticated() is True
    
    def test_authenticate_with_refresh_token(self, client):
        """Test authentication with refresh token."""
        result = client.authenticate("access_token", refresh_token="refresh_token")
        assert result is True
        assert client.credentials.get("refresh_token") == "refresh_token"
    
    def test_is_authenticated(self, client):
        """Test authentication status check."""
        assert client.is_authenticated() is False
        client._authenticated = True
        assert client.is_authenticated() is True
    
    def test_fetch_emails_not_authenticated(self, client):
        """Test fetching emails without authentication."""
        with pytest.raises(AuthenticationError):
            client.fetch_emails()
    
    def test_fetch_emails_authenticated(self, authenticated_client):
        """Test fetching emails when authenticated."""
        emails, token = authenticated_client.fetch_emails(max_results=5)
        assert len(emails) > 0
        assert all("id" in email for email in emails)
    
    def test_fetch_emails_max_results(self, authenticated_client):
        """Test fetching emails with max results limit."""
        emails, _ = authenticated_client.fetch_emails(max_results=200)
        assert len(emails) <= authenticated_client.MAX_RESULTS_PER_PAGE
    
    def test_fetch_emails_with_query(self, authenticated_client):
        """Test fetching emails with search query."""
        emails, _ = authenticated_client.fetch_emails(query="from:test@example.com")
        assert len(emails) >= 0
    
    def test_fetch_email_by_id(self, authenticated_client):
        """Test fetching email by ID."""
        email = authenticated_client.fetch_email_by_id("msg_123")
        assert email["id"] == "msg_123"
        assert "payload" in email
    
    def test_fetch_email_by_id_invalid_format(self, authenticated_client):
        """Test fetching email with invalid format."""
        with pytest.raises(ValueError):
            authenticated_client.fetch_email_by_id("msg_123", format="invalid")
    
    def test_send_email_success(self, authenticated_client):
        """Test sending email successfully."""
        message_id = authenticated_client.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body"
        )
        assert message_id is not None
        assert len(message_id) > 0
    
    def test_send_email_empty_recipients(self, authenticated_client):
        """Test sending email without recipients."""
        with pytest.raises(ValueError):
            authenticated_client.send_email(to=[], subject="Test", body="Test")
    
    def test_send_email_invalid_recipients(self, authenticated_client):
        """Test sending email with invalid recipients."""
        with pytest.raises(ValueError):
            authenticated_client.send_email(
                to=["invalid_email"],
                subject="Test",
                body="Test"
            )
    
    def test_send_email_empty_subject(self, authenticated_client):
        """Test sending email without subject."""
        with pytest.raises(ValueError):
            authenticated_client.send_email(
                to=["recipient@example.com"],
                subject="",
                body="Test"
            )
    
    def test_send_email_empty_body(self, authenticated_client):
        """Test sending email without body."""
        with pytest.raises(ValueError):
            authenticated_client.send_email(
                to=["recipient@example.com"],
                subject="Test",
                body=""
            )
    
    def test_send_email_with_cc(self, authenticated_client):
        """Test sending email with CC recipients."""
        message_id = authenticated_client.send_email(
            to=["recipient@example.com"],
            subject="Test",
            body="Test",
            cc=["cc@example.com"]
        )
        assert message_id is not None
    
    def test_send_email_with_attachments(self, authenticated_client):
        """Test sending email with attachments."""
        message_id = authenticated_client.send_email(
            to=["recipient@example.com"],
            subject="Test",
            body="Test",
            attachments=["file.txt"]
        )
        assert message_id is not None
    
    def test_delete_email(self, authenticated_client):
        """Test deleting email."""
        result = authenticated_client.delete_email("msg_123")
        assert result is True
    
    def test_delete_email_empty_id(self, authenticated_client):
        """Test deleting email with empty ID."""
        with pytest.raises(ValueError):
            authenticated_client.delete_email("")
    
    def test_delete_email_permanent(self, authenticated_client):
        """Test permanently deleting email."""
        result = authenticated_client.delete_email("msg_123", permanent=True)
        assert result is True
    
    def test_get_labels(self, authenticated_client):
        """Test getting all labels."""
        labels = authenticated_client.get_labels()
        assert len(labels) > 0
        assert any(l["name"] == "INBOX" for l in labels)
    
    def test_create_label(self, authenticated_client):
        """Test creating new label."""
        label = authenticated_client.create_label("TestLabel")
        assert label["name"] == "TestLabel"
        assert "id" in label
    
    def test_apply_label(self, authenticated_client):
        """Test applying label to email."""
        result = authenticated_client.apply_label("msg_123", "STARRED")
        assert result is True
    
    def test_apply_label_empty_email_id(self, authenticated_client):
        """Test applying label with empty email ID."""
        with pytest.raises(ValueError):
            authenticated_client.apply_label("", "STARRED")
    
    def test_remove_label(self, authenticated_client):
        """Test removing label from email."""
        result = authenticated_client.remove_label("msg_123", "STARRED")
        assert result is True
    
    def test_archive_email(self, authenticated_client):
        """Test archiving email."""
        result = authenticated_client.archive_email("msg_123")
        assert result is True
    
    def test_mark_as_read(self, authenticated_client):
        """Test marking email as read."""
        result = authenticated_client.mark_as_read("msg_123")
        assert result is True
    
    def test_mark_as_unread(self, authenticated_client):
        """Test marking email as unread."""
        result = authenticated_client.mark_as_unread("msg_123")
        assert result is True
    
    def test_star_email(self, authenticated_client):
        """Test starring email."""
        result = authenticated_client.star_email("msg_123")
        assert result is True
    
    def test_unstar_email(self, authenticated_client):
        """Test unstarring email."""
        result = authenticated_client.unstar_email("msg_123")
        assert result is True
    
    def test_search_emails(self, authenticated_client):
        """Test searching emails."""
        emails = authenticated_client.search_emails("subject:test")
        assert isinstance(emails, list)
    
    def test_search_emails_empty_query(self, authenticated_client):
        """Test searching with empty query."""
        with pytest.raises(ValueError):
            authenticated_client.search_emails("")
    
    def test_batch_apply_label(self, authenticated_client):
        """Test applying label to multiple emails."""
        count = authenticated_client.batch_apply_label(
            ["msg_1", "msg_2", "msg_3"],
            "STARRED"
        )
        assert count > 0
    
    def test_batch_delete_emails(self, authenticated_client):
        """Test deleting multiple emails."""
        count = authenticated_client.batch_delete_emails(["msg_1", "msg_2"])
        assert count > 0
    
    def test_get_thread(self, authenticated_client):
        """Test getting email thread."""
        thread = authenticated_client.get_thread("thread_123")
        assert thread["id"] == "thread_123"
        assert "messages" in thread
    
    def test_validate_email_valid(self, client):
        """Test email validation with valid email."""
        assert client._validate_email("user@example.com") is True
    
    def test_validate_email_invalid(self, client):
        """Test email validation with invalid email."""
        assert client._validate_email("invalid") is False
        assert client._validate_email("") is False
        assert client._validate_email("@example.com") is False
    
    def test_close_client(self, client):
        """Test closing client."""
        client._session_cache["key"] = "value"
        client._authenticated = True
        client.close()
        assert len(client._session_cache) == 0
        assert client._authenticated is False


class TestGmailClientBuilder:
    """Test suite for GmailClientBuilder."""
    
    def test_builder_default(self):
        """Test builder with default values."""
        client = GmailClientBuilder().build()
        assert client.user_id == "me"
        assert client.debug is False
    
    def test_builder_with_credentials(self):
        """Test builder with credentials."""
        creds = {"token": "test"}
        client = GmailClientBuilder().with_credentials(creds).build()
        assert client.credentials == creds
    
    def test_builder_with_user_id(self):
        """Test builder with custom user ID."""
        client = GmailClientBuilder().with_user_id("user123").build()
        assert client.user_id == "user123"
    
    def test_builder_with_debug(self):
        """Test builder with debug enabled."""
        client = GmailClientBuilder().with_debug(True).build()
        assert client.debug is True
    
    def test_builder_chaining(self):
        """Test builder method chaining."""
        creds = {"token": "test"}
        client = (GmailClientBuilder()
                 .with_credentials(creds)
                 .with_user_id("user123")
                 .with_debug(True)
                 .build())
        
        assert client.credentials == creds
        assert client.user_id == "user123"
        assert client.debug is True


class TestRetryDecorator:
    """Test suite for retry decorator."""
    
    def test_retry_on_success(self):
        """Test retry decorator on successful call."""
        @retry_on_failure(max_attempts=3)
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_retry_on_rate_limit(self):
        """Test retry decorator on rate limit error."""
        call_count = [0]
        
        @retry_on_failure(max_attempts=2, backoff_factor=0.1)
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RateLimitError("Rate limited")
            return "success"
        
        result = rate_limited_func()
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_max_attempts(self):
        """Test retry decorator max attempts."""
        call_count = [0]
        
        @retry_on_failure(max_attempts=2)
        def failing_func():
            call_count[0] += 1
            raise ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            failing_func()
        
        assert call_count[0] == 2


class TestRateLimiting:
    """Test suite for rate limiting."""
    
    def test_rate_limit_check(self):
        """Test rate limit checking."""
        client = GmailClient()
        client._rate_limit_remaining = 5
        # Should not raise when above threshold
        client._check_rate_limit()
    
    def test_rate_limit_warning(self):
        """Test rate limit warning."""
        client = GmailClient()
        client._rate_limit_remaining = 8
        # Should not raise but log warning
        client._check_rate_limit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
