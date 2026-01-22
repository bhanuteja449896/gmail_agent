"""API Gateway and REST request/response handling."""

import logging
from typing import Any, Dict, List, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field as dataclass_field
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import json
import hashlib
import uuid

logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ContentType(Enum):
    """Content types."""
    JSON = "application/json"
    XML = "application/xml"
    FORM = "application/x-www-form-urlencoded"
    PLAIN = "text/plain"
    HTML = "text/html"
    OCTET = "application/octet-stream"


@dataclass
class Request:
    """HTTP Request."""
    method: HTTPMethod
    path: str
    headers: Dict[str, str] = dataclass_field(default_factory=dict)
    body: Optional[str] = None
    query_params: Dict[str, str] = dataclass_field(default_factory=dict)
    path_params: Dict[str, str] = dataclass_field(default_factory=dict)
    request_id: str = dataclass_field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = dataclass_field(default_factory=datetime.now)
    source_ip: str = "127.0.0.1"
    user_agent: str = ""
    
    def get_content_type(self) -> Optional[str]:
        """Get content type from headers."""
        return self.headers.get("Content-Type")
    
    def get_json_body(self) -> Optional[Dict]:
        """Parse JSON body."""
        if self.body:
            try:
                return json.loads(self.body)
            except:
                return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "method": self.method.value,
            "path": self.path,
            "timestamp": self.timestamp.isoformat(),
            "source_ip": self.source_ip
        }


@dataclass
class Response:
    """HTTP Response."""
    status_code: int
    body: Optional[str] = None
    headers: Dict[str, str] = dataclass_field(default_factory=dict)
    content_type: ContentType = ContentType.JSON
    request_id: str = ""
    timestamp: datetime = dataclass_field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    
    def set_json_body(self, data: Dict[str, Any]) -> None:
        """Set JSON response body."""
        self.body = json.dumps(data)
        self.content_type = ContentType.JSON
        self.headers["Content-Type"] = ContentType.JSON.value
    
    def is_success(self) -> bool:
        """Check if response is successful."""
        return 200 <= self.status_code < 300
    
    def is_error(self) -> bool:
        """Check if response is error."""
        return self.status_code >= 400
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status_code": self.status_code,
            "content_type": self.content_type.value,
            "response_time_ms": self.response_time_ms,
            "request_id": self.request_id
        }


class RouteHandler(ABC):
    """Abstract route handler."""
    
    @abstractmethod
    def handle(self, request: Request) -> Response:
        """Handle request."""
        pass
    
    @abstractmethod
    def can_handle(self, request: Request) -> bool:
        """Check if handler can handle request."""
        pass


class Route:
    """Route definition."""
    
    def __init__(self, path: str, method: HTTPMethod, handler: RouteHandler):
        """Initialize route."""
        self.path = path
        self.method = method
        self.handler = handler
        self.middleware: List['Middleware'] = []
        self.rate_limit: Optional[int] = None
        self.requires_auth = False
        self.description = ""
    
    def add_middleware(self, middleware: 'Middleware') -> 'Route':
        """Add middleware."""
        self.middleware.append(middleware)
        return self
    
    def set_rate_limit(self, requests_per_minute: int) -> 'Route':
        """Set rate limit."""
        self.rate_limit = requests_per_minute
        return self
    
    def set_auth_required(self, required: bool) -> 'Route':
        """Set auth requirement."""
        self.requires_auth = required
        return self
    
    def matches(self, request: Request) -> bool:
        """Check if route matches request."""
        if request.method != self.method:
            return False
        
        # Simple path matching (can be enhanced with regex)
        path_parts = request.path.split('/')
        route_parts = self.path.split('/')
        
        if len(path_parts) != len(route_parts):
            return False
        
        for path_part, route_part in zip(path_parts, route_parts):
            if route_part.startswith(':'):
                param_name = route_part[1:]
                request.path_params[param_name] = path_part
            elif path_part != route_part:
                return False
        
        return True


class Middleware(ABC):
    """Abstract middleware."""
    
    @abstractmethod
    def process_request(self, request: Request) -> Optional[Response]:
        """Process request."""
        pass
    
    @abstractmethod
    def process_response(self, response: Response) -> Response:
        """Process response."""
        pass


class AuthMiddleware(Middleware):
    """Authentication middleware."""
    
    def __init__(self, token_validator: Callable[[str], bool]):
        """Initialize middleware."""
        self.token_validator = token_validator
    
    def process_request(self, request: Request) -> Optional[Response]:
        """Process request."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response(
                status_code=401,
                body="Missing authorization header"
            )
        
        try:
            token = auth_header.replace("Bearer ", "")
            if not self.token_validator(token):
                return Response(
                    status_code=403,
                    body="Invalid token"
                )
        except:
            return Response(
                status_code=401,
                body="Invalid authorization"
            )
        
        return None
    
    def process_response(self, response: Response) -> Response:
        """Process response."""
        return response


class LoggingMiddleware(Middleware):
    """Logging middleware."""
    
    def process_request(self, request: Request) -> Optional[Response]:
        """Process request."""
        logger.info(f"Request: {request.method.value} {request.path}")
        return None
    
    def process_response(self, response: Response) -> Response:
        """Process response."""
        logger.info(f"Response: {response.status_code}")
        return response


class ValidationMiddleware(Middleware):
    """Validation middleware."""
    
    def __init__(self, validators: Dict[str, Callable]):
        """Initialize middleware."""
        self.validators = validators
    
    def process_request(self, request: Request) -> Optional[Response]:
        """Process request."""
        if request.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
            body = request.get_json_body()
            if body:
                for field, validator in self.validators.items():
                    if field in body:
                        if not validator(body[field]):
                            return Response(
                                status_code=400,
                                body=f"Invalid {field}"
                            )
        return None
    
    def process_response(self, response: Response) -> Response:
        """Process response."""
        return response


class CacheMiddleware(Middleware):
    """Response caching middleware."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize middleware."""
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Response, datetime]] = {}
    
    def process_request(self, request: Request) -> Optional[Response]:
        """Process request."""
        if request.method != HTTPMethod.GET:
            return None
        
        cache_key = self._get_cache_key(request)
        if cache_key in self.cache:
            response, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.ttl_seconds:
                logger.info("Cache hit")
                return response
            else:
                del self.cache[cache_key]
        
        return None
    
    def process_response(self, response: Response) -> Response:
        """Process response."""
        if response.is_success():
            cache_key = self._get_cache_key(response)
            self.cache[cache_key] = (response, datetime.now())
        return response
    
    def _get_cache_key(self, obj) -> str:
        """Generate cache key."""
        if isinstance(obj, Request):
            key = f"{obj.method.value}:{obj.path}"
        else:
            key = f"response:{obj.request_id}"
        return hashlib.md5(key.encode()).hexdigest()


