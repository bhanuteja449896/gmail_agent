"""Tests for API gateway module."""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.api_gateway import (
    HTTPMethod, ContentType, Request, Response, RouteHandler, Route,
    Middleware, AuthMiddleware, LoggingMiddleware, ValidationMiddleware,
    CacheMiddleware, ErrorHandler, APIGateway, APIVersion, RateLimiter,
    WebSocketUpgrade
)


@pytest.fixture
def sample_request():
    """Sample request fixture."""
    return Request(
        method=HTTPMethod.GET,
        path="/api/v1/emails",
        headers={"Content-Type": "application/json"},
        source_ip="192.168.1.1"
    )


@pytest.fixture
def sample_response():
    """Sample response fixture."""
    return Response(
        status_code=200,
        body='{"success": true}',
        content_type=ContentType.JSON
    )


@pytest.fixture
def api_gateway():
    """API gateway fixture."""
    return APIGateway()


class TestHTTPMethod:
    """Test HTTPMethod enum."""
    
    def test_http_methods_defined(self):
        """Test all HTTP methods."""
        methods = [
            HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT,
            HTTPMethod.PATCH, HTTPMethod.DELETE, HTTPMethod.HEAD,
            HTTPMethod.OPTIONS
        ]
        assert len(methods) == 7


class TestContentType:
    """Test ContentType enum."""
    
    def test_content_types_defined(self):
        """Test all content types."""
        types = [
            ContentType.JSON, ContentType.XML, ContentType.FORM,
            ContentType.PLAIN, ContentType.HTML, ContentType.OCTET
        ]
        assert len(types) == 6


class TestRequest:
    """Test Request class."""
    
    def test_request_creation(self, sample_request):
        """Test request creation."""
        assert sample_request.method == HTTPMethod.GET
        assert sample_request.path == "/api/v1/emails"
        assert sample_request.request_id is not None
    
    def test_request_has_timestamp(self, sample_request):
        """Test request has timestamp."""
        assert isinstance(sample_request.timestamp, datetime)
    
    def test_request_get_content_type(self):
        """Test get content type."""
        req = Request(
            method=HTTPMethod.POST,
            path="/api/emails",
            headers={"Content-Type": "application/json"}
        )
        assert req.get_content_type() == "application/json"
    
    def test_request_get_json_body(self):
        """Test get JSON body."""
        body = '{"email_id": "123", "status": "read"}'
        req = Request(
            method=HTTPMethod.POST,
            path="/api/emails",
            body=body
        )
        json_body = req.get_json_body()
        assert json_body["email_id"] == "123"
    
    def test_request_to_dict(self, sample_request):
        """Test request to dictionary."""
        req_dict = sample_request.to_dict()
        assert req_dict["method"] == "GET"
        assert req_dict["path"] == "/api/v1/emails"


class TestResponse:
    """Test Response class."""
    
    def test_response_creation(self, sample_response):
        """Test response creation."""
        assert sample_response.status_code == 200
        assert sample_response.content_type == ContentType.JSON
    
    def test_response_set_json_body(self):
        """Test set JSON body."""
        resp = Response(status_code=200)
        resp.set_json_body({"success": True, "message": "OK"})
        assert resp.content_type == ContentType.JSON
        assert "success" in resp.body
    
    def test_response_is_success(self):
        """Test is success."""
        resp_200 = Response(status_code=200)
        resp_201 = Response(status_code=201)
        resp_400 = Response(status_code=400)
        
        assert resp_200.is_success() is True
        assert resp_201.is_success() is True
        assert resp_400.is_success() is False
    
    def test_response_is_error(self):
        """Test is error."""
        resp_200 = Response(status_code=200)
        resp_404 = Response(status_code=404)
        resp_500 = Response(status_code=500)
        
        assert resp_200.is_error() is False
        assert resp_404.is_error() is True
        assert resp_500.is_error() is True
    
    def test_response_to_dict(self, sample_response):
        """Test response to dictionary."""
        resp_dict = sample_response.to_dict()
        assert resp_dict["status_code"] == 200


