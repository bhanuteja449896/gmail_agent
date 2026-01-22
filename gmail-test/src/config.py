"""Extended configuration system for gmail agent."""

import logging
import json
import os
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    username: str = "user"
    password: str = ""
    database: str = "gmail_agent"
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    password_min_length: int = 8
    enable_https: bool = True
    cors_origins: List[str] = None


@dataclass
class APIConfig:
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    timeout: int = 30
    max_request_size: int = 1048576  # 1MB
    rate_limit_requests: int = 1000
    rate_limit_window: int = 3600  # 1 hour


@dataclass
class EmailConfig:
    """Email configuration."""
    max_batch_size: int = 100
    fetch_timeout: int = 30
    max_attachments: int = 10
    max_attachment_size: int = 26214400  # 25MB
    retry_attempts: int = 3
    retry_backoff: float = 2.0


class Config:
    """Main configuration class."""
    
    def __init__(self, environment: str = "development"):
        """Initialize configuration."""
        self.environment = Environment(environment)
        self.debug = environment == "development"
        
        # Load configurations
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        self.api = APIConfig()
        self.email = EmailConfig()
        
        # Additional config
        self.cache_ttl = 3600
        self.enable_cache = True
        self.enable_monitoring = True
        self.enable_metrics = True
        
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_prefix = "GMAIL_AGENT_"
        
        # Load database config
        if os.getenv(f"{env_prefix}DB_HOST"):
            self.database.host = os.getenv(f"{env_prefix}DB_HOST", "localhost")
        
        # Load API config
        if os.getenv(f"{env_prefix}API_PORT"):
            self.api.port = int(os.getenv(f"{env_prefix}API_PORT", 8000))
        
        # Load security config
        if os.getenv(f"{env_prefix}SECRET_KEY"):
            self.security.secret_key = os.getenv(f"{env_prefix}SECRET_KEY")
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """Load configuration from file."""
        config = cls()
        
        if not os.path.exists(file_path):
            logger.warning(f"Config file not found: {file_path}")
            return config
        
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            config._load_from_dict(data)
            logger.info(f"Loaded configuration from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
        
        return config
    
    def _load_from_dict(self, data: Dict) -> None:
        """Load configuration from dictionary."""
        if "database" in data:
            db_data = data["database"]
            self.database.host = db_data.get("host", self.database.host)
            self.database.port = db_data.get("port", self.database.port)
        
        if "api" in data:
            api_data = data["api"]
            self.api.host = api_data.get("host", self.api.host)
            self.api.port = api_data.get("port", self.api.port)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "database": asdict(self.database),
            "logging": asdict(self.logging),
            "security": asdict(self.security),
            "api": asdict(self.api),
            "email": asdict(self.email)
        }
    
    def to_json(self) -> str:
        """Convert configuration to JSON."""
        return json.dumps(self.to_dict(), indent=2)


class ConfigValidator:
    """Validate configuration."""
    
    @staticmethod
    def validate_config(config: Config) -> List[str]:
        """Validate configuration."""
        errors = []
        
        # Validate database
        if not config.database.host:
            errors.append("Database host is required")
        if config.database.port < 1 or config.database.port > 65535:
            errors.append("Invalid database port")
        
        # Validate API
        if config.api.port < 1 or config.api.port > 65535:
            errors.append("Invalid API port")
        
        # Validate security
        if len(config.security.secret_key) < 10:
            errors.append("Secret key too short")
        
        # Validate email
        if config.email.retry_attempts < 1:
            errors.append("Invalid retry attempts")
        
        return errors


class FeatureFlags:
    """Feature flags system."""
    
    def __init__(self):
        """Initialize feature flags."""
        self.flags: Dict[str, bool] = {
            "enable_api": True,
            "enable_cli": True,
            "enable_scheduling": True,
            "enable_webhooks": False,
            "enable_advanced_filters": True,
            "enable_analytics": True,
            "enable_backup": True,
            "enable_sync": False,
        }
    
    def is_enabled(self, feature: str) -> bool:
        """Check if feature is enabled."""
        return self.flags.get(feature, False)
    
    def enable_feature(self, feature: str) -> None:
        """Enable feature."""
        self.flags[feature] = True
        logger.info(f"Enabled feature: {feature}")
    
    def disable_feature(self, feature: str) -> None:
        """Disable feature."""
        self.flags[feature] = False
        logger.info(f"Disabled feature: {feature}")
    
    def toggle_feature(self, feature: str) -> bool:
        """Toggle feature."""
        new_state = not self.flags.get(feature, False)
        self.flags[feature] = new_state
        return new_state


class ConfigurationRegistry:
    """Registry for managing multiple configurations."""
    
    def __init__(self):
        """Initialize configuration registry."""
        self.configs: Dict[str, Config] = {}
        self.active_config: Optional[str] = None
    
    def register(self, name: str, config: Config) -> None:
        """Register configuration."""
        self.configs[name] = config
        if self.active_config is None:
            self.active_config = name
        logger.info(f"Registered configuration: {name}")
    
    def get_config(self, name: str = None) -> Config:
        """Get configuration."""
        if name is None:
            name = self.active_config
        
        if name not in self.configs:
            raise ValueError(f"Configuration not found: {name}")
        
        return self.configs[name]
    
    def set_active(self, name: str) -> None:
        """Set active configuration."""
        if name not in self.configs:
            raise ValueError(f"Configuration not found: {name}")
        
        self.active_config = name
        logger.info(f"Set active configuration: {name}")


class ConfigurationMerger:
    """Merge multiple configurations."""
    
    @staticmethod
    def merge_configs(*configs: Config) -> Config:
        """Merge multiple configurations."""
        merged = Config()
        
        for config in configs:
            # Merge database config
            if hasattr(config, 'database'):
                for key, value in asdict(config.database).items():
                    if value:
                        setattr(merged.database, key, value)
            
            # Merge API config
            if hasattr(config, 'api'):
                for key, value in asdict(config.api).items():
                    if value:
                        setattr(merged.api, key, value)
        
        return merged
