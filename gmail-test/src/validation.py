"""Data validation and serialization system."""

import logging
import re
import json
from typing import Any, Dict, List, Optional, Type, Callable, Union
from enum import Enum
from dataclasses import dataclass, field, is_dataclass, asdict
from abc import ABC, abstractmethod
import datetime

logger = logging.getLogger(__name__)


class ValidationRule(Enum):
    """Validation rule types."""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    EMAIL = "email"
    URL = "url"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    CHOICES = "choices"
    CUSTOM = "custom"


@dataclass
class ValidationError:
    """Validation error."""
    field: str
    rule: ValidationRule
    message: str
    value: Any = None


class Validator(ABC):
    """Base validator."""
    
    @abstractmethod
    def validate(self, value: Any) -> List[ValidationError]:
        """Validate value."""
        pass


class StringValidator(Validator):
    """Validate string values."""
    
    def __init__(self):
        """Initialize validator."""
        self.min_length = None
        self.max_length = None
        self.pattern = None
        self.choices = None
        self.required = False
    
    def set_required(self, required: bool = True) -> 'StringValidator':
        """Set required."""
        self.required = required
        return self
    
    def set_min_length(self, length: int) -> 'StringValidator':
        """Set minimum length."""
        self.min_length = length
        return self
    
    def set_max_length(self, length: int) -> 'StringValidator':
        """Set maximum length."""
        self.max_length = length
        return self
    
    def set_pattern(self, pattern: str) -> 'StringValidator':
        """Set regex pattern."""
        self.pattern = pattern
        return self
    
    def set_choices(self, choices: List[str]) -> 'StringValidator':
        """Set allowed choices."""
        self.choices = choices
        return self
    
    def validate(self, value: Any, field_name: str = "field") -> List[ValidationError]:
        """Validate value."""
        errors = []
        
        if value is None:
            if self.required:
                errors.append(ValidationError(
                    field=field_name,
                    rule=ValidationRule.REQUIRED,
                    message="Field is required",
                    value=value
                ))
            return errors
        
        if not isinstance(value, str):
            value = str(value)
        
        if self.min_length is not None and len(value) < self.min_length:
            errors.append(ValidationError(
                field=field_name,
                rule=ValidationRule.MIN_LENGTH,
                message=f"Minimum length is {self.min_length}",
                value=value
            ))
        
        if self.max_length is not None and len(value) > self.max_length:
            errors.append(ValidationError(
                field=field_name,
                rule=ValidationRule.MAX_LENGTH,
                message=f"Maximum length is {self.max_length}",
                value=value
            ))
        
        if self.pattern is not None:
            if not re.match(self.pattern, value):
                errors.append(ValidationError(
                    field=field_name,
                    rule=ValidationRule.PATTERN,
                    message=f"Value does not match pattern {self.pattern}",
                    value=value
                ))
        
        if self.choices is not None and value not in self.choices:
            errors.append(ValidationError(
                field=field_name,
                rule=ValidationRule.CHOICES,
                message=f"Value must be one of {self.choices}",
                value=value
            ))
        
        return errors


class EmailValidator(StringValidator):
    """Validate email addresses."""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def __init__(self):
        """Initialize validator."""
        super().__init__()
        self.pattern = self.EMAIL_PATTERN
    
    def validate(self, value: Any, field_name: str = "field") -> List[ValidationError]:
        """Validate email."""
        errors = super().validate(value, field_name)
        
        if not errors and value:
            if not re.match(self.EMAIL_PATTERN, str(value)):
                errors.append(ValidationError(
                    field=field_name,
                    rule=ValidationRule.EMAIL,
                    message="Invalid email format",
                    value=value
                ))
        
        return errors


class URLValidator(StringValidator):
    """Validate URLs."""
    
    URL_PATTERN = r'^https?://[^\s/$.?#].[^\s]*$'
    
    def __init__(self):
        """Initialize validator."""
        super().__init__()
        self.pattern = self.URL_PATTERN
    
    def validate(self, value: Any, field_name: str = "field") -> List[ValidationError]:
        """Validate URL."""
        errors = super().validate(value, field_name)
        
        if not errors and value:
            if not re.match(self.URL_PATTERN, str(value)):
                errors.append(ValidationError(
                    field=field_name,
                    rule=ValidationRule.URL,
                    message="Invalid URL format",
                    value=value
                ))
        
        return errors