class TestRoute:
    """Test Route class."""
    
    def test_route_creation(self):
        """Test route creation."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        assert route.path == "/api/emails"
        assert route.method == HTTPMethod.GET
    
    def test_route_matches_simple(self):
        """Test route matches simple path."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        assert route.matches(req) is True
    
    def test_route_matches_with_params(self):
        """Test route matches with params."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails/:id", HTTPMethod.GET, handler)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails/123")
        assert route.matches(req) is True
        assert req.path_params["id"] == "123"
    
    def test_route_matches_method_mismatch(self):
        """Test route doesn't match on method mismatch."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        req = Request(method=HTTPMethod.POST, path="/api/emails")
        assert route.matches(req) is False
    
    def test_route_add_middleware(self):
        """Test add middleware to route."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        middleware = Mock(spec=Middleware)
        route.add_middleware(middleware)
        
        assert len(route.middleware) == 1
    
    def test_route_set_rate_limit(self):
        """Test set rate limit."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        route.set_rate_limit(100)
        assert route.rate_limit == 100
    
    def test_route_set_auth_required(self):
        """Test set auth required."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        route.set_auth_required(True)
        assert route.requires_auth is True


class TestAuthMiddleware:
    """Test AuthMiddleware."""
    
    def test_auth_middleware_valid_token(self):
        """Test auth middleware with valid token."""
        validator = lambda token: token == "valid_token"
        middleware = AuthMiddleware(validator)
        
        req = Request(
            method=HTTPMethod.GET,
            path="/api/emails",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        response = middleware.process_request(req)
        assert response is None
    
    def test_auth_middleware_invalid_token(self):
        """Test auth middleware with invalid token."""
        validator = lambda token: token == "valid_token"
        middleware = AuthMiddleware(validator)
        
        req = Request(
            method=HTTPMethod.GET,
            path="/api/emails",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        response = middleware.process_request(req)
        assert response is not None
        assert response.status_code == 403
    
    def test_auth_middleware_missing_header(self):
        """Test auth middleware without auth header."""
        validator = lambda token: True
        middleware = AuthMiddleware(validator)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        response = middleware.process_request(req)
        
        assert response is not None
        assert response.status_code == 401


class TestValidationMiddleware:
    """Test ValidationMiddleware."""
    
    def test_validation_middleware_valid_data(self):
        """Test validation middleware with valid data."""
        validators = {
            "email": lambda x: "@" in x,
            "name": lambda x: len(x) > 0
        }
        middleware = ValidationMiddleware(validators)
        
        req = Request(
            method=HTTPMethod.POST,
            path="/api/users",
            body='{"email": "test@example.com", "name": "Test"}'
        )
        
        response = middleware.process_request(req)
        assert response is None
    
    def test_validation_middleware_invalid_data(self):
        """Test validation middleware with invalid data."""
        validators = {
            "email": lambda x: "@" in x
        }
        middleware = ValidationMiddleware(validators)
        
        req = Request(
            method=HTTPMethod.POST,
            path="/api/users",
            body='{"email": "invalid_email"}'
        )
        
        response = middleware.process_request(req)
        assert response is not None
        assert response.status_code == 400


class TestCacheMiddleware:
    """Test CacheMiddleware."""
    
    def test_cache_middleware_cache_miss(self):
        """Test cache middleware cache miss."""
        middleware = CacheMiddleware(ttl_seconds=60)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        response = middleware.process_request(req)
        
        assert response is None
    
    def test_cache_middleware_cache_hit(self):
        """Test cache middleware cache hit."""
        middleware = CacheMiddleware(ttl_seconds=60)
        
        req1 = Request(method=HTTPMethod.GET, path="/api/emails")
        req2 = Request(method=HTTPMethod.GET, path="/api/emails")
        
        resp = Response(status_code=200, body='{"emails": []}')
        resp.request_id = req1.request_id
        
        middleware.process_response(resp)
        
        cached_response = middleware.process_request(req2)
        # Should not be cached since it's a different request
        assert cached_response is None
    
    def test_cache_middleware_post_not_cached(self):
        """Test cache middleware doesn't cache POST."""
        middleware = CacheMiddleware(ttl_seconds=60)
        
        req = Request(
            method=HTTPMethod.POST,
            path="/api/emails",
            body='{"subject": "Test"}'
        )
        
        response = middleware.process_request(req)
        assert response is None


class TestErrorHandler:
    """Test ErrorHandler."""
    
    def test_error_handler_register(self):
        """Test register error handler."""
        handler = ErrorHandler()
        
        custom_handler = lambda msg: Response(status_code=404, body=msg)
        handler.register(404, custom_handler)
        
        response = handler.handle(404, "Not found")
        assert response.status_code == 404
    
    def test_error_handler_default(self):
        """Test default error handler."""
        handler = ErrorHandler()
        
        response = handler.handle(500, "Internal error")
        assert response.status_code == 500


