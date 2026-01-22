"""Tests for filter and template services."""

import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.services.filter_service import (
    FilterService, EmailFilter, FilterCondition, FilterOperator,
    FilterAction, TemplateService, EmailTemplate
)


class TestFilterService:
    """Test suite for FilterService."""
    
    @pytest.fixture
    def filter_service(self):
        """Create filter service."""
        return FilterService()
    
    def test_filter_service_creation(self, filter_service):
        """Test filter service creation."""
        assert len(filter_service.filters) == 0
        assert len(filter_service.active_filters) == 0
    
    def test_create_filter(self, filter_service):
        """Test creating filter."""
        filter_obj = filter_service.create_filter("Test Filter", "Test description")
        assert filter_obj.name == "Test Filter"
        assert len(filter_service.filters) == 1
    
    def test_get_filter(self, filter_service):
        """Test getting filter."""
        filter_obj = filter_service.create_filter("Test Filter")
        retrieved = filter_service.get_filter("Test Filter")
        assert retrieved is not None
        assert retrieved.name == "Test Filter"
    
    def test_enable_filter(self, filter_service):
        """Test enabling filter."""
        filter_obj = filter_service.create_filter("Test Filter")
        result = filter_service.enable_filter("Test Filter")
        assert result is True
        assert len(filter_service.active_filters) == 1
    
    def test_disable_filter(self, filter_service):
        """Test disabling filter."""
        filter_obj = filter_service.create_filter("Test Filter")
        filter_service.enable_filter("Test Filter")
        result = filter_service.disable_filter("Test Filter")
        assert result is True
        assert len(filter_service.active_filters) == 0
    
    def test_delete_filter(self, filter_service):
        """Test deleting filter."""
        filter_obj = filter_service.create_filter("Test Filter")
        result = filter_service.delete_filter("Test Filter")
        assert result is True
        assert len(filter_service.filters) == 0
    
    def test_get_all_filters(self, filter_service):
        """Test getting all filters."""
        filter_service.create_filter("Filter 1")
        filter_service.create_filter("Filter 2")
        filters = filter_service.get_all_filters()
        assert len(filters) == 2
    
    def test_apply_filters(self, filter_service):
        """Test applying filters to email."""
        email = {
            "from": "test@example.com",
            "subject": "URGENT: Test"
        }
        
        filter_obj = filter_service.create_filter("Urgent")
        filter_obj.add_condition("subject", FilterOperator.CONTAINS, "URGENT")
        filter_obj.add_action(FilterAction.STAR)
        filter_service.enable_filter("Urgent")
        
        actions = filter_service.apply_filters(email)
        assert FilterAction.STAR in actions


class TestEmailFilter:
    """Test suite for EmailFilter."""
    
    def test_filter_creation(self):
        """Test filter creation."""
        filter_obj = EmailFilter("Test", "Test filter")
        assert filter_obj.name == "Test"
        assert filter_obj.enabled is False
    
    def test_add_condition(self):
        """Test adding condition."""
        filter_obj = EmailFilter("Test")
        filter_obj.add_condition("from", FilterOperator.EQUALS, "user@example.com")
        assert len(filter_obj.conditions) == 1
    
    def test_add_action(self):
        """Test adding action."""
        filter_obj = EmailFilter("Test")
        filter_obj.add_action(FilterAction.LABEL)
        assert len(filter_obj.actions) == 1
    
    def test_filter_matches(self):
        """Test filter matching."""
        filter_obj = EmailFilter("Test")
        filter_obj.add_condition("from", FilterOperator.EQUALS, "sender@example.com")
        filter_obj.enabled = True
        
        email = {"from": "sender@example.com"}
        assert filter_obj.matches(email) is True
    
    def test_filter_not_matches(self):
        """Test filter not matching."""
        filter_obj = EmailFilter("Test")
        filter_obj.add_condition("from", FilterOperator.EQUALS, "sender@example.com")
        filter_obj.enabled = True
        
        email = {"from": "other@example.com"}
        assert filter_obj.matches(email) is False
    
    def test_filter_disabled(self):
        """Test disabled filter."""
        filter_obj = EmailFilter("Test")
        filter_obj.add_condition("from", FilterOperator.EQUALS, "sender@example.com")
        filter_obj.enabled = False
        
        email = {"from": "sender@example.com"}
        assert filter_obj.matches(email) is False
    
    def test_filter_to_dict(self):
        """Test converting filter to dictionary."""
        filter_obj = EmailFilter("Test", "Description")
        filter_obj.add_condition("from", FilterOperator.EQUALS, "sender@example.com")
        filter_obj.add_action(FilterAction.LABEL)
        
        data = filter_obj.to_dict()
        assert data["name"] == "Test"
        assert len(data["conditions"]) == 1


