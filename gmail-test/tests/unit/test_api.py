"""Tests for API routes."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.api.routes import (
    GmailAPI, APIRouter, APIResponse, APIError,
    ValidationError, NotFoundError, UnauthorizedError,
    ResponseStatus
)


class TestAPIResponse:
    """Test suite for APIResponse."""
    
    def test_response_creation(self):
        """Test response creation."""
        response = APIResponse(
            status=ResponseStatus.SUCCESS,
            message="Test",
            data={"key": "value"}
        )
        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"key": "value"}
    
    def test_response_to_dict(self):
        """Test converting response to dict."""
        response = APIResponse(
            status=ResponseStatus.SUCCESS,
            message="Test"
        )
        data = response.to_dict()
        assert data["status"] == "success"
        assert data["message"] == "Test"


class TestGmailAPI:
    """Test suite for GmailAPI."""
    
    @pytest.fixture
    def api(self):
        """Create API instance."""
        return GmailAPI()
    
    def test_get_emails_success(self, api):
        """Test getting emails."""
        response = api.get_emails(limit=5)
        assert response.status == ResponseStatus.SUCCESS
        assert response.data is not None
    
    def test_get_emails_invalid_limit(self, api):
        """Test getting emails with invalid limit."""
        response = api.get_emails(limit=200)
        assert response.status == ResponseStatus.VALIDATION_ERROR
    
    def test_send_email_success(self, api):
        """Test sending email."""
        response = api.send_email(
            to=["recipient@example.com"],
            subject="Test",
            body="Test body"
        )
        assert response.status == ResponseStatus.SUCCESS
    
    def test_send_email_empty_recipients(self, api):
        """Test sending email without recipients."""
        response = api.send_email(to=[], subject="Test", body="Test")
        assert response.status == ResponseStatus.VALIDATION_ERROR
    
    def test_send_email_empty_subject(self, api):
        """Test sending email without subject."""
        response = api.send_email(
            to=["recipient@example.com"],
            subject="",
            body="Test"
        )
        assert response.status == ResponseStatus.VALIDATION_ERROR
    
    def test_delete_email_success(self, api):
        """Test deleting email."""
        response = api.delete_email("msg_123")
        assert response.status == ResponseStatus.SUCCESS
    
    def test_delete_email_empty_id(self, api):
        """Test deleting email without ID."""
        response = api.delete_email("")
        assert response.status == ResponseStatus.VALIDATION_ERROR
    
    def test_apply_filter_success(self, api):
        """Test applying filter."""
        response = api.apply_filter(
            filter_name="Test",
            email_ids=["msg_1", "msg_2"]
        )
        assert response.status == ResponseStatus.SUCCESS
    
    def test_get_labels(self, api):
        """Test getting labels."""
        response = api.get_labels()
        assert response.status == ResponseStatus.SUCCESS
        assert "labels" in response.data
    
    def test_create_filter(self, api):
        """Test creating filter."""
        response = api.create_filter(
            name="TestFilter",
            conditions={"from": "test@example.com"}
        )
        assert response.status == ResponseStatus.SUCCESS
    
    def test_get_stats(self, api):
        """Test getting statistics."""
        response = api.get_stats()
        assert response.status == ResponseStatus.SUCCESS
        assert "total_emails" in response.data


class TestAPIRouter:
    """Test suite for APIRouter."""
    
    @pytest.fixture
    def router(self):
        """Create API router."""
        return APIRouter()
    
    def test_route_get_emails(self, router):
        """Test routing GET /emails."""
        response = router.route("GET", "/emails", {"limit": 5})
        assert response.status == ResponseStatus.SUCCESS
    
    def test_route_post_emails(self, router):
        """Test routing POST /emails."""
        response = router.route(
            "POST",
            "/emails",
            {
                "to": ["recipient@example.com"],
                "subject": "Test",
                "body": "Test"
            }
        )
        assert response.status == ResponseStatus.SUCCESS
    
    def test_route_not_found(self, router):
        """Test routing non-existent route."""
        response = router.route("GET", "/nonexistent", {})
        assert response.status == ResponseStatus.NOT_FOUND


class TestAPIErrors:
    """Test suite for API errors."""
    
    def test_api_error_creation(self):
        """Test creating API error."""
        error = APIError("Test error")
        assert error.message == "Test error"
    
    def test_validation_error_creation(self):
        """Test creating validation error."""
        error = ValidationError("Invalid", ["Error 1", "Error 2"])
        assert error.status == ResponseStatus.VALIDATION_ERROR
        assert len(error.errors) == 2
    
    def test_not_found_error(self):
        """Test creating not found error."""
        error = NotFoundError("Not found")
        assert error.status == ResponseStatus.NOT_FOUND
    
    def test_unauthorized_error(self):
        """Test creating unauthorized error."""
        error = UnauthorizedError()
        assert error.status == ResponseStatus.UNAUTHORIZED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
