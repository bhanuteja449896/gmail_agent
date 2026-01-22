"""Utility functions and helper classes."""

import logging
import json
import hashlib
import re
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class StringUtils:
    """String utility functions."""
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize string."""
        if not text:
            return ""
        return text.strip().lower()
    
    @staticmethod
    def truncate(text: str, max_length: int = 100) -> str:
        """Truncate string."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    @staticmethod
    def split_camel_case(text: str) -> str:
        """Split camel case string."""
        result = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', result).lower()
    
    @staticmethod
    def is_email(text: str) -> bool:
        """Check if string is email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, text) is not None
    
    @staticmethod
    def is_url(text: str) -> bool:
        """Check if string is URL."""
        pattern = r'^https?://[^\s]+'
        return re.match(pattern, text) is not None
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract emails from text."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text."""
        pattern = r'https?://[^\s]+'
        return re.findall(pattern, text)
    
    @staticmethod
    def to_slug(text: str) -> str:
        """Convert to URL slug."""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')


class HashUtils:
    """Hash utility functions."""
    
    @staticmethod
    def md5(text: str) -> str:
        """Generate MD5 hash."""
        return hashlib.md5(text.encode()).hexdigest()
    
    @staticmethod
    def sha256(text: str) -> str:
        """Generate SHA256 hash."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    @staticmethod
    def hash_file(filepath: str, algorithm: str = 'sha256') -> str:
        """Hash file content."""
        hash_func = hashlib.sha256() if algorithm == 'sha256' else hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file: {e}")
            return ""


class JSONUtils:
    """JSON utility functions."""
    
    @staticmethod
    def safe_dumps(obj: Any, **kwargs) -> str:
        """Safe JSON dumps."""
        try:
            return json.dumps(obj, default=str, **kwargs)
        except Exception as e:
            logger.error(f"Error serializing JSON: {e}")
            return "{}"
    
    @staticmethod
    def safe_loads(text: str) -> Dict[str, Any]:
        """Safe JSON loads."""
        try:
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return {}
    
    @staticmethod
    def pretty_print(obj: Any) -> str:
        """Pretty print JSON."""
        return JSONUtils.safe_dumps(obj, indent=2)


class DateTimeUtils:
    """DateTime utility functions."""
    
    @staticmethod
    def now() -> datetime:
        """Get current datetime."""
        return datetime.now()
    
    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC datetime."""
        from datetime import timezone
        return datetime.now(timezone.utc)
    
    @staticmethod
    def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime."""
        try:
            return dt.strftime(fmt)
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            return ""
    
    @staticmethod
    def parse_datetime(text: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """Parse datetime."""
        try:
            return datetime.strptime(text, fmt)
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            return None
    
    @staticmethod
    def get_relative_time(dt: datetime) -> str:
        """Get relative time string."""
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            return f"{diff.days // 365} years ago"
        elif diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "just now"


class ListUtils:
    """List utility functions."""
    
    @staticmethod
    def flatten(nested_list: List) -> List:
        """Flatten nested list."""
        result = []
        for item in nested_list:
            if isinstance(item, list):
                result.extend(ListUtils.flatten(item))
            else:
                result.append(item)
        return result
    
    @staticmethod
    def unique(items: List) -> List:
        """Get unique items."""
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    
    @staticmethod
    def chunk(items: List, size: int) -> List[List]:
        """Split list into chunks."""
        return [items[i:i + size] for i in range(0, len(items), size)]
    
    @staticmethod
    def zip_dicts(keys: List, values: List) -> Dict:
        """Zip keys and values."""
        return dict(zip(keys, values))


class DictUtils:
    """Dictionary utility functions."""
    
    @staticmethod
    def merge(*dicts: Dict) -> Dict:
        """Merge dictionaries."""
        result = {}
        for d in dicts:
            result.update(d)
        return result
    
    @staticmethod
    def get_nested(d: Dict, path: str, default=None) -> Any:
        """Get nested dictionary value."""
        keys = path.split('.')
        value = d
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value
    
    @staticmethod
    def set_nested(d: Dict, path: str, value: Any) -> None:
        """Set nested dictionary value."""
        keys = path.split('.')
        current = d
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    @staticmethod
    def flatten(d: Dict, parent_key: str = '') -> Dict:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DictUtils.flatten(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)


class EnvironmentUtils:
    """Environment utility functions."""
    
    @staticmethod
    def get_env(key: str, default: Any = None) -> Any:
        """Get environment variable."""
        import os
        value = os.getenv(key)
        if value is None:
            return default
        if value.lower() in ['true', '1', 'yes']:
            return True
        if value.lower() in ['false', '0', 'no']:
            return False
        try:
            return int(value)
        except:
            return value
    
    @staticmethod
    def get_env_list(key: str, separator: str = ',') -> List[str]:
        """Get environment variable as list."""
        import os
        value = os.getenv(key, '')
        if not value:
            return []
        return [item.strip() for item in value.split(separator)]
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production."""
        import os
        return os.getenv('ENV', 'development').lower() == 'production'
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development."""
        import os
        return os.getenv('ENV', 'development').lower() == 'development'


class RetryUtils:
    """Retry utility functions."""
    
    @staticmethod
    def retry(func: Callable, max_attempts: int = 3, delay: float = 1.0) -> Any:
        """Retry function with exponential backoff."""
        import time
        
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)


class ValidationUtils:
    """Validation utility functions."""
    
    @staticmethod
    def is_none_or_empty(value: Any) -> bool:
        """Check if value is None or empty."""
        return value is None or value == ""
    
    @staticmethod
    def is_valid_type(value: Any, expected_type) -> bool:
        """Check if value is valid type."""
        return isinstance(value, expected_type)
    
    @staticmethod
    def is_positive(value: int) -> bool:
        """Check if value is positive."""
        return isinstance(value, int) and value > 0
    
    @staticmethod
    def is_between(value: float, min_val: float, max_val: float) -> bool:
        """Check if value is between min and max."""
        return min_val <= value <= max_val
