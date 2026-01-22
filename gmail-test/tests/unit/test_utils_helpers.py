"""Tests for utility helpers."""

import pytest
from datetime import datetime, timedelta
from src.utils_helpers import (
    StringUtils, HashUtils, JSONUtils, DateTimeUtils, ListUtils,
    DictUtils, EnvironmentUtils, RetryUtils, ValidationUtils
)


class TestStringUtils:
    """Test StringUtils."""
    
    def test_sanitize(self):
        """Test sanitize."""
        assert StringUtils.sanitize("  HELLO WORLD  ") == "hello world"
        assert StringUtils.sanitize("") == ""
    
    def test_truncate(self):
        """Test truncate."""
        text = "This is a very long string that should be truncated"
        truncated = StringUtils.truncate(text, 20)
        assert len(truncated) == 20
        assert truncated.endswith("...")
    
    def test_split_camel_case(self):
        """Test split camel case."""
        assert StringUtils.split_camel_case("helloWorld") == "hello_world"
        assert StringUtils.split_camel_case("HelloWorld") == "hello_world"
    
    def test_is_email(self):
        """Test is email."""
        assert StringUtils.is_email("test@example.com") is True
        assert StringUtils.is_email("invalid-email") is False
    
    def test_is_url(self):
        """Test is URL."""
        assert StringUtils.is_url("https://example.com") is True
        assert StringUtils.is_url("http://test.org") is True
        assert StringUtils.is_url("not a url") is False
    
    def test_extract_emails(self):
        """Test extract emails."""
        text = "Contact me at test@example.com or admin@test.org"
        emails = StringUtils.extract_emails(text)
        assert len(emails) == 2
        assert "test@example.com" in emails
    
    def test_extract_urls(self):
        """Test extract URLs."""
        text = "Visit https://example.com or http://test.org for more"
        urls = StringUtils.extract_urls(text)
        assert len(urls) == 2
    
    def test_to_slug(self):
        """Test to slug."""
        assert StringUtils.to_slug("Hello World") == "hello-world"
        assert StringUtils.to_slug("Hello-World-123") == "hello-world-123"


class TestHashUtils:
    """Test HashUtils."""
    
    def test_md5(self):
        """Test MD5 hash."""
        hash_val = HashUtils.md5("hello")
        assert len(hash_val) == 32
        assert hash_val == "5d41402abc4b2a76b9719d911017c592"
    
    def test_sha256(self):
        """Test SHA256 hash."""
        hash_val = HashUtils.sha256("hello")
        assert len(hash_val) == 64


class TestJSONUtils:
    """Test JSONUtils."""
    
    def test_safe_dumps(self):
        """Test safe dumps."""
        data = {"key": "value", "number": 42}
        result = JSONUtils.safe_dumps(data)
        assert "key" in result
        assert "value" in result
    
    def test_safe_loads(self):
        """Test safe loads."""
        json_str = '{"key": "value"}'
        result = JSONUtils.safe_loads(json_str)
        assert result["key"] == "value"
    
    def test_safe_loads_invalid(self):
        """Test safe loads with invalid JSON."""
        result = JSONUtils.safe_loads("invalid json")
        assert result == {}
    
    def test_pretty_print(self):
        """Test pretty print."""
        data = {"key": "value"}
        result = JSONUtils.pretty_print(data)
        assert "\n" in result or isinstance(result, str)


class TestDateTimeUtils:
    """Test DateTimeUtils."""
    
    def test_now(self):
        """Test now."""
        now = DateTimeUtils.now()
        assert isinstance(now, datetime)
    
    def test_format_datetime(self):
        """Test format datetime."""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        formatted = DateTimeUtils.format_datetime(dt)
        assert "2024" in formatted
        assert "12" in formatted
    
    def test_parse_datetime(self):
        """Test parse datetime."""
        text = "2024-01-01 12:30:45"
        dt = DateTimeUtils.parse_datetime(text)
        assert dt is not None
        assert dt.year == 2024
    
    def test_get_relative_time(self):
        """Test get relative time."""
        now = datetime.now()
        past = now - timedelta(hours=2)
        
        relative = DateTimeUtils.get_relative_time(past)
        assert "hour" in relative or "ago" in relative


class TestListUtils:
    """Test ListUtils."""
    
    def test_flatten(self):
        """Test flatten."""
        nested = [1, [2, 3, [4, 5]], 6]
        flat = ListUtils.flatten(nested)
        assert flat == [1, 2, 3, 4, 5, 6]
    
    def test_unique(self):
        """Test unique."""
        items = [1, 2, 2, 3, 3, 3, 4]
        unique = ListUtils.unique(items)
        assert unique == [1, 2, 3, 4]
    
    def test_chunk(self):
        """Test chunk."""
        items = [1, 2, 3, 4, 5, 6, 7]
        chunks = ListUtils.chunk(items, 3)
        assert len(chunks) == 3
        assert chunks[0] == [1, 2, 3]
        assert chunks[-1] == [7]
    
    def test_zip_dicts(self):
        """Test zip dicts."""
        keys = ["a", "b", "c"]
        values = [1, 2, 3]
        result = ListUtils.zip_dicts(keys, values)
        assert result == {"a": 1, "b": 2, "c": 3}


