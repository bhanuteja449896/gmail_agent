"""Tests for middleware module."""

import pytest
import sys
import time
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.middleware import (
    RateLimiter, AuthenticationMiddleware, CachingMiddleware,
    LoggingMiddleware, ErrorHandler, RequestValidator,
    ResponseFormatter, SecurityHeaders, InputSanitizer
)


class TestRateLimiter:
    """Test suite for RateLimiter."""
    
    @pytest.fixture
    def limiter(self):
        """Create rate limiter."""
        return RateLimiter(requests_per_minute=10)
    
    def test_rate_limiter_initialization(self, limiter):
        """Test initialization."""
        assert limiter.requests_per_minute == 10
    
    def test_request_allowed(self, limiter):
        """Test allowing requests."""
        assert limiter.is_allowed("user_1") is True
    
    def test_rate_limit_exceeded(self, limiter):
        """Test rate limit exceeded."""
        limiter_strict = RateLimiter(requests_per_minute=2)
        
        assert limiter_strict.is_allowed("user") is True
        assert limiter_strict.is_allowed("user") is True
        assert limiter_strict.is_allowed("user") is False
    
    def test_get_reset_time(self, limiter):
        """Test getting reset time."""
        limiter.is_allowed("user")
        reset_time = limiter.get_reset_time("user")
        assert reset_time >= 0


class TestAuthenticationMiddleware:
    """Test suite for AuthenticationMiddleware."""
    
    @pytest.fixture
    def auth(self):
        """Create auth middleware."""
        return AuthenticationMiddleware()
    
    def test_register_token(self, auth):
        """Test registering token."""
        auth.register_token("token_123", "user_1")
        assert "token_123" in auth.tokens
    
    def test_validate_token(self, auth):
        """Test validating token."""
        auth.register_token("token_123", "user_1")
        assert auth.validate_token("token_123") is True
    
    def test_validate_invalid_token(self, auth):
        """Test validating invalid token."""
        assert auth.validate_token("invalid") is False
    
    def test_get_user_id(self, auth):
        """Test getting user ID."""
        auth.register_token("token_123", "user_1")
        user_id = auth.get_user_id("token_123")
        assert user_id == "user_1"
    
    def test_revoke_token(self, auth):
        """Test revoking token."""
        auth.register_token("token_123", "user_1")
        assert auth.revoke_token("token_123") is True
        assert auth.validate_token("token_123") is False


class TestCachingMiddleware:
    """Test suite for CachingMiddleware."""
    
    @pytest.fixture
    def cache(self):
        """Create caching middleware."""
        return CachingMiddleware(ttl_seconds=10)
    
    def test_cache_operations(self, cache):
        """Test cache set and get."""
        key = "test_key"
        value = {"data": "test"}
        
        cache.set_cache(key, value)
        retrieved = cache.get_cache(key)
        assert retrieved == value
    
    def test_cache_expiry(self, cache):
        """Test cache expiration."""
        cache_short = CachingMiddleware(ttl_seconds=0)
        cache_short.set_cache("key", "value")
        time.sleep(0.1)
        assert cache_short.get_cache("key") is None
    
    def test_clear_cache(self, cache):
        """Test clearing cache."""
        cache.set_cache("key1", "value1")
        cache.set_cache("key2", "value2")
        cache.clear_cache()
        assert cache.get_cache("key1") is None


class TestLoggingMiddleware:
    """Test suite for LoggingMiddleware."""
    
    @pytest.fixture
    def logger_mw(self):
        """Create logging middleware."""
        return LoggingMiddleware()
    
    def test_log_request(self, logger_mw):
        """Test logging request."""
        logger_mw.log_request("GET", "/emails", "user_1")
        log = logger_mw.get_request_log()
        assert len(log) == 1
        assert log[0]["method"] == "GET"
    
    def test_get_request_log(self, logger_mw):
        """Test getting request log."""
        logger_mw.log_request("GET", "/emails")
        logger_mw.log_request("POST", "/emails")
        log = logger_mw.get_request_log()
        assert len(log) == 2


class TestErrorHandler:
    """Test suite for ErrorHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create error handler."""
        return ErrorHandler()
    
    def test_register_handler(self, handler):
        """Test registering error handler."""
        def value_error_handler(e):
            return {"error": "value_error"}
        
        handler.register_handler(ValueError, value_error_handler)
        assert ValueError in handler.error_handlers
    
    def test_handle_error(self, handler):
        """Test handling error."""
        result = handler.handle_error(Exception("Test error"))
        assert "error" in result
    
    def test_error_log(self, handler):
        """Test error logging."""
        handler.handle_error(Exception("Error 1"))
        handler.handle_error(Exception("Error 2"))
        log = handler.get_error_log()
        assert len(log) == 2


class TestRequestValidator:
    """Test suite for RequestValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create request validator."""
        return RequestValidator()
    
    def test_add_and_validate_rule(self, validator):
        """Test adding and validating rule."""
        def check_email(data):
            return "@" in data.get("email", "")
        
        validator.add_rule("/emails", check_email)
        
        valid, errors = validator.validate("/emails", {"email": "user@example.com"})
        assert valid is True
    
    def test_validation_failure(self, validator):
        """Test validation failure."""
        def check_required(data):
            return "id" in data
        
        validator.add_rule("/test", check_required)
        
        valid, errors = validator.validate("/test", {})
        assert valid is False


class TestResponseFormatter:
    """Test suite for ResponseFormatter."""
    
    def test_success_response(self):
        """Test success response format."""
        response = ResponseFormatter.success({"data": "test"})
        assert response["status"] == "success"
        assert "data" in response
    
    def test_error_response(self):
        """Test error response format."""
        response = ResponseFormatter.error("Error occurred", ["error1"])
        assert response["status"] == "error"
        assert "message" in response
    
    def test_paginated_response(self):
        """Test paginated response format."""
        response = ResponseFormatter.paginated([1, 2, 3], 1, 10, 25)
        assert "pagination" in response
        assert response["pagination"]["page"] == 1


class TestSecurityHeaders:
    """Test suite for SecurityHeaders."""
    
    def test_get_security_headers(self):
        """Test getting security headers."""
        headers = SecurityHeaders.get_security_headers()
        assert len(headers) > 0
        assert "X-Content-Type-Options" in headers


class TestInputSanitizer:
    """Test suite for InputSanitizer."""
    
    def test_sanitize_string(self):
        """Test sanitizing string."""
        result = InputSanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "<" not in result
    
    def test_sanitize_email(self):
        """Test sanitizing email."""
        result = InputSanitizer.sanitize_email("user@example.com")
        assert "@" in result
    
    def test_sanitize_dict(self):
        """Test sanitizing dict."""
        data = {"name": "<b>John</b>", "email": "john@example.com"}
        result = InputSanitizer.sanitize_dict(data)
        assert "<" not in result["name"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
