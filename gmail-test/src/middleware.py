"""Advanced configuration and middleware."""

import logging
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting middleware."""
    
    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter."""
        self.requests_per_minute = requests_per_minute
        self.request_times: Dict[str, List[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        minute_ago = now - 60
        
        if key not in self.request_times:
            self.request_times[key] = []
        
        # Remove old requests
        self.request_times[key] = [t for t in self.request_times[key] if t > minute_ago]
        
        if len(self.request_times[key]) < self.requests_per_minute:
            self.request_times[key].append(now)
            return True
        
        return False
    
    def get_reset_time(self, key: str) -> float:
        """Get when rate limit resets."""
        if key not in self.request_times or not self.request_times[key]:
            return 0
        
        oldest_request = min(self.request_times[key])
        reset_time = oldest_request + 60
        return max(0, reset_time - time.time())


class AuthenticationMiddleware:
    """Authentication middleware."""
    
    def __init__(self):
        """Initialize auth middleware."""
        self.tokens: Dict[str, Dict] = {}
        self.token_expiry: Dict[str, float] = {}
    
    def register_token(self, token: str, user_id: str, expires_in: int = 3600) -> None:
        """Register authentication token."""
        self.tokens[token] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        self.token_expiry[token] = time.time() + expires_in
        logger.debug(f"Registered token for user {user_id}")
    
    def validate_token(self, token: str) -> bool:
        """Validate authentication token."""
        if token not in self.tokens:
            return False
        
        if time.time() > self.token_expiry.get(token, 0):
            del self.tokens[token]
            return False
        
        return True
    
    def get_user_id(self, token: str) -> Optional[str]:
        """Get user ID from token."""
        if self.validate_token(token):
            return self.tokens[token]["user_id"]
        return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke token."""
        if token in self.tokens:
            del self.tokens[token]
            if token in self.token_expiry:
                del self.token_expiry[token]
            logger.debug(f"Revoked token")
            return True
        return False


class CachingMiddleware:
    """Caching middleware for request results."""
    
    def __init__(self, ttl_seconds: int = 300):
        """Initialize caching middleware."""
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self.ttl_seconds = ttl_seconds
    
    def get_cache_key(self, method: str, path: str, params: Dict) -> str:
        """Generate cache key from request."""
        import hashlib
        key_str = f"{method}:{path}:{str(params)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def set_cache(self, key: str, value: Any) -> None:
        """Set cached value."""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get cached value if valid."""
        if key not in self.cache:
            return None
        
        if time.time() - self.timestamps[key] > self.ttl_seconds:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        return self.cache[key]
    
    def clear_cache(self) -> None:
        """Clear all cache."""
        self.cache.clear()
        self.timestamps.clear()


class LoggingMiddleware:
    """Logging middleware."""
    
    def __init__(self):
        """Initialize logging middleware."""
        self.request_log: List[Dict] = []
    
    def log_request(self, method: str, path: str, user_id: Optional[str] = None) -> None:
        """Log incoming request."""
        log_entry = {
            "method": method,
            "path": path,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        self.request_log.append(log_entry)
        logger.info(f"Request: {method} {path}")
    
    def log_response(self, status: str, response_time: float) -> None:
        """Log response."""
        logger.info(f"Response: {status} ({response_time:.3f}s)")
    
    def get_request_log(self, limit: int = 100) -> List[Dict]:
        """Get request log."""
        return self.request_log[-limit:]


class MiddlewarePipeline:
    """Pipeline for managing middleware."""
    
    def __init__(self):
        """Initialize middleware pipeline."""
        self.middleware: List[Callable] = []
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to pipeline."""
        self.middleware.append(middleware)
        logger.debug(f"Added middleware: {middleware.__class__.__name__}")
    
    def execute(self, func: Callable) -> Callable:
        """Execute middleware pipeline."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Execute middleware
            for mw in self.middleware:
                # Dummy middleware execution
                pass
            
            return func(*args, **kwargs)
        
        return wrapper


class ErrorHandler:
    """Error handling middleware."""
    
    def __init__(self):
        """Initialize error handler."""
        self.error_handlers: Dict[type, Callable] = {}
        self.error_log: List[Dict] = []
    
    def register_handler(self, exception_type: type, handler: Callable) -> None:
        """Register error handler."""
        self.error_handlers[exception_type] = handler
        logger.debug(f"Registered handler for {exception_type.__name__}")
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle error."""
        error_entry = {
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        self.error_log.append(error_entry)
        
        handler = self.error_handlers.get(type(error))
        if handler:
            return handler(error)
        
        return {"error": str(error), "status": "error"}
    
    def get_error_log(self) -> List[Dict]:
        """Get error log."""
        return self.error_log.copy()


class RequestValidator:
    """Validate incoming requests."""
    
    def __init__(self):
        """Initialize request validator."""
        self.validation_rules: Dict[str, List[Callable]] = {}
    
    def add_rule(self, endpoint: str, rule: Callable) -> None:
        """Add validation rule."""
        if endpoint not in self.validation_rules:
            self.validation_rules[endpoint] = []
        
        self.validation_rules[endpoint].append(rule)
    
    def validate(self, endpoint: str, data: Dict) -> Tuple[bool, List[str]]:
        """Validate request data."""
        errors = []
        
        if endpoint not in self.validation_rules:
            return True, []
        
        for rule in self.validation_rules[endpoint]:
            try:
                if not rule(data):
                    errors.append(f"Validation rule failed: {rule.__name__}")
            except Exception as e:
                errors.append(f"Validation error: {str(e)}")
        
        return len(errors) == 0, errors


class ResponseFormatter:
    """Format API responses."""
    
    @staticmethod
    def success(data: Any, message: str = "Success") -> Dict:
        """Format success response."""
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def error(message: str, errors: List[str] = None) -> Dict:
        """Format error response."""
        return {
            "status": "error",
            "message": message,
            "errors": errors or [],
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def paginated(items: List, page: int, per_page: int, total: int) -> Dict:
        """Format paginated response."""
        return {
            "status": "success",
            "data": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }


class SecurityHeaders:
    """Security headers middleware."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }


class InputSanitizer:
    """Sanitize user input."""
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not isinstance(input_str, str):
            return ""
        
        # Remove dangerous characters
        sanitized = input_str.replace("<", "&lt;").replace(">", "&gt;")
        sanitized = sanitized.replace("\"", "&quot;").replace("'", "&#x27;")
        
        # Limit length
        return sanitized[:max_length]
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email input."""
        return InputSanitizer.sanitize_string(email, 254)
    
    @staticmethod
    def sanitize_dict(data: Dict) -> Dict:
        """Sanitize dictionary."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            else:
                sanitized[key] = value
        
        return sanitized
