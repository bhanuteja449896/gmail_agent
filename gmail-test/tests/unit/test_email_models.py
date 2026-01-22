"""Tests for email models."""

import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.models.email import (
    Email, EmailAddress, EmailThread, Label, Attachment,
    SearchResult, DraftEmail, EmailStats, EmailFactory,
    AttachmentType, MessageFormat
)


class TestEmailAddress:
    """Test suite for EmailAddress."""
    
    def test_email_address_creation(self):
        """Test email address creation."""
        addr = EmailAddress("user@example.com", "John Doe")
        assert addr.email == "user@example.com"
        assert addr.name == "John Doe"
    
    def test_email_address_string_representation(self):
        """Test email address string representation."""
        addr = EmailAddress("user@example.com", "John Doe")
        assert str(addr) == "John Doe <user@example.com>"
    
    def test_email_address_equality(self):
        """Test email address equality."""
        addr1 = EmailAddress("user@example.com")
        addr2 = EmailAddress("user@example.com")
        assert addr1 == addr2
    
    def test_email_address_case_insensitive(self):
        """Test case insensitive email comparison."""
        addr1 = EmailAddress("user@example.com")
        addr2 = EmailAddress("USER@EXAMPLE.COM")
        assert addr1 == addr2


class TestAttachment:
    """Test suite for Attachment."""
    
    def test_attachment_creation(self):
        """Test attachment creation."""
        attachment = Attachment(
            filename="test.pdf",
            mime_type="application/pdf",
            size=1024,
            attachment_id="att_123"
        )
        assert attachment.filename == "test.pdf"
        assert attachment.size == 1024
    
    def test_attachment_type_image(self):
        """Test attachment type detection for image."""
        attachment = Attachment(
            filename="photo.jpg",
            mime_type="image/jpeg",
            size=5120,
            attachment_id="att_123"
        )
        assert attachment.type == AttachmentType.IMAGE
    
    def test_attachment_type_document(self):
        """Test attachment type detection for document."""
        attachment = Attachment(
            filename="doc.pdf",
            mime_type="application/pdf",
            size=2048,
            attachment_id="att_123"
        )
        assert attachment.type == AttachmentType.DOCUMENT
    
    def test_attachment_type_archive(self):
        """Test attachment type detection for archive."""
        attachment = Attachment(
            filename="archive.zip",
            mime_type="application/zip",
            size=10240,
            attachment_id="att_123"
        )
        assert attachment.type == AttachmentType.ARCHIVE


class TestEmail:
    """Test suite for Email model."""
    
    @pytest.fixture
    def sample_email(self):
        """Create sample email."""
        return Email(
            message_id="msg_123",
            thread_id="thread_123",
            subject="Test Email",
            from_address=EmailAddress("sender@example.com", "Sender"),
            to_addresses=[EmailAddress("recipient@example.com", "Recipient")],
            body="Test body content",
            timestamp=datetime.now(),
            is_read=True,
            is_starred=False
        )
    
    def test_email_creation(self, sample_email):
        """Test email creation."""
        assert sample_email.subject == "Test Email"
        assert sample_email.message_id == "msg_123"
    
    def test_email_is_important(self, sample_email):
        """Test important email detection."""
        assert sample_email.is_important is False
        sample_email.add_label("STARRED")
        assert sample_email.is_important is True
    
    def test_email_has_attachments(self, sample_email):
        """Test attachment detection."""
        assert sample_email.has_attachments is False
        sample_email.attachments.append(
            Attachment("file.txt", "text/plain", 512, "att_1")
        )
        assert sample_email.has_attachments is True
    
    def test_email_recipient_count(self, sample_email):
        """Test recipient count."""
        assert sample_email.recipient_count == 1
        sample_email.cc_addresses.append(EmailAddress("cc@example.com"))
        assert sample_email.recipient_count == 2
    
    def test_email_body_length(self, sample_email):
        """Test body length calculation."""
        length = sample_email.body_length
        assert length == len(sample_email.body)
    
    def test_email_add_label(self, sample_email):
        """Test adding label."""
        sample_email.add_label("IMPORTANT")
        assert sample_email.has_label("IMPORTANT")
    
    def test_email_remove_label(self, sample_email):
        """Test removing label."""
        sample_email.add_label("IMPORTANT")
        sample_email.remove_label("IMPORTANT")
        assert not sample_email.has_label("IMPORTANT")
    
    def test_email_get_all_recipients(self, sample_email):
        """Test getting all recipients."""
        sample_email.cc_addresses.append(EmailAddress("cc@example.com"))
        recipients = sample_email.get_all_recipients()
        assert len(recipients) == 2
    
    def test_email_get_recipient_emails(self, sample_email):
        """Test getting recipient email addresses."""
        emails = sample_email.get_recipient_emails()
        assert "recipient@example.com" in emails