class ErrorHandler:
    """Error handler."""
    
    def __init__(self):
        """Initialize error handler."""
        self.handlers: Dict[int, Callable] = {}
    
    def register(self, status_code: int, handler: Callable) -> None:
        """Register error handler."""
        self.handlers[status_code] = handler
    
    def handle(self, status_code: int, error: str) -> Response:
        """Handle error."""
        if status_code in self.handlers:
            return self.handlers[status_code](error)
        
        return Response(
            status_code=status_code,
            body=json.dumps({"error": error})
        )


class APIGateway:
    """API Gateway."""
    
    def __init__(self):
        """Initialize gateway."""
        self.routes: List[Route] = []
        self.middleware: List[Middleware] = []
        self.error_handler = ErrorHandler()
        self.request_log: List[Request] = []
        self.response_log: List[Response] = []
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0.0
        }
    
    def register_route(self, route: Route) -> None:
        """Register route."""
        self.routes.append(route)
        logger.info(f"Registered route: {route.method.value} {route.path}")
    
    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware."""
        self.middleware.append(middleware)
    
    def handle_request(self, request: Request) -> Response:
        """Handle request."""
        import time
        start_time = time.time()
        
        try:
            # Process through global middleware
            for middleware in self.middleware:
                response = middleware.process_request(request)
                if response:
                    return response
            
            # Find matching route
            matching_route = None
            for route in self.routes:
                if route.matches(request):
                    matching_route = route
                    break
            
            if not matching_route:
                return Response(status_code=404, body="Route not found")
            
            # Process through route middleware
            for middleware in matching_route.middleware:
                response = middleware.process_request(request)
                if response:
                    return response
            
            # Handle request
            response = matching_route.handler.handle(request)
            
            # Process through middleware responses
            for middleware in reversed(self.middleware + matching_route.middleware):
                response = middleware.process_response(response)
            
            response.request_id = request.request_id
            response.response_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(response)
            
            return response
        
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self.error_handler.handle(500, str(e))
    
    def _update_stats(self, response: Response) -> None:
        """Update statistics."""
        self.stats["total_requests"] += 1
        if response.is_success():
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.stats.copy()


class APIVersion:
    """API version management."""
    
    def __init__(self, version: str):
        """Initialize version."""
        self.version = version
        self.routes: Dict[str, Route] = {}
        self.deprecated = False
        self.sunset_date: Optional[datetime] = None
    
    def add_route(self, path: str, route: Route) -> None:
        """Add route."""
        key = f"{route.method.value}:{path}"
        self.routes[key] = route
    
    def is_active(self) -> bool:
        """Check if version is active."""
        if self.sunset_date:
            return datetime.now() < self.sunset_date
        return not self.deprecated
    
    def get_routes(self) -> List[Route]:
        """Get routes."""
        return list(self.routes.values())


class RateLimiter:
    """Rate limiter."""
    
    def __init__(self, max_requests: int, time_window_seconds: int):
        """Initialize limiter."""
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self.requests: Dict[str, List[datetime]] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed."""
        now = datetime.now()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        cutoff = now - timedelta(seconds=self.time_window)
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if ts > cutoff
        ]
        
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(now)
            return True
        
        return False
    
    def get_retry_after(self, client_id: str) -> int:
        """Get retry-after seconds."""
        if client_id in self.requests and self.requests[client_id]:
            oldest = self.requests[client_id][0]
            retry_after = self.time_window - (datetime.now() - oldest).total_seconds()
            return max(1, int(retry_after))
        return self.time_window


class WebSocketUpgrade:
    """WebSocket upgrade support."""
    
    def __init__(self):
        """Initialize upgrade."""
        self.connections: Dict[str, Any] = {}
    
    def upgrade(self, request: Request) -> bool:
        """Upgrade connection."""
        upgrade_header = request.headers.get("Upgrade", "").lower()
        connection_header = request.headers.get("Connection", "").lower()
        
        if upgrade_header == "websocket" and "upgrade" in connection_header:
            logger.info("WebSocket upgrade")
            return True
        
        return False
    
    def add_connection(self, connection_id: str, connection: Any) -> None:
        """Add connection."""
        self.connections[connection_id] = connection
    
    def remove_connection(self, connection_id: str) -> None:
        """Remove connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
    
    def broadcast(self, message: str) -> None:
        """Broadcast message to all connections."""
        for conn in self.connections.values():
            conn.send(message)
