"""Email processor for handling email operations and workflows."""

import logging
import json
import hashlib
from typing import List, Dict, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Email processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PriorityLevel(Enum):
    """Email priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ProcessingResult:
    """Result of email processing."""
    email_id: str
    status: ProcessingStatus
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmailProcessor:
    """
    Main email processor for handling various email operations.
    
    Supports filtering, categorization, prioritization, and batch processing.
    """
    
    def __init__(self, max_batch_size: int = 100, timeout: int = 300):
        """
        Initialize email processor.
        
        Args:
            max_batch_size: Maximum emails to process in one batch
            timeout: Processing timeout in seconds
        """
        self.max_batch_size = max_batch_size
        self.timeout = timeout
        self._processing_queue: List[str] = []
        self._processing_results: List[ProcessingResult] = []
        self._processors: Dict[str, Callable] = {}
        self._filters: List[Callable] = []
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def register_processor(self, name: str, processor: Callable) -> None:
        """
        Register a custom email processor function.
        
        Args:
            name: Processor name
            processor: Callable that processes an email
        """
        if not callable(processor):
            raise ValueError("Processor must be callable")
        
        self._processors[name] = processor
        logger.info(f"Registered processor: {name}")
    
    def add_filter(self, filter_func: Callable[[Dict], bool]) -> None:
        """
        Add a filter to the processor.
        
        Args:
            filter_func: Function that returns True for emails to process
        """
        if not callable(filter_func):
            raise ValueError("Filter must be callable")
        
        self._filters.append(filter_func)
        logger.info(f"Added filter, total filters: {len(self._filters)}")
    
    def process_email(self, email_data: Dict[str, Any], 
                     processor_name: Optional[str] = None) -> ProcessingResult:
        """
        Process a single email.
        
        Args:
            email_data: Email data dictionary
            processor_name: Name of processor to use
            
        Returns:
            ProcessingResult object
        """
        email_id = email_data.get("id", "unknown")
        
        try:
            # Apply filters
            for filter_func in self._filters:
                if not filter_func(email_data):
                    result = ProcessingResult(
                        email_id=email_id,
                        status=ProcessingStatus.SKIPPED,
                        message="Filtered out by filter"
                    )
                    self._processing_results.append(result)
                    self._stats["skipped"] += 1
                    return result
            
            # Use specified processor or default
            if processor_name and processor_name in self._processors:
                self._processors[processor_name](email_data)
            elif self._processors:
                for processor in self._processors.values():
                    processor(email_data)
            
            result = ProcessingResult(
                email_id=email_id,
                status=ProcessingStatus.COMPLETED,
                message="Email processed successfully"
            )
            self._processing_results.append(result)
            self._stats["successful"] += 1
            self._stats["total_processed"] += 1
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to process email {email_id}: {e}")
            result = ProcessingResult(
                email_id=email_id,
                status=ProcessingStatus.FAILED,
                message="Processing failed",
                error=str(e)
            )
            self._processing_results.append(result)
            self._stats["failed"] += 1
            self._stats["total_processed"] += 1
            
            return result
    
    def process_batch(self, emails: List[Dict[str, Any]], 
                     processor_name: Optional[str] = None) -> List[ProcessingResult]:
        """
        Process multiple emails in batch.
        
        Args:
            emails: List of email data dictionaries
            processor_name: Name of processor to use
            
        Returns:
            List of ProcessingResult objects
        """
        if len(emails) > self.max_batch_size:
            logger.warning(f"Batch size {len(emails)} exceeds max {self.max_batch_size}")
        
        results = []
        for email in emails:
            result = self.process_email(email, processor_name)
            results.append(result)
        
        logger.info(f"Processed {len(results)} emails")
        return results
    
    def extract_metadata(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from email.
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            Dictionary of extracted metadata
        """
        headers = email_data.get("headers", {})
        
        metadata = {
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "cc": headers.get("Cc", ""),
            "date": headers.get("Date", ""),
            "message_id": email_data.get("id", ""),
            "size": email_data.get("sizeEstimate", 0),
            "has_attachments": len(email_data.get("attachments", [])) > 0
        }
        
        return metadata
    
    def categorize_email(self, email_data: Dict[str, Any]) -> str:
        """
        Categorize email based on content.
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            Category name
        """
        subject = email_data.get("headers", {}).get("Subject", "").lower()
        from_addr = email_data.get("headers", {}).get("From", "").lower()
        
        # Dummy categorization logic
        if any(word in subject for word in ["invoice", "receipt", "payment"]):
            return "Finance"
        elif any(word in subject for word in ["meeting", "schedule", "calendar"]):
            return "Meeting"
        elif any(word in subject for word in ["alert", "error", "warning"]):
            return "Alert"
        elif "noreply" in from_addr or "no-reply" in from_addr:
            return "Notification"
        else:
            return "General"
    
    def calculate_priority(self, email_data: Dict[str, Any]) -> PriorityLevel:
        """
        Calculate email priority.
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            PriorityLevel
        """
        subject = email_data.get("headers", {}).get("Subject", "").lower()
        
        if any(word in subject for word in ["urgent", "critical", "important", "asap"]):
            return PriorityLevel.CRITICAL
        elif any(word in subject for word in ["important"]):
            return PriorityLevel.HIGH
        elif any(word in subject for word in ["low priority", "fyi", "info"]):
            return PriorityLevel.LOW
        else:
            return PriorityLevel.NORMAL
    
    def extract_action_items(self, email_data: Dict[str, Any]) -> List[str]:
        """
        Extract action items from email.
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            List of action items
        """
        body = email_data.get("body", "")
        action_items = []
        
        # Simple pattern matching for action items
        patterns = [
            r'(?:TODO|Action|Please):\s*(.+?)(?:\.|$)',
            r'(?:Need to|Should|Must)\s+(.+?)(?:\.|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            action_items.extend(matches)
        
        return action_items
    
    def find_duplicates(self, emails: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """
        Find duplicate emails in a list.
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            List of (index1, index2) tuples of duplicate pairs
        """
        hashes = {}
        duplicates = []
        
        for idx, email in enumerate(emails):
            subject = email.get("headers", {}).get("Subject", "")
            from_addr = email.get("headers", {}).get("From", "")
            
            # Create hash of email
            email_hash = hashlib.md5(f"{subject}:{from_addr}".encode()).hexdigest()
            
            if email_hash in hashes:
                duplicates.append((hashes[email_hash], idx))
            else:
                hashes[email_hash] = idx
        
        return duplicates
    
    def merge_threads(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Group emails by thread.
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            Dictionary mapping thread IDs to emails
        """
        threads = {}
        
        for email in emails:
            thread_id = email.get("threadId", "unknown")
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)
        
        return threads
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self._stats,
            "pending": len(self._processing_queue),
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_results(self) -> None:
        """Clear processing results."""
        self._processing_results.clear()
        logger.info("Cleared processing results")
    
    def filter_by_date_range(self, emails: List[Dict], 
                            start_date: datetime, 
                            end_date: datetime) -> List[Dict]:
        """Filter emails by date range."""
        filtered = []
        for email in emails:
            # Dummy date filtering
            filtered.append(email)
        
        return filtered
    
    def filter_by_sender(self, emails: List[Dict], 
                        senders: List[str]) -> List[Dict]:
        """Filter emails by sender."""
        filtered = []
        for email in emails:
            from_addr = email.get("headers", {}).get("From", "").lower()
            if any(sender.lower() in from_addr for sender in senders):
                filtered.append(email)
        
        return filtered
    
    def filter_by_label(self, emails: List[Dict], 
                       labels: List[str]) -> List[Dict]:
        """Filter emails by label."""
        filtered = []
        for email in emails:
            email_labels = email.get("labelIds", [])
            if any(label in email_labels for label in labels):
                filtered.append(email)
        
        return filtered


class BulkEmailProcessor(EmailProcessor):
    """Extended processor for handling large-scale email processing."""
    
    def __init__(self, max_batch_size: int = 1000, timeout: int = 600):
        super().__init__(max_batch_size, timeout)
        self._batch_results = []
        self._error_recovery_enabled = True
    
    def process_large_batch(self, emails: List[Dict], 
                           batch_size: Optional[int] = None) -> List[ProcessingResult]:
        """Process large email batches with chunking."""
        if batch_size is None:
            batch_size = self.max_batch_size
        
        results = []
        for i in range(0, len(emails), batch_size):
            chunk = emails[i:i + batch_size]
            chunk_results = self.process_batch(chunk)
            results.extend(chunk_results)
            logger.info(f"Processed batch {i // batch_size + 1}")
        
        return results
    
    def enable_error_recovery(self, enabled: bool = True) -> None:
        """Enable/disable error recovery for failed emails."""
        self._error_recovery_enabled = enabled
    
    def retry_failed_emails(self) -> List[ProcessingResult]:
        """Retry processing of failed emails."""
        failed_results = [r for r in self._processing_results 
                         if r.status == ProcessingStatus.FAILED]
        
        retry_results = []
        for result in failed_results:
            logger.info(f"Retrying email {result.email_id}")
            retry_results.append(result)
        
        return retry_results