class NumberValidator(Validator):
    """Validate numeric values."""
    
    def __init__(self):
        """Initialize validator."""
        self.min_value = None
        self.max_value = None
        self.required = False
    
    def set_required(self, required: bool = True) -> 'NumberValidator':
        """Set required."""
        self.required = required
        return self
    
    def set_min_value(self, value: float) -> 'NumberValidator':
        """Set minimum value."""
        self.min_value = value
        return self
    
    def set_max_value(self, value: float) -> 'NumberValidator':
        """Set maximum value."""
        self.max_value = value
        return self
    
    def validate(self, value: Any, field_name: str = "field") -> List[ValidationError]:
        """Validate value."""
        errors = []
        
        if value is None:
            if self.required:
                errors.append(ValidationError(
                    field=field_name,
                    rule=ValidationRule.REQUIRED,
                    message="Field is required",
                    value=value
                ))
            return errors
        
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field=field_name,
                    rule=ValidationRule.CUSTOM,
                    message="Value must be numeric",
                    value=value
                ))
                return errors
        
        if self.min_value is not None and value < self.min_value:
            errors.append(ValidationError(
                field=field_name,
                rule=ValidationRule.MIN_VALUE,
                message=f"Minimum value is {self.min_value}",
                value=value
            ))
        
        if self.max_value is not None and value > self.max_value:
            errors.append(ValidationError(
                field=field_name,
                rule=ValidationRule.MAX_VALUE,
                message=f"Maximum value is {self.max_value}",
                value=value
            ))
        
        return errors


class SchemaValidator:
    """Validate against schema."""
    
    def __init__(self):
        """Initialize validator."""
        self.schema: Dict[str, Validator] = {}
    
    def add_field(self, field_name: str, validator: Validator) -> None:
        """Add field validator."""
        self.schema[field_name] = validator
    
    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Validate data against schema."""
        errors = []
        
        for field_name, validator in self.schema.items():
            value = data.get(field_name)
            field_errors = validator.validate(value, field_name)
            errors.extend(field_errors)
        
        return errors
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Check if data is valid."""
        return len(self.validate(data)) == 0


class Serializer(ABC):
    """Base serializer."""
    
    @abstractmethod
    def serialize(self, obj: Any) -> Any:
        """Serialize object."""
        pass
    
    @abstractmethod
    def deserialize(self, data: Any) -> Any:
        """Deserialize data."""
        pass


class JSONSerializer(Serializer):
    """JSON serializer."""
    
    def serialize(self, obj: Any) -> str:
        """Serialize to JSON."""
        try:
            return json.dumps(obj, default=self._default_handler, indent=2)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            raise
    
    def deserialize(self, data: str) -> Any:
        """Deserialize from JSON."""
        try:
            return json.loads(data)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise
    
    def _default_handler(self, obj: Any) -> Any:
        """Handle non-JSON-serializable objects."""
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        else:
            return str(obj)


class DataTransformer:
    """Transform data."""
    
    def __init__(self):
        """Initialize transformer."""
        self.transformers: Dict[str, Callable] = {}
    
    def register_transformer(self, name: str, transformer: Callable) -> None:
        """Register transformer."""
        self.transformers[name] = transformer
    
    def transform(self, data: Any, transformer_name: str) -> Any:
        """Transform data."""
        if transformer_name not in self.transformers:
            raise ValueError(f"Transformer not found: {transformer_name}")
        
        try:
            return self.transformers[transformer_name](data)
        except Exception as e:
            logger.error(f"Transformation error: {e}")
            raise
    
    def transform_field(self, data: Dict, field: str, transformer_name: str) -> None:
        """Transform field in dictionary."""
        if field in data:
            data[field] = self.transform(data[field], transformer_name)


class DataFilter:
    """Filter data."""
    
    def __init__(self):
        """Initialize filter."""
        self.filters: Dict[str, Callable] = {}
    
    def register_filter(self, name: str, filter_func: Callable) -> None:
        """Register filter."""
        self.filters[name] = filter_func
    
    def apply_filter(self, data: List[Any], filter_name: str) -> List[Any]:
        """Apply filter to list."""
        if filter_name not in self.filters:
            raise ValueError(f"Filter not found: {filter_name}")
        
        return [item for item in data if self.filters[filter_name](item)]


class DataNormalizer:
    """Normalize data."""
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email."""
        return email.lower().strip() if email else email
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL."""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number."""
        # Remove non-digits
        return re.sub(r'\D', '', phone)
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace."""
        return ' '.join(text.split())


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [
                {
                    "field": e.field,
                    "rule": e.rule.value,
                    "message": e.message
                }
                for e in self.errors
            ]
        }


class ValidationPipeline:
    """Pipeline for data validation."""
    
    def __init__(self):
        """Initialize pipeline."""
        self.validators: List[Validator] = []
    
    def add_validator(self, validator: Validator) -> None:
        """Add validator to pipeline."""
        self.validators.append(validator)
    
    def validate(self, data: Any, field_name: str = "data") -> ValidationResult:
        """Validate data through pipeline."""
        errors = []
        
        for validator in self.validators:
            field_errors = validator.validate(data, field_name)
            errors.extend(field_errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            data={"field": data} if len(errors) == 0 else None
        )


class DataBuilder:
    """Build and validate data."""
    
    def __init__(self, schema_validator: SchemaValidator):
        """Initialize builder."""
        self.schema_validator = schema_validator
        self.data: Dict[str, Any] = {}
    
    def set_field(self, field_name: str, value: Any) -> 'DataBuilder':
        """Set field value."""
        self.data[field_name] = value
        return self
    
    def build(self) -> ValidationResult:
        """Build and validate data."""
        errors = self.schema_validator.validate(self.data)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            data=self.data.copy() if len(errors) == 0 else None
        )
    
    def reset(self) -> None:
        """Reset builder."""
        self.data.clear()