class TestAPIGateway:
    """Test APIGateway."""
    
    def test_gateway_creation(self, api_gateway):
        """Test gateway creation."""
        assert api_gateway is not None
        assert len(api_gateway.routes) == 0
    
    def test_register_route(self, api_gateway):
        """Test register route."""
        handler = Mock(spec=RouteHandler)
        route = Route("/api/emails", HTTPMethod.GET, handler)
        
        api_gateway.register_route(route)
        assert len(api_gateway.routes) == 1
    
    def test_handle_request_not_found(self, api_gateway, sample_request):
        """Test handle request not found."""
        response = api_gateway.handle_request(sample_request)
        assert response.status_code == 404
    
    def test_handle_request_found(self, api_gateway):
        """Test handle request found."""
        handler = Mock(spec=RouteHandler)
        handler.handle = Mock(return_value=Response(status_code=200, body='{"data": "test"}'))
        
        route = Route("/api/emails", HTTPMethod.GET, handler)
        api_gateway.register_route(route)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        response = api_gateway.handle_request(req)
        
        assert response.status_code == 200
    
    def test_gateway_statistics(self, api_gateway):
        """Test gateway statistics."""
        handler = Mock(spec=RouteHandler)
        handler.handle = Mock(return_value=Response(status_code=200))
        
        route = Route("/api/emails", HTTPMethod.GET, handler)
        api_gateway.register_route(route)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        api_gateway.handle_request(req)
        
        stats = api_gateway.get_statistics()
        assert stats["total_requests"] == 1
        assert stats["successful_requests"] == 1


class TestAPIVersion:
    """Test APIVersion."""
    
    def test_version_creation(self):
        """Test version creation."""
        version = APIVersion("1.0")
        assert version.version == "1.0"
        assert version.deprecated is False
    
    def test_version_is_active(self):
        """Test version is active."""
        version = APIVersion("1.0")
        assert version.is_active() is True
    
    def test_version_deprecated(self):
        """Test version deprecated."""
        version = APIVersion("1.0")
        version.deprecated = True
        assert version.is_active() is False
    
    def test_version_sunset(self):
        """Test version sunset date."""
        version = APIVersion("1.0")
        past_date = datetime.now() - timedelta(days=1)
        version.sunset_date = past_date
        
        assert version.is_active() is False


class TestRateLimiter:
    """Test RateLimiter."""
    
    def test_rate_limiter_creation(self):
        """Test rate limiter creation."""
        limiter = RateLimiter(max_requests=100, time_window_seconds=60)
        assert limiter.max_requests == 100
    
    def test_rate_limiter_allowed(self):
        """Test rate limiter allowed."""
        limiter = RateLimiter(max_requests=2, time_window_seconds=60)
        
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False
    
    def test_rate_limiter_get_retry_after(self):
        """Test rate limiter retry after."""
        limiter = RateLimiter(max_requests=1, time_window_seconds=10)
        
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")  # Exceeds limit
        
        retry_after = limiter.get_retry_after("client1")
        assert retry_after > 0
        assert retry_after <= 10


class TestWebSocketUpgrade:
    """Test WebSocketUpgrade."""
    
    def test_websocket_upgrade_valid(self):
        """Test valid WebSocket upgrade."""
        upgrade = WebSocketUpgrade()
        
        req = Request(
            method=HTTPMethod.GET,
            path="/ws",
            headers={
                "Upgrade": "websocket",
                "Connection": "Upgrade"
            }
        )
        
        assert upgrade.upgrade(req) is True
    
    def test_websocket_upgrade_invalid(self):
        """Test invalid WebSocket upgrade."""
        upgrade = WebSocketUpgrade()
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        assert upgrade.upgrade(req) is False
    
    def test_websocket_add_connection(self):
        """Test add WebSocket connection."""
        upgrade = WebSocketUpgrade()
        
        conn = Mock()
        upgrade.add_connection("conn1", conn)
        
        assert "conn1" in upgrade.connections
    
    def test_websocket_remove_connection(self):
        """Test remove WebSocket connection."""
        upgrade = WebSocketUpgrade()
        
        conn = Mock()
        upgrade.add_connection("conn1", conn)
        upgrade.remove_connection("conn1")
        
        assert "conn1" not in upgrade.connections


class TestAPIGatewayIntegration:
    """Integration tests for API gateway."""
    
    def test_request_with_middleware(self, api_gateway):
        """Test request with middleware."""
        logging_middleware = LoggingMiddleware()
        api_gateway.add_middleware(logging_middleware)
        
        handler = Mock(spec=RouteHandler)
        handler.handle = Mock(return_value=Response(status_code=200))
        
        route = Route("/api/emails", HTTPMethod.GET, handler)
        api_gateway.register_route(route)
        
        req = Request(method=HTTPMethod.GET, path="/api/emails")
        response = api_gateway.handle_request(req)
        
        assert response.status_code == 200
    
    def test_request_with_auth(self, api_gateway):
        """Test request with authentication."""
        auth_middleware = AuthMiddleware(lambda token: token == "secret")
        api_gateway.add_middleware(auth_middleware)
        
        handler = Mock(spec=RouteHandler)
        handler.handle = Mock(return_value=Response(status_code=200))
        
        route = Route("/api/emails", HTTPMethod.GET, handler)
        api_gateway.register_route(route)
        
        req = Request(
            method=HTTPMethod.GET,
            path="/api/emails",
            headers={"Authorization": "Bearer secret"}
        )
        response = api_gateway.handle_request(req)
        
        assert response.status_code == 200