class TestEmailThread:
    """Test suite for EmailThread."""
    
    @pytest.fixture
    def sample_thread(self):
        """Create sample thread."""
        email1 = Email(
            message_id="msg_1",
            thread_id="thread_123",
            subject="Test Thread",
            from_address=EmailAddress("user1@example.com"),
            to_addresses=[EmailAddress("user2@example.com")],
            body="First message",
            timestamp=datetime.now(),
            is_read=True
        )
        return EmailThread(
            thread_id="thread_123",
            subject="Test Thread",
            emails=[email1]
        )
    
    def test_thread_creation(self, sample_thread):
        """Test thread creation."""
        assert sample_thread.thread_id == "thread_123"
        assert sample_thread.message_count == 1
    
    def test_thread_is_empty(self, sample_thread):
        """Test empty thread detection."""
        empty_thread = EmailThread(
            thread_id="empty",
            subject="Empty"
        )
        assert empty_thread.is_empty is True
        assert sample_thread.is_empty is False
    
    def test_thread_is_unread(self, sample_thread):
        """Test unread detection."""
        assert sample_thread.is_unread is False
        sample_thread.emails[0].is_read = False
        assert sample_thread.is_unread is True
    
    def test_thread_participants(self, sample_thread):
        """Test getting participants."""
        participants = sample_thread.participants
        assert "user1@example.com" in participants
    
    def test_thread_first_message(self, sample_thread):
        """Test getting first message."""
        first = sample_thread.first_message
        assert first is not None
        assert first.message_id == "msg_1"
    
    def test_thread_add_email(self, sample_thread):
        """Test adding email to thread."""
        email2 = Email(
            message_id="msg_2",
            thread_id="thread_123",
            subject="Test Thread",
            from_address=EmailAddress("user2@example.com"),
            to_addresses=[],
            body="Second message",
            timestamp=datetime.now()
        )
        sample_thread.add_email(email2)
        assert sample_thread.message_count == 2
    
    def test_thread_mark_as_read(self, sample_thread):
        """Test marking thread as read."""
        sample_thread.emails[0].is_read = False
        sample_thread.mark_as_read()
        assert all(e.is_read for e in sample_thread.emails)


class TestLabel:
    """Test suite for Label."""
    
    def test_label_creation(self):
        """Test label creation."""
        label = Label(
            label_id="INBOX",
            name="INBOX",
            messages_total=100
        )
        assert label.name == "INBOX"
        assert label.messages_total == 100
    
    def test_label_is_system_label(self):
        """Test system label detection."""
        inbox_label = Label(label_id="INBOX", name="INBOX")
        assert inbox_label.is_system_label is True
        
        custom_label = Label(label_id="custom_1", name="Custom")
        assert custom_label.is_system_label is False
    
    def test_label_visibility(self):
        """Test label visibility checks."""
        label = Label(
            label_id="label_1",
            name="Test",
            label_list_visibility="labelShow",
            message_list_visibility="show"
        )
        assert label.is_visible_in_list is True
        assert label.is_visible_in_messages is True


class TestSearchResult:
    """Test suite for SearchResult."""
    
    def test_search_result_creation(self):
        """Test search result creation."""
        result = SearchResult(
            query="from:user@example.com",
            total_results=5
        )
        assert result.query == "from:user@example.com"
        assert result.total_results == 5
    
    def test_search_result_has_more_results(self):
        """Test checking for more results."""
        result = SearchResult(
            query="test",
            total_results=100,
            page_token="next_page"
        )
        assert result.has_more_results is True


class TestDraftEmail:
    """Test suite for DraftEmail."""
    
    def test_draft_creation(self):
        """Test draft email creation."""
        email = Email(
            message_id="draft_1",
            thread_id="",
            subject="Draft Subject",
            from_address=EmailAddress("user@example.com"),
            to_addresses=[EmailAddress("recipient@example.com")],
            body="Draft body",
            timestamp=datetime.now(),
            is_draft=True
        )
        draft = DraftEmail(
            draft_id="draft_1",
            message=email,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert draft.message.is_draft is True
    
    def test_draft_update_content(self):
        """Test updating draft content."""
        email = Email(
            message_id="draft_1",
            thread_id="",
            subject="Original",
            from_address=EmailAddress("user@example.com"),
            to_addresses=[],
            body="Original body",
            timestamp=datetime.now()
        )
        draft = DraftEmail(
            draft_id="draft_1",
            message=email,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        draft.update_content(subject="Updated", body="Updated body")
        assert draft.message.subject == "Updated"
        assert draft.message.body == "Updated body"


class TestEmailStats:
    """Test suite for EmailStats."""
    
    def test_stats_creation(self):
        """Test stats creation."""
        stats = EmailStats(
            total_emails=1000,
            unread_count=50,
            starred_count=10
        )
        assert stats.total_emails == 1000
        assert stats.unread_count == 50
    
    def test_calculate_averages(self):
        """Test average calculation."""
        stats = EmailStats(
            total_emails=100,
            total_size_bytes=1000000
        )
        stats.calculate_averages()
        assert stats.average_email_size == 10000.0


class TestEmailFactory:
    """Test suite for EmailFactory."""
    
    def test_create_from_dict(self):
        """Test creating email from dictionary."""
        data = {
            "id": "msg_123",
            "threadId": "thread_123",
            "subject": "Test",
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "body": "Test body"
        }
        email = EmailFactory.create_from_dict(data)
        assert email.message_id == "msg_123"
        assert email.subject == "Test"
    
    def test_create_thread_from_emails(self):
        """Test creating thread from emails."""
        email1 = Email(
            message_id="msg_1",
            thread_id="thread_1",
            subject="Test",
            from_address=EmailAddress("user@example.com"),
            to_addresses=[],
            body="Message 1",
            timestamp=datetime.now()
        )
        email2 = Email(
            message_id="msg_2",
            thread_id="thread_1",
            subject="Test",
            from_address=EmailAddress("user@example.com"),
            to_addresses=[],
            body="Message 2",
            timestamp=datetime.now()
        )
        thread = EmailFactory.create_thread_from_emails([email1, email2])
        assert thread.message_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
