"""Tests for data validation and serialization."""

import pytest
import json
from datetime import datetime, date
from src.validation import (
    ValidationRule, ValidationError, StringValidator, EmailValidator,
    URLValidator, NumberValidator, SchemaValidator, JSONSerializer,
    DataTransformer, DataFilter, DataNormalizer, ValidationResult,
    ValidationPipeline, DataBuilder
)


class TestValidationRule:
    """Test ValidationRule enum."""
    
    def test_rules(self):
        """Test validation rules."""
        assert ValidationRule.REQUIRED.value == "required"
        assert ValidationRule.EMAIL.value == "email"
        assert ValidationRule.URL.value == "url"


class TestValidationError:
    """Test ValidationError."""
    
    def test_creation(self):
        """Test error creation."""
        error = ValidationError(
            field="email",
            rule=ValidationRule.EMAIL,
            message="Invalid email"
        )
        assert error.field == "email"
        assert error.rule == ValidationRule.EMAIL


class TestStringValidator:
    """Test StringValidator."""
    
    def test_valid_string(self):
        """Test validating string."""
        validator = StringValidator()
        errors = validator.validate("test", "field")
        assert len(errors) == 0
    
    def test_required_empty(self):
        """Test required validation."""
        validator = StringValidator().set_required(True)
        errors = validator.validate(None, "field")
        assert len(errors) > 0
    
    def test_required_not_set(self):
        """Test optional field."""
        validator = StringValidator()
        errors = validator.validate(None, "field")
        assert len(errors) == 0
    
    def test_min_length(self):
        """Test minimum length."""
        validator = StringValidator().set_min_length(3)
        
        errors = validator.validate("ab", "field")
        assert len(errors) > 0
        
        errors = validator.validate("abc", "field")
        assert len(errors) == 0
    
    def test_max_length(self):
        """Test maximum length."""
        validator = StringValidator().set_max_length(5)
        
        errors = validator.validate("abcdef", "field")
        assert len(errors) > 0
        
        errors = validator.validate("abc", "field")
        assert len(errors) == 0
    
    def test_pattern(self):
        """Test pattern validation."""
        validator = StringValidator().set_pattern(r'^\d+$')
        
        errors = validator.validate("abc", "field")
        assert len(errors) > 0
        
        errors = validator.validate("123", "field")
        assert len(errors) == 0
    
    def test_choices(self):
        """Test choice validation."""
        validator = StringValidator().set_choices(["red", "green", "blue"])
        
        errors = validator.validate("yellow", "field")
        assert len(errors) > 0
        
        errors = validator.validate("red", "field")
        assert len(errors) == 0
    
    def test_chaining(self):
        """Test validator chaining."""
        validator = (StringValidator()
                     .set_required(True)
                     .set_min_length(3)
                     .set_max_length(10))
        
        errors = validator.validate("test", "field")
        assert len(errors) == 0


class TestEmailValidator:
    """Test EmailValidator."""
    
    def test_valid_email(self):
        """Test valid email."""
        validator = EmailValidator()
        errors = validator.validate("test@example.com", "field")
        assert len(errors) == 0
    
    def test_invalid_email(self):
        """Test invalid email."""
        validator = EmailValidator()
        
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "invalid @example.com"
        ]
        
        for email in invalid_emails:
            errors = validator.validate(email, "field")
            assert len(errors) > 0


class TestURLValidator:
    """Test URLValidator."""
    
    def test_valid_url(self):
        """Test valid URL."""
        validator = URLValidator()
        
        valid_urls = [
            "http://example.com",
            "https://example.com/path",
            "https://example.com:8080/path?query=value"
        ]
        
        for url in valid_urls:
            errors = validator.validate(url, "field")
            assert len(errors) == 0
    
    def test_invalid_url(self):
        """Test invalid URL."""
        validator = URLValidator()
        errors = validator.validate("not a url", "field")
        assert len(errors) > 0


