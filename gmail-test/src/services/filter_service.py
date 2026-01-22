"""Service layer for email filtering and template management."""

import logging
import re
from typing import List, Dict, Callable, Optional, Any, Pattern
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class FilterOperator(Enum):
    """Filter operators."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IN = "in"
    NOT_IN = "not_in"


class FilterAction(Enum):
    """Actions to apply after filtering."""
    LABEL = "label"
    ARCHIVE = "archive"
    DELETE = "delete"
    STAR = "star"
    MARK_READ = "mark_read"
    SKIP = "skip"
    FORWARD = "forward"


class FilterService:
    """
    Advanced email filtering service.
    
    Supports creating complex filter rules with multiple conditions
    and automated actions.
    """
    
    def __init__(self):
        """Initialize filter service."""
        self.filters: List['EmailFilter'] = []
        self.active_filters: List['EmailFilter'] = []
        self._filter_cache: Dict[str, Any] = {}
    
    def create_filter(self, name: str, description: str = "") -> 'EmailFilter':
        """
        Create a new email filter.
        
        Args:
            name: Filter name
            description: Filter description
            
        Returns:
            New EmailFilter instance
        """
        filter_obj = EmailFilter(name, description)
        self.filters.append(filter_obj)
        logger.info(f"Created filter: {name}")
        return filter_obj
    
    def apply_filters(self, email: Dict[str, Any]) -> List[FilterAction]:
        """
        Apply all active filters to an email.
        
        Args:
            email: Email data dictionary
            
        Returns:
            List of actions to apply
        """
        actions = []
        
        for filter_obj in self.active_filters:
            if filter_obj.matches(email):
                actions.extend(filter_obj.actions)
                logger.debug(f"Filter '{filter_obj.name}' matched")
        
        return actions
    
    def get_filter(self, name: str) -> Optional['EmailFilter']:
        """Get filter by name."""
        for filter_obj in self.filters:
            if filter_obj.name == name:
                return filter_obj
        return None
    
    def enable_filter(self, name: str) -> bool:
        """Enable a filter."""
        filter_obj = self.get_filter(name)
        if filter_obj:
            filter_obj.enabled = True
            if filter_obj not in self.active_filters:
                self.active_filters.append(filter_obj)
            logger.info(f"Enabled filter: {name}")
            return True
        return False
    
    def disable_filter(self, name: str) -> bool:
        """Disable a filter."""
        filter_obj = self.get_filter(name)
        if filter_obj:
            filter_obj.enabled = False
            if filter_obj in self.active_filters:
                self.active_filters.remove(filter_obj)
            logger.info(f"Disabled filter: {name}")
            return True
        return False
    
    def delete_filter(self, name: str) -> bool:
        """Delete a filter."""
        filter_obj = self.get_filter(name)
        if filter_obj:
            if filter_obj in self.active_filters:
                self.active_filters.remove(filter_obj)
            self.filters.remove(filter_obj)
            logger.info(f"Deleted filter: {name}")
            return True
        return False
    
    def get_all_filters(self) -> List['EmailFilter']:
        """Get all filters."""
        return self.filters.copy()
    
    def get_active_filters(self) -> List['EmailFilter']:
        """Get all active filters."""
        return self.active_filters.copy()


class EmailFilter:
    """
    Email filter with conditions and actions.
    
    Supports complex filtering with multiple conditions.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize email filter.
        
        Args:
            name: Filter name
            description: Filter description
        """
        self.name = name
        self.description = description
        self.conditions: List['FilterCondition'] = []
        self.actions: List[FilterAction] = []
        self.enabled = False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_condition(self, field: str, operator: FilterOperator, value: Any) -> 'EmailFilter':
        """
        Add a condition to the filter.
        
        Args:
            field: Email field name
            operator: Comparison operator
            value: Value to compare
            
        Returns:
            Self for chaining
        """
        condition = FilterCondition(field, operator, value)
        self.conditions.append(condition)
        self.updated_at = datetime.now()
        return self
    
    def add_action(self, action: FilterAction) -> 'EmailFilter':
        """
        Add an action to the filter.
        
        Args:
            action: Action to apply
            
        Returns:
            Self for chaining
        """
        self.actions.append(action)
        self.updated_at = datetime.now()
        return self
    
    def matches(self, email: Dict[str, Any], match_all: bool = True) -> bool:
        """
        Check if email matches filter conditions.
        
        Args:
            email: Email data dictionary
            match_all: If True, all conditions must match; if False, any condition
            
        Returns:
            True if email matches filter
        """
        if not self.enabled or not self.conditions:
            return False
        
        results = [condition.evaluate(email) for condition in self.conditions]
        
        if match_all:
            return all(results)
        else:
            return any(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.value for a in self.actions]
        }


class FilterCondition:
    """
    Single filter condition.
    
    Represents one condition in a filter.
    """
    
    def __init__(self, field: str, operator: FilterOperator, value: Any):
        """
        Initialize filter condition.
        
        Args:
            field: Email field name
            operator: Comparison operator
            value: Value to compare
        """
        self.field = field
        self.operator = operator
        self.value = value
    
    def evaluate(self, email: Dict[str, Any]) -> bool:
        """
        Evaluate condition against email.
        
        Args:
            email: Email data dictionary
            
        Returns:
            True if condition matches
        """
        email_value = self._get_email_value(email)
        
        if email_value is None:
            return False
        
        if self.operator == FilterOperator.EQUALS:
            return email_value == self.value
        elif self.operator == FilterOperator.NOT_EQUALS:
            return email_value != self.value
        elif self.operator == FilterOperator.CONTAINS:
            return str(self.value).lower() in str(email_value).lower()
        elif self.operator == FilterOperator.NOT_CONTAINS:
            return str(self.value).lower() not in str(email_value).lower()
        elif self.operator == FilterOperator.STARTS_WITH:
            return str(email_value).lower().startswith(str(self.value).lower())
        elif self.operator == FilterOperator.ENDS_WITH:
            return str(email_value).lower().endswith(str(self.value).lower())
        elif self.operator == FilterOperator.IN:
            return email_value in self.value
        elif self.operator == FilterOperator.NOT_IN:
            return email_value not in self.value
        
        return False
    
    def _get_email_value(self, email: Dict[str, Any]) -> Any:
        """Get value from email by field name."""
        if "." in self.field:
            parts = self.field.split(".")
            value = email
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        else:
            return email.get(self.field)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert condition to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value
        }


class TemplateService:
    """
    Email template service.
    
    Manages email templates for quick composition.
    """
    
    def __init__(self):
        """Initialize template service."""
        self.templates: Dict[str, 'EmailTemplate'] = {}
        self._default_templates = self._create_default_templates()
        self.templates.update(self._default_templates)
    
    def _create_default_templates(self) -> Dict[str, 'EmailTemplate']:
        """Create default email templates."""
        return {
            "greeting": EmailTemplate(
                "greeting",
                "Hello {{name}},\n\n{{body}}\n\nBest regards",
                "Greeting Template"
            ),
            "apology": EmailTemplate(
                "apology",
                "Dear {{name}},\n\nI sincerely apologize for {{issue}}.\n\n{{explanation}}\n\nThank you for your understanding.",
                "Apology Template"
            ),
            "meeting_request": EmailTemplate(
                "meeting_request",
                "Dear {{name}},\n\nWould you be available for a meeting on {{date}} at {{time}}?\n\n{{details}}\n\nPlease let me know.",
                "Meeting Request Template"
            ),
            "follow_up": EmailTemplate(
                "follow_up",
                "Hi {{name}},\n\nFollowing up on {{topic}}.\n\n{{message}}\n\nThanks",
                "Follow-up Template"
            )
        }
    
    def create_template(self, name: str, content: str, description: str = "") -> 'EmailTemplate':
        """
        Create a new email template.
        
        Args:
            name: Template name
            content: Template content with {{variable}} placeholders
            description: Template description
            
        Returns:
            New EmailTemplate instance
        """
        template = EmailTemplate(name, content, description)
        self.templates[name] = template
        logger.info(f"Created template: {name}")
        return template
    
    def get_template(self, name: str) -> Optional['EmailTemplate']:
        """Get template by name."""
        return self.templates.get(name)
    
    def delete_template(self, name: str) -> bool:
        """Delete a template."""
        if name in self._default_templates:
            logger.warning(f"Cannot delete default template: {name}")
            return False
        
        if name in self.templates:
            del self.templates[name]
            logger.info(f"Deleted template: {name}")
            return True
        
        return False
    
    def render_template(self, name: str, variables: Dict[str, str]) -> Optional[str]:
        """
        Render a template with variables.
        
        Args:
            name: Template name
            variables: Dictionary of variables to substitute
            
        Returns:
            Rendered template content or None
        """
        template = self.get_template(name)
        if template:
            return template.render(variables)
        return None
    
    def list_templates(self, default_only: bool = False) -> List[str]:
        """Get list of template names."""
        if default_only:
            return list(self._default_templates.keys())
        return list(self.templates.keys())


class EmailTemplate:
    """
    Email template with variable substitution.
    
    Supports {{variable}} placeholders.
    """
    
    def __init__(self, name: str, content: str, description: str = ""):
        """
        Initialize email template.
        
        Args:
            name: Template name
            content: Template content
            description: Template description
        """
        self.name = name
        self.content = content
        self.description = description
        self.created_at = datetime.now()
        self._pattern = re.compile(r'\{\{(\w+)\}\}')
    
    def get_variables(self) -> List[str]:
        """Get list of variables in template."""
        return self._pattern.findall(self.content)
    
    def render(self, variables: Dict[str, str]) -> str:
        """
        Render template with variables.
        
        Args:
            variables: Dictionary of variable values
            
        Returns:
            Rendered content
        """
        result = self.content
        for var, value in variables.items():
            result = result.replace(f"{{{{{var}}}}}", str(value))
        return result
    
    def validate_variables(self, variables: Dict[str, str]) -> bool:
        """
        Validate that all required variables are provided.
        
        Args:
            variables: Dictionary of provided variables
            
        Returns:
            True if all variables provided
        """
        required = set(self.get_variables())
        provided = set(variables.keys())
        return required.issubset(provided)