class TestFilterCondition:
    """Test suite for FilterCondition."""
    
    def test_condition_equals(self):
        """Test equals operator."""
        condition = FilterCondition("from", FilterOperator.EQUALS, "user@example.com")
        email = {"from": "user@example.com"}
        assert condition.evaluate(email) is True
    
    def test_condition_not_equals(self):
        """Test not equals operator."""
        condition = FilterCondition("from", FilterOperator.NOT_EQUALS, "user@example.com")
        email = {"from": "other@example.com"}
        assert condition.evaluate(email) is True
    
    def test_condition_contains(self):
        """Test contains operator."""
        condition = FilterCondition("subject", FilterOperator.CONTAINS, "urgent")
        email = {"subject": "URGENT: Fix needed"}
        assert condition.evaluate(email) is True
    
    def test_condition_starts_with(self):
        """Test starts with operator."""
        condition = FilterCondition("subject", FilterOperator.STARTS_WITH, "URGENT")
        email = {"subject": "URGENT: Fix needed"}
        assert condition.evaluate(email) is True
    
    def test_condition_ends_with(self):
        """Test ends with operator."""
        condition = FilterCondition("subject", FilterOperator.ENDS_WITH, "needed")
        email = {"subject": "URGENT: Fix needed"}
        assert condition.evaluate(email) is True
    
    def test_condition_in_list(self):
        """Test in operator."""
        condition = FilterCondition(
            "from",
            FilterOperator.IN,
            ["user1@example.com", "user2@example.com"]
        )
        email = {"from": "user1@example.com"}
        assert condition.evaluate(email) is True
    
    def test_condition_nested_field(self):
        """Test evaluating nested field."""
        condition = FilterCondition("headers.From", FilterOperator.EQUALS, "sender@example.com")
        email = {"headers": {"From": "sender@example.com"}}
        assert condition.evaluate(email) is True


class TestTemplateService:
    """Test suite for TemplateService."""
    
    @pytest.fixture
    def template_service(self):
        """Create template service."""
        return TemplateService()
    
    def test_template_service_initialization(self, template_service):
        """Test template service has default templates."""
        templates = template_service.list_templates()
        assert len(templates) > 0
    
    def test_create_template(self, template_service):
        """Test creating custom template."""
        template_service.create_template(
            "custom",
            "Hello {{name}}, {{message}}"
        )
        templates = template_service.list_templates()
        assert "custom" in templates
    
    def test_get_template(self, template_service):
        """Test getting template."""
        template_service.create_template("test", "Test content")
        template = template_service.get_template("test")
        assert template is not None
    
    def test_delete_template(self, template_service):
        """Test deleting template."""
        template_service.create_template("custom", "Content")
        result = template_service.delete_template("custom")
        assert result is True
    
    def test_delete_default_template(self, template_service):
        """Test deleting default template."""
        result = template_service.delete_template("greeting")
        assert result is False
    
    def test_render_template(self, template_service):
        """Test rendering template."""
        result = template_service.render_template(
            "greeting",
            {"name": "John", "body": "Welcome!"}
        )
        assert "John" in result
    
    def test_list_templates_default_only(self, template_service):
        """Test listing only default templates."""
        templates = template_service.list_templates(default_only=True)
        assert len(templates) > 0


class TestEmailTemplate:
    """Test suite for EmailTemplate."""
    
    def test_template_creation(self):
        """Test template creation."""
        template = EmailTemplate(
            "greeting",
            "Hello {{name}}, welcome!"
        )
        assert template.name == "greeting"
    
    def test_get_variables(self):
        """Test extracting variables."""
        template = EmailTemplate(
            "test",
            "Hello {{name}}, your email is {{email}}"
        )
        variables = template.get_variables()
        assert "name" in variables
        assert "email" in variables
    
    def test_render_template(self):
        """Test rendering template."""
        template = EmailTemplate(
            "greeting",
            "Hello {{name}}, welcome to {{company}}!"
        )
        result = template.render({
            "name": "John",
            "company": "Acme Corp"
        })
        assert "John" in result
        assert "Acme Corp" in result
    
    def test_validate_variables_success(self):
        """Test variable validation success."""
        template = EmailTemplate(
            "test",
            "Hello {{name}}"
        )
        result = template.validate_variables({"name": "John"})
        assert result is True
    
    def test_validate_variables_missing(self):
        """Test variable validation with missing variables."""
        template = EmailTemplate(
            "test",
            "Hello {{name}}, your email is {{email}}"
        )
        result = template.validate_variables({"name": "John"})
        assert result is False


class TestFilterOperator:
    """Test suite for FilterOperator enum."""
    
    def test_filter_operators(self):
        """Test filter operator values."""
        assert FilterOperator.EQUALS.value == "eq"
        assert FilterOperator.CONTAINS.value == "contains"
        assert FilterOperator.IN.value == "in"


class TestFilterAction:
    """Test suite for FilterAction enum."""
    
    def test_filter_actions(self):
        """Test filter action values."""
        assert FilterAction.LABEL.value == "label"
        assert FilterAction.ARCHIVE.value == "archive"
        assert FilterAction.DELETE.value == "delete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