class TestNumberValidator:
    """Test NumberValidator."""
    
    def test_valid_number(self):
        """Test valid number."""
        validator = NumberValidator()
        errors = validator.validate(42, "field")
        assert len(errors) == 0
    
    def test_min_value(self):
        """Test minimum value."""
        validator = NumberValidator().set_min_value(0)
        
        errors = validator.validate(-1, "field")
        assert len(errors) > 0
        
        errors = validator.validate(1, "field")
        assert len(errors) == 0
    
    def test_max_value(self):
        """Test maximum value."""
        validator = NumberValidator().set_max_value(100)
        
        errors = validator.validate(101, "field")
        assert len(errors) > 0
        
        errors = validator.validate(50, "field")
        assert len(errors) == 0
    
    def test_invalid_number(self):
        """Test invalid number."""
        validator = NumberValidator()
        errors = validator.validate("not a number", "field")
        assert len(errors) > 0


class TestSchemaValidator:
    """Test SchemaValidator."""
    
    def test_schema_validation(self):
        """Test schema validation."""
        schema = SchemaValidator()
        schema.add_field("email", EmailValidator())
        schema.add_field("age", NumberValidator().set_min_value(0))
        
        valid_data = {
            "email": "test@example.com",
            "age": 25
        }
        
        errors = schema.validate(valid_data)
        assert len(errors) == 0
    
    def test_schema_validation_failure(self):
        """Test schema validation failure."""
        schema = SchemaValidator()
        schema.add_field("email", EmailValidator())
        
        invalid_data = {
            "email": "invalid"
        }
        
        errors = schema.validate(invalid_data)
        assert len(errors) > 0
    
    def test_is_valid(self):
        """Test is_valid method."""
        schema = SchemaValidator()
        schema.add_field("email", EmailValidator())
        
        assert schema.is_valid({"email": "test@example.com"}) is True
        assert schema.is_valid({"email": "invalid"}) is False


class TestJSONSerializer:
    """Test JSONSerializer."""
    
    def test_serialize_dict(self):
        """Test serializing dictionary."""
        serializer = JSONSerializer()
        data = {"name": "test", "value": 42}
        
        result = serializer.serialize(data)
        assert isinstance(result, str)
        assert "name" in result
    
    def test_deserialize_json(self):
        """Test deserializing JSON."""
        serializer = JSONSerializer()
        json_str = '{"name": "test", "value": 42}'
        
        result = serializer.deserialize(json_str)
        assert result["name"] == "test"
        assert result["value"] == 42
    
    def test_serialize_datetime(self):
        """Test serializing datetime."""
        serializer = JSONSerializer()
        data = {"timestamp": datetime.now()}
        
        result = serializer.serialize(data)
        assert isinstance(result, str)
    
    def test_serialize_enum(self):
        """Test serializing enum."""
        from enum import Enum
        
        class Color(Enum):
            RED = "red"
            BLUE = "blue"
        
        serializer = JSONSerializer()
        data = {"color": Color.RED}
        
        result = serializer.serialize(data)
        assert "red" in result


class TestDataTransformer:
    """Test DataTransformer."""
    
    def test_register_transformer(self):
        """Test registering transformer."""
        transformer = DataTransformer()
        transformer.register_transformer("upper", lambda x: x.upper())
        
        result = transformer.transform("hello", "upper")
        assert result == "HELLO"
    
    def test_transform_field(self):
        """Test transforming field."""
        transformer = DataTransformer()
        transformer.register_transformer("upper", lambda x: x.upper())
        
        data = {"name": "hello"}
        transformer.transform_field(data, "name", "upper")
        
        assert data["name"] == "HELLO"


class TestDataFilter:
    """Test DataFilter."""
    
    def test_apply_filter(self):
        """Test applying filter."""
        filter_obj = DataFilter()
        filter_obj.register_filter("even", lambda x: x % 2 == 0)
        
        data = [1, 2, 3, 4, 5, 6]
        result = filter_obj.apply_filter(data, "even")
        
        assert result == [2, 4, 6]


