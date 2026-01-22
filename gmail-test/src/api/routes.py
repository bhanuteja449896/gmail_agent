"""API layer for Gmail agent."""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """API response status codes."""
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"


@dataclass
class APIResponse:
    """Standard API response."""
    status: ResponseStatus
    message: str = ""
    data: Optional[Any] = None
    errors: List[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat()
        }


class APIError(Exception):
    """Base API error."""
    
    def __init__(self, message: str, status: ResponseStatus = ResponseStatus.ERROR):
        self.message = message
        self.status = status
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error."""
    
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message, ResponseStatus.VALIDATION_ERROR)
        self.errors = errors or []


class NotFoundError(APIError):
    """Not found error."""
    
    def __init__(self, message: str):
        super().__init__(message, ResponseStatus.NOT_FOUND)


class UnauthorizedError(APIError):
    """Unauthorized error."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, ResponseStatus.UNAUTHORIZED)


class GmailAPI:
    """
    REST API interface for Gmail agent.
    
    Provides endpoints for email operations, filtering, and management.
    """
    
    def __init__(self, version: str = "v1"):
        """Initialize API."""
        self.version = version
        self.base_path = f"/api/{version}"
        logger.info(f"Initialized GmailAPI version {version}")
    
    def get_emails(self, query: str = "", limit: int = 10) -> APIResponse:
        """Get emails endpoint."""
        try:
            if limit < 1 or limit > 100:
                raise ValidationError(
                    "Invalid limit",
                    ["Limit must be between 1 and 100"]
                )
            
            # Dummy implementation
            emails = [
                {"id": f"msg_{i}", "subject": f"Email {i}"}
                for i in range(min(limit, 5))
            ]
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="Emails retrieved",
                data={"emails": emails, "count": len(emails)}
            )
        except ValidationError as e:
            return APIResponse(
                status=e.status,
                message=e.message,
                errors=getattr(e, 'errors', [])
            )
    
    def send_email(self, to: List[str], subject: str, body: str) -> APIResponse:
        """Send email endpoint."""
        try:
            if not to or not isinstance(to, list):
                raise ValidationError(
                    "Invalid recipients",
                    ["Recipients must be a non-empty list"]
                )
            
            if not subject:
                raise ValidationError(
                    "Invalid subject",
                    ["Subject cannot be empty"]
                )
            
            if not body:
                raise ValidationError(
                    "Invalid body",
                    ["Body cannot be empty"]
                )
            
            # Dummy implementation
            message_id = f"msg_{datetime.now().timestamp()}"
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="Email sent successfully",
                data={"message_id": message_id}
            )
        except ValidationError as e:
            return APIResponse(
                status=e.status,
                message=e.message,
                errors=getattr(e, 'errors', [])
            )
    
    def delete_email(self, email_id: str) -> APIResponse:
        """Delete email endpoint."""
        try:
            if not email_id:
                raise ValidationError(
                    "Invalid email ID",
                    ["Email ID cannot be empty"]
                )
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="Email deleted",
                data={"email_id": email_id}
            )
        except ValidationError as e:
            return APIResponse(
                status=e.status,
                message=e.message,
                errors=getattr(e, 'errors', [])
            )
    
    def apply_filter(self, filter_name: str, email_ids: List[str]) -> APIResponse:
        """Apply filter endpoint."""
        try:
            if not filter_name:
                raise ValidationError(
                    "Invalid filter",
                    ["Filter name cannot be empty"]
                )
            
            if not email_ids:
                raise ValidationError(
                    "Invalid emails",
                    ["Email IDs cannot be empty"]
                )
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Applied filter {filter_name}",
                data={"applied_count": len(email_ids)}
            )
        except ValidationError as e:
            return APIResponse(
                status=e.status,
                message=e.message,
                errors=getattr(e, 'errors', [])
            )
    
    def get_labels(self) -> APIResponse:
        """Get labels endpoint."""
        try:
            labels = [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "SENT", "name": "SENT"},
                {"id": "DRAFT", "name": "DRAFT"},
            ]
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="Labels retrieved",
                data={"labels": labels, "count": len(labels)}
            )
        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="Failed to get labels"
            )
    
    def create_filter(self, name: str, conditions: Dict) -> APIResponse:
        """Create filter endpoint."""
        try:
            if not name:
                raise ValidationError(
                    "Invalid filter name",
                    ["Name cannot be empty"]
                )
            
            if not conditions:
                raise ValidationError(
                    "Invalid conditions",
                    ["Conditions cannot be empty"]
                )
            
            filter_id = f"filter_{datetime.now().timestamp()}"
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="Filter created",
                data={"filter_id": filter_id, "name": name}
            )
        except ValidationError as e:
            return APIResponse(
                status=e.status,
                message=e.message,
                errors=getattr(e, 'errors', [])
            )
    
    def get_stats(self) -> APIResponse:
        """Get statistics endpoint."""
        try:
            stats = {
                "total_emails": 1000,
                "unread_emails": 42,
                "total_threads": 500,
                "starred_emails": 15,
                "api_calls_today": 500
            }
            
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message="Statistics retrieved",
                data=stats
            )
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="Failed to get statistics"
            )


class APIRouter:
    """Route API requests to handlers."""
    
    def __init__(self):
        """Initialize router."""
        self.api = GmailAPI()
        self.routes = {
            "GET /emails": self.api.get_emails,
            "POST /emails": self.api.send_email,
            "DELETE /emails/{id}": self.api.delete_email,
            "POST /filters": self.api.create_filter,
            "GET /labels": self.api.get_labels,
            "GET /stats": self.api.get_stats,
        }
    
    def route(self, method: str, path: str, params: Dict = None) -> APIResponse:
        """Route request to handler."""
        route_key = f"{method} {path}"
        
        if route_key not in self.routes:
            return APIResponse(
                status=ResponseStatus.NOT_FOUND,
                message=f"Route not found: {route_key}"
            )
        
        handler = self.routes[route_key]
        params = params or {}
        
        try:
            return handler(**params)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return APIResponse(
                status=ResponseStatus.ERROR,
                message="Internal server error"
            )