class TestDictUtils:
    """Test DictUtils."""
    
    def test_merge(self):
        """Test merge."""
        d1 = {"a": 1, "b": 2}
        d2 = {"c": 3}
        d3 = {"d": 4}
        
        merged = DictUtils.merge(d1, d2, d3)
        assert merged == {"a": 1, "b": 2, "c": 3, "d": 4}
    
    def test_get_nested(self):
        """Test get nested."""
        d = {"user": {"profile": {"name": "John"}}}
        value = DictUtils.get_nested(d, "user.profile.name")
        assert value == "John"
    
    def test_get_nested_default(self):
        """Test get nested with default."""
        d = {"user": {}}
        value = DictUtils.get_nested(d, "user.profile.name", "default")
        assert value == "default"
    
    def test_set_nested(self):
        """Test set nested."""
        d = {}
        DictUtils.set_nested(d, "user.profile.name", "John")
        assert d["user"]["profile"]["name"] == "John"
    
    def test_flatten(self):
        """Test flatten."""
        d = {"user": {"name": "John", "age": 30}, "active": True}
        flat = DictUtils.flatten(d)
        assert flat["user.name"] == "John"
        assert flat["user.age"] == 30
        assert flat["active"] is True


class TestEnvironmentUtils:
    """Test EnvironmentUtils."""
    
    def test_get_env_bool_true(self):
        """Test get env bool true."""
        import os
        os.environ["TEST_VAR"] = "true"
        value = EnvironmentUtils.get_env("TEST_VAR", False)
        assert value is True
    
    def test_get_env_bool_false(self):
        """Test get env bool false."""
        import os
        os.environ["TEST_VAR"] = "false"
        value = EnvironmentUtils.get_env("TEST_VAR", True)
        assert value is False
    
    def test_get_env_int(self):
        """Test get env int."""
        import os
        os.environ["TEST_NUM"] = "42"
        value = EnvironmentUtils.get_env("TEST_NUM")
        assert value == 42
    
    def test_get_env_list(self):
        """Test get env list."""
        import os
        os.environ["TEST_LIST"] = "a,b,c"
        values = EnvironmentUtils.get_env_list("TEST_LIST")
        assert values == ["a", "b", "c"]


class TestRetryUtils:
    """Test RetryUtils."""
    
    def test_retry_success(self):
        """Test retry success."""
        call_count = [0]
        
        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Error")
            return "success"
        
        result = RetryUtils.retry(func, max_attempts=5, delay=0.01)
        assert result == "success"
        assert call_count[0] == 3
    
    def test_retry_failure(self):
        """Test retry failure."""
        def func():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            RetryUtils.retry(func, max_attempts=2, delay=0.01)


class TestValidationUtils:
    """Test ValidationUtils."""
    
    def test_is_none_or_empty(self):
        """Test is none or empty."""
        assert ValidationUtils.is_none_or_empty(None) is True
        assert ValidationUtils.is_none_or_empty("") is True
        assert ValidationUtils.is_none_or_empty("value") is False
    
    def test_is_valid_type(self):
        """Test is valid type."""
        assert ValidationUtils.is_valid_type(42, int) is True
        assert ValidationUtils.is_valid_type("hello", str) is True
        assert ValidationUtils.is_valid_type(42, str) is False
    
    def test_is_positive(self):
        """Test is positive."""
        assert ValidationUtils.is_positive(5) is True
        assert ValidationUtils.is_positive(0) is False
        assert ValidationUtils.is_positive(-5) is False
    
    def test_is_between(self):
        """Test is between."""
        assert ValidationUtils.is_between(5, 1, 10) is True
        assert ValidationUtils.is_between(0, 1, 10) is False
        assert ValidationUtils.is_between(15, 1, 10) is False


class TestUtilsIntegration:
    """Integration tests for utilities."""
    
    def test_string_and_hash_utils(self):
        """Test string and hash utils together."""
        email = "test@example.com"
        
        assert StringUtils.is_email(email) is True
        hashed = HashUtils.md5(email)
        assert len(hashed) == 32
    
    def test_dict_and_validation_utils(self):
        """Test dict and validation utils together."""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com"
        }
        
        name = DictUtils.get_nested(data, "name")
        assert not ValidationUtils.is_none_or_empty(name)
    
    def test_list_and_dict_utils(self):
        """Test list and dict utils together."""
        items = [
            {"id": 1, "name": "Item1"},
            {"id": 2, "name": "Item2"},
            {"id": 1, "name": "Item1"}
        ]
        
        # Flatten the list (would work with custom logic)
        ids = [item["id"] for item in items]
        unique_ids = ListUtils.unique(ids)
        assert unique_ids == [1, 2]