class TestDataNormalizer:
    """Test DataNormalizer."""
    
    def test_normalize_email(self):
        """Test normalizing email."""
        result = DataNormalizer.normalize_email("  Test@Example.COM  ")
        assert result == "test@example.com"
    
    def test_normalize_url(self):
        """Test normalizing URL."""
        result = DataNormalizer.normalize_url("example.com")
        assert result == "https://example.com"
    
    def test_normalize_phone(self):
        """Test normalizing phone."""
        result = DataNormalizer.normalize_phone("+1 (555) 123-4567")
        assert result == "15551234567"
    
    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        result = DataNormalizer.normalize_whitespace("  hello    world  ")
        assert result == "hello world"


class TestValidationResult:
    """Test ValidationResult."""
    
    def test_valid_result(self):
        """Test valid result."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_invalid_result(self):
        """Test invalid result."""
        error = ValidationError("field", ValidationRule.REQUIRED, "Required")
        result = ValidationResult(valid=False, errors=[error])
        
        assert result.valid is False
        assert len(result.errors) == 1
    
    def test_to_dict(self):
        """Test converting to dict."""
        result = ValidationResult(valid=True)
        data = result.to_dict()
        
        assert data["valid"] is True
        assert "errors" in data


class TestValidationPipeline:
    """Test ValidationPipeline."""
    
    def test_single_validator(self):
        """Test with single validator."""
        pipeline = ValidationPipeline()
        pipeline.add_validator(StringValidator().set_required(True))
        
        result = pipeline.validate("test", "field")
        assert result.valid is True
    
    def test_multiple_validators(self):
        """Test with multiple validators."""
        pipeline = ValidationPipeline()
        pipeline.add_validator(StringValidator().set_required(True))
        pipeline.add_validator(StringValidator().set_min_length(5))
        
        result = pipeline.validate("test", "field")
        assert result.valid is False
        
        result = pipeline.validate("testing", "field")
        assert result.valid is True


class TestDataBuilder:
    """Test DataBuilder."""
    
    def test_build_valid_data(self):
        """Test building valid data."""
        schema = SchemaValidator()
        schema.add_field("name", StringValidator().set_required(True))
        schema.add_field("age", NumberValidator().set_min_value(0))
        
        builder = DataBuilder(schema)
        builder.set_field("name", "John").set_field("age", 30)
        
        result = builder.build()
        assert result.valid is True
    
    def test_build_invalid_data(self):
        """Test building invalid data."""
        schema = SchemaValidator()
        schema.add_field("name", StringValidator().set_required(True))
        
        builder = DataBuilder(schema)
        builder.set_field("name", None)
        
        result = builder.build()
        assert result.valid is False
    
    def test_reset_builder(self):
        """Test resetting builder."""
        schema = SchemaValidator()
        builder = DataBuilder(schema)
        builder.set_field("name", "John")
        builder.reset()
        
        assert len(builder.data) == 0


class TestValidationIntegration:
    """Integration tests for validation."""
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        # Create schema
        schema = SchemaValidator()
        schema.add_field("email", EmailValidator().set_required(True))
        schema.add_field("age", NumberValidator().set_min_value(0).set_max_value(150))
        
        # Valid data
        valid_data = {
            "email": "test@example.com",
            "age": 30
        }
        
        assert schema.is_valid(valid_data) is True
        
        # Invalid data
        invalid_data = {
            "email": "invalid",
            "age": 200
        }
        
        errors = schema.validate(invalid_data)
        assert len(errors) > 0
    
    def test_serialization_workflow(self):
        """Test serialization workflow."""
        serializer = JSONSerializer()
        
        data = {
            "name": "test",
            "value": 42,
            "timestamp": datetime.now()
        }
        
        # Serialize
        serialized = serializer.serialize(data)
        assert isinstance(serialized, str)
        
        # Deserialize
        deserialized = serializer.deserialize(serialized)
        assert deserialized["name"] == "test"
        assert deserialized["value"] == 42
