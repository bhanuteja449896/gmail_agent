"""Core Gmail client implementation for API communication and email operations."""

import logging
import json
import time
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from functools import wraps
from abc import ABC, abstractmethod
from enum import Enum
import hashlib
import base64

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class GmailAPIError(Exception):
    """Raised when Gmail API returns an error."""
    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class ConnectionError(Exception):
    """Raised when connection fails."""
    pass


class EmailEncoding(Enum):
    """Email encoding types."""
    UTF8 = "utf-8"
    ASCII = "ascii"
    BASE64 = "base64"


def retry_on_failure(max_attempts: int = 3, backoff_factor: float = 2.0):
    """Decorator to retry failed operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            wait_time = 1.0
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (RateLimitError, ConnectionError) as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    logger.warning(f"Attempt {attempt} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    wait_time *= backoff_factor
                except Exception as e:
                    logger.error(f"Unrecoverable error in {func.__name__}: {e}")
                    raise
            
            return None
        
        return wrapper
    return decorator


class GmailClient:
    """
    Main Gmail client for API communication.
    
    Provides methods for authentication, email fetching, sending, and label management.
    Implements rate limiting, retry logic, and comprehensive error handling.
    """
    
    MAX_RESULTS_PER_PAGE = 100
    API_BASE_URL = "https://www.googleapis.com/gmail/v1/users"
    REQUEST_TIMEOUT = 30
    
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, 
                 user_id: str = "me", debug: bool = False):
        """
        Initialize Gmail client.
        
        Args:
            credentials: OAuth2 credentials dictionary
            user_id: Gmail user ID (default: "me" for current user)
            debug: Enable debug logging
        """
        self.credentials = credentials or {}
        self.user_id = user_id
        self.debug = debug
        self._session_cache: Dict[str, Any] = {}
        self._rate_limit_remaining = 1000
        self._rate_limit_reset_time = None
        self._authenticated = False
        self._last_request_time = 0
        
        if debug:
            logger.setLevel(logging.DEBUG)
    
    def authenticate(self, token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Authenticate with Gmail API using OAuth2 token.
        
        Args:
            token: Access token
            refresh_token: Refresh token for token renewal
            
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            if not token:
                raise AuthenticationError("Token cannot be empty")
            
            self.credentials["access_token"] = token
            if refresh_token:
                self.credentials["refresh_token"] = refresh_token
            
            # Validate token by fetching profile
            profile = self._get_profile()
            if profile and "emailAddress" in profile:
                self._authenticated = True
                self.user_id = profile.get("id", "me")
                logger.info(f"Successfully authenticated as {profile['emailAddress']}")
                return True
            
            raise AuthenticationError("Failed to validate token")
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(str(e))
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._authenticated
    
    def _get_profile(self) -> Dict[str, Any]:
        """Get Gmail account profile information."""
        # Dummy implementation
        return {
            "id": "user123",
            "emailAddress": "user@gmail.com",
            "messagesTotal": 1000,
            "threadsTotal": 500,
            "historyId": "12345"
        }
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        if self._rate_limit_remaining < 10:
            logger.warning("Approaching rate limit")
        
        if self._rate_limit_reset_time and datetime.now() < self._rate_limit_reset_time:
            wait_time = (self._rate_limit_reset_time - datetime.now()).total_seconds()
            raise RateLimitError(f"Rate limit exceeded. Reset in {wait_time}s")
    
    @retry_on_failure(max_attempts=3)
    def fetch_emails(self, query: str = "", max_results: int = 10,
                    page_token: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        """
        Fetch emails matching query.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of emails to fetch
            page_token: Token for pagination
            
        Returns:
            Tuple of (emails list, next page token)
        """
        self._check_rate_limit()
        
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        if max_results > self.MAX_RESULTS_PER_PAGE:
            max_results = self.MAX_RESULTS_PER_PAGE
        
        # Dummy implementation
        emails = []
        for i in range(min(max_results, 5)):
            emails.append({
                "id": f"msg_{i}_{int(time.time())}",
                "threadId": f"thread_{i}",
                "labelIds": ["INBOX"],
                "snippet": f"Email snippet {i}",
                "internalDate": str(int(time.time() * 1000)),
                "headers": {
                    "Subject": f"Test Email {i}",
                    "From": f"sender{i}@example.com",
                    "To": "recipient@example.com"
                }
            })
        
        return emails, None
    
    def fetch_email_by_id(self, email_id: str, format: str = "full") -> Dict[str, Any]:
        """
        Fetch specific email by ID.
        
        Args:
            email_id: Email message ID
            format: Format of the response (minimal, full, raw)
            
        Returns:
            Email data dictionary
        """
        if not email_id:
            raise ValueError("Email ID cannot be empty")
        
        if format not in ("minimal", "full", "raw"):
            raise ValueError(f"Invalid format: {format}")
        
        # Dummy implementation
        return {
            "id": email_id,
            "threadId": f"thread_{email_id}",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"}
                ],
                "body": {
                    "size": 1234,
                    "data": base64.b64encode(b"Email body content").decode()
                }
            },
            "sizeEstimate": 1234
        }
    
    def send_email(self, to: List[str], subject: str, body: str,
                   cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None,
                   attachments: Optional[List[str]] = None) -> str:
        """
        Send an email.
        
        Args:
            to: Recipient email addresses
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            attachments: File paths for attachments
            
        Returns:
            Message ID of sent email
            
        Raises:
            ValueError: If required parameters are missing
        """
        if not to or not isinstance(to, list):
            raise ValueError("Recipients must be a non-empty list")
        
        if not subject or not isinstance(subject, str):
            raise ValueError("Subject must be a non-empty string")
        
        if not body:
            raise ValueError("Body cannot be empty")
        
        # Validate email addresses
        for email in to:
            if not self._validate_email(email):
                raise ValueError(f"Invalid email address: {email}")
        
        # Dummy implementation
        message_id = hashlib.sha256(f"{subject}{to}{time.time()}".encode()).hexdigest()[:20]
        logger.info(f"Email sent to {', '.join(to)} with ID {message_id}")
        return message_id
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        if not email or "@" not in email:
            return False
        parts = email.split("@")
        return len(parts) == 2 and parts[0] and parts[1]
    
    def delete_email(self, email_id: str, permanent: bool = False) -> bool:
        """
        Delete an email.
        
        Args:
            email_id: Email message ID
            permanent: If True, permanently delete; otherwise move to Trash
            
        Returns:
            True if successful
        """
        if not email_id:
            raise ValueError("Email ID cannot be empty")
        
        logger.info(f"Email {email_id} {'permanently deleted' if permanent else 'moved to trash'}")
        return True
    
    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all labels for the user."""
        # Dummy implementation
        return [
            {"id": "INBOX", "name": "INBOX"},
            {"id": "SENT", "name": "SENT"},
            {"id": "DRAFT", "name": "DRAFT"},
            {"id": "TRASH", "name": "TRASH"},
            {"id": "SPAM", "name": "SPAM"},
        ]
    
    def create_label(self, name: str, label_list_visibility: str = "labelShow",
                    message_list_visibility: str = "show") -> Dict[str, Any]:
        """
        Create a new label.
        
        Args:
            name: Label name
            label_list_visibility: Visibility in label list
            message_list_visibility: Visibility in message list
            
        Returns:
            Created label data
        """
        if not name or not isinstance(name, str):
            raise ValueError("Label name must be a non-empty string")
        
        label_id = hashlib.sha256(name.encode()).hexdigest()[:16]
        return {
            "id": label_id,
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility
        }
    
    def apply_label(self, email_id: str, label_id: str) -> bool:
        """Apply label to an email."""
        if not email_id or not label_id:
            raise ValueError("Email ID and label ID cannot be empty")
        
        logger.info(f"Applied label {label_id} to email {email_id}")
        return True
    
    def remove_label(self, email_id: str, label_id: str) -> bool:
        """Remove label from an email."""
        if not email_id or not label_id:
            raise ValueError("Email ID and label ID cannot be empty")
        
        logger.info(f"Removed label {label_id} from email {email_id}")
        return True
    
    def archive_email(self, email_id: str) -> bool:
        """Archive an email (remove from INBOX)."""
        return self.remove_label(email_id, "INBOX")
    
    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read."""
        if not email_id:
            raise ValueError("Email ID cannot be empty")
        
        return self.remove_label(email_id, "UNREAD")
    
    def mark_as_unread(self, email_id: str) -> bool:
        """Mark email as unread."""
        if not email_id:
            raise ValueError("Email ID cannot be empty")
        
        return self.apply_label(email_id, "UNREAD")
    
    def star_email(self, email_id: str) -> bool:
        """Add star to email."""
        return self.apply_label(email_id, "STARRED")
    
    def unstar_email(self, email_id: str) -> bool:
        """Remove star from email."""
        return self.remove_label(email_id, "STARRED")
    
    def search_emails(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for emails using Gmail search syntax.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List of matching emails
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        emails, _ = self.fetch_emails(query, max_results)
        return emails
    
    def batch_apply_label(self, email_ids: List[str], label_id: str) -> int:
        """
        Apply label to multiple emails.
        
        Args:
            email_ids: List of email IDs
            label_id: Label to apply
            
        Returns:
            Number of emails successfully labeled
        """
        count = 0
        for email_id in email_ids:
            try:
                if self.apply_label(email_id, label_id):
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to label email {email_id}: {e}")
        
        return count
    
    def batch_delete_emails(self, email_ids: List[str], permanent: bool = False) -> int:
        """
        Delete multiple emails.
        
        Args:
            email_ids: List of email IDs
            permanent: If True, permanently delete
            
        Returns:
            Number of successfully deleted emails
        """
        count = 0
        for email_id in email_ids:
            try:
                if self.delete_email(email_id, permanent):
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to delete email {email_id}: {e}")
        
        return count
    
    def get_thread(self, thread_id: str, format: str = "full") -> Dict[str, Any]:
        """Get email thread by ID."""
        if not thread_id:
            raise ValueError("Thread ID cannot be empty")
        
        return {
            "id": thread_id,
            "messages": []
        }
    
    def close(self):
        """Close the client and cleanup resources."""
        self._session_cache.clear()
        self._authenticated = False
        logger.info("Gmail client closed")


class GmailClientBuilder:
    """Builder for configuring Gmail client."""
    
    def __init__(self):
        self._credentials = {}
        self._user_id = "me"
        self._debug = False
    
    def with_credentials(self, credentials: Dict[str, Any]) -> 'GmailClientBuilder':
        self._credentials = credentials
        return self
    
    def with_user_id(self, user_id: str) -> 'GmailClientBuilder':
        self._user_id = user_id
        return self
    
    def with_debug(self, debug: bool) -> 'GmailClientBuilder':
        self._debug = debug
        return self
    
    def build(self) -> GmailClient:
        return GmailClient(
            credentials=self._credentials,
            user_id=self._user_id,
            debug=self._debug
        )
