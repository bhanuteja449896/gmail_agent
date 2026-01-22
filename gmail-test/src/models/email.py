"""Data models for Gmail agent."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class MessageFormat(Enum):
    """Message format types."""
    PLAIN_TEXT = "text/plain"
    HTML = "text/html"
    MULTIPART = "multipart/mixed"


class AttachmentType(Enum):
    """Attachment type enumeration."""
    DOCUMENT = "document"
    IMAGE = "image"
    ARCHIVE = "archive"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


@dataclass
class Attachment:
    """Email attachment data."""
    filename: str
    mime_type: str
    size: int
    attachment_id: str
    data: Optional[bytes] = None
    
    @property
    def type(self) -> AttachmentType:
        """Determine attachment type from MIME type."""
        if self.mime_type.startswith("image/"):
            return AttachmentType.IMAGE
        elif self.mime_type.startswith("video/"):
            return AttachmentType.VIDEO
        elif self.mime_type.startswith("audio/"):
            return AttachmentType.AUDIO
        elif "pdf" in self.mime_type or "word" in self.mime_type:
            return AttachmentType.DOCUMENT
        elif "zip" in self.mime_type or "archive" in self.mime_type:
            return AttachmentType.ARCHIVE
        else:
            return AttachmentType.OTHER


@dataclass
class EmailAddress:
    """Email address representation."""
    email: str
    name: Optional[str] = None
    
    def __str__(self) -> str:
        """Return formatted email address."""
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email
    
    def __eq__(self, other) -> bool:
        """Compare email addresses."""
        if isinstance(other, EmailAddress):
            return self.email.lower() == other.email.lower()
        elif isinstance(other, str):
            return self.email.lower() == other.lower()
        return False


@dataclass
class Email:
    """
    Email message representation.
    
    Comprehensive data model for email messages with metadata,
    content, and attachment support.
    """
    message_id: str
    thread_id: str
    subject: str
    from_address: EmailAddress
    to_addresses: List[EmailAddress]
    body: str
    timestamp: datetime
    labels: List[str] = field(default_factory=list)
    cc_addresses: List[EmailAddress] = field(default_factory=list)
    bcc_addresses: List[EmailAddress] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    is_read: bool = True
    is_starred: bool = False
    is_draft: bool = False
    is_spam: bool = False
    is_trash: bool = False
    raw_message: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_important(self) -> bool:
        """Check if email is marked as important."""
        return "IMPORTANT" in self.labels or "STARRED" in self.labels
    
    @property
    def has_attachments(self) -> bool:
        """Check if email has attachments."""
        return len(self.attachments) > 0
    
    @property
    def recipient_count(self) -> int:
        """Get total recipient count."""
        return len(self.to_addresses) + len(self.cc_addresses) + len(self.bcc_addresses)
    
    @property
    def body_length(self) -> int:
        """Get body length in characters."""
        return len(self.body) if self.body else 0
    
    def add_label(self, label: str) -> None:
        """Add label to email."""
        if label not in self.labels:
            self.labels.append(label)
    
    def remove_label(self, label: str) -> None:
        """Remove label from email."""
        if label in self.labels:
            self.labels.remove(label)
    
    def has_label(self, label: str) -> bool:
        """Check if email has label."""
        return label in self.labels
    
    def get_all_recipients(self) -> List[EmailAddress]:
        """Get all recipients (to, cc, bcc)."""
        return self.to_addresses + self.cc_addresses + self.bcc_addresses
    
    def get_recipient_emails(self) -> List[str]:
        """Get all recipient email addresses."""
        return [addr.email for addr in self.get_all_recipients()]


@dataclass
class EmailThread:
    """
    Email thread containing multiple related messages.
    
    Represents a conversation thread with multiple emails.
    """
    thread_id: str
    subject: str
    emails: List[Email] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    snippet: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def message_count(self) -> int:
        """Get number of messages in thread."""
        return len(self.emails)
    
    @property
    def is_empty(self) -> bool:
        """Check if thread has no messages."""
        return len(self.emails) == 0
    
    @property
    def is_unread(self) -> bool:
        """Check if any message in thread is unread."""
        return any(not email.is_read for email in self.emails)
    
    @property
    def participants(self) -> set:
        """Get all participants in thread."""
        participants = set()
        for email in self.emails:
            participants.add(email.from_address.email)
            for addr in email.get_all_recipients():
                participants.add(addr.email)
        return participants
    
    @property
    def first_message(self) -> Optional[Email]:
        """Get first message in thread."""
        if self.emails:
            return min(self.emails, key=lambda e: e.timestamp)
        return None
    
    @property
    def last_message(self) -> Optional[Email]:
        """Get last message in thread."""
        if self.emails:
            return max(self.emails, key=lambda e: e.timestamp)
        return None
    
    def add_email(self, email: Email) -> None:
        """Add email to thread."""
        if email not in self.emails:
            self.emails.append(email)
            if self.created_at is None or email.timestamp < self.created_at:
                self.created_at = email.timestamp
            self.updated_at = email.timestamp
    
    def get_emails_from(self, sender: str) -> List[Email]:
        """Get emails from specific sender."""
        return [e for e in self.emails 
                if e.from_address.email.lower() == sender.lower()]
    
    def mark_as_read(self) -> None:
        """Mark all emails in thread as read."""
        for email in self.emails:
            email.is_read = True
    
    def mark_as_unread(self) -> None:
        """Mark all emails in thread as unread."""
        for email in self.emails:
            email.is_read = False


@dataclass
class Label:
    """
    Gmail label representation.
    
    Represents a label for organizing emails.
    """
    label_id: str
    name: str
    message_list_visibility: str = "show"
    label_list_visibility: str = "labelShow"
    color: Optional[str] = None
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    messages_total: int = 0
    messages_unread: int = 0
    threads_total: int = 0
    threads_unread: int = 0
    
    @property
    def is_system_label(self) -> bool:
        """Check if label is a system label."""
        system_labels = {"INBOX", "DRAFT", "SENT", "STARRED", "IMPORTANT", "TRASH", "SPAM", "UNREAD"}
        return self.label_id in system_labels
    
    @property
    def is_visible_in_list(self) -> bool:
        """Check if label is visible in label list."""
        return self.label_list_visibility == "labelShow"
    
    @property
    def is_visible_in_messages(self) -> bool:
        """Check if label is visible in message list."""
        return self.message_list_visibility == "show"
    
    def __str__(self) -> str:
        """Return label name."""
        return self.name


@dataclass
class SearchResult:
    """
    Email search result.
    
    Contains search query and matching emails.
    """
    query: str
    total_results: int
    emails: List[Email] = field(default_factory=list)
    page_token: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def has_more_results(self) -> bool:
        """Check if there are more results."""
        return self.page_token is not None


@dataclass
class DraftEmail:
    """
    Email draft.
    
    Represents an unsent email draft.
    """
    draft_id: str
    message: Email
    created_at: datetime
    updated_at: datetime
    auto_save: bool = True
    
    def update_content(self, subject: Optional[str] = None, 
                      body: Optional[str] = None) -> None:
        """Update draft content."""
        if subject is not None:
            self.message.subject = subject
        if body is not None:
            self.message.body = body
        self.updated_at = datetime.now()


@dataclass
class EmailStats:
    """Email statistics."""
    total_emails: int = 0
    total_threads: int = 0
    unread_count: int = 0
    starred_count: int = 0
    spam_count: int = 0
    trash_count: int = 0
    total_size_bytes: int = 0
    average_email_size: float = 0.0
    
    def calculate_averages(self) -> None:
        """Calculate average statistics."""
        if self.total_emails > 0:
            self.average_email_size = self.total_size_bytes / self.total_emails


class EmailFactory:
    """Factory for creating email objects."""
    
    @staticmethod
    def create_from_dict(data: Dict[str, Any]) -> Email:
        """Create Email from dictionary."""
        return Email(
            message_id=data.get("id", ""),
            thread_id=data.get("threadId", ""),
            subject=data.get("subject", ""),
            from_address=EmailAddress(data.get("from", "")),
            to_addresses=[EmailAddress(t) for t in data.get("to", [])],
            body=data.get("body", ""),
            timestamp=datetime.now(),
            labels=data.get("labels", [])
        )
    
    @staticmethod
    def create_thread_from_emails(emails: List[Email]) -> EmailThread:
        """Create EmailThread from list of emails."""
        if not emails:
            raise ValueError("Cannot create thread from empty email list")
        
        thread = EmailThread(
            thread_id=emails[0].thread_id,
            subject=emails[0].subject,
            emails=emails
        )
        return thread
