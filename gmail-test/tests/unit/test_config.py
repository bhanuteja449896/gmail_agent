"""Tests for configuration module."""

import pytest
import json
import tempfile
import os
from src.config import (
    Config, Environment, DatabaseConfig, LoggingConfig, SecurityConfig,
    APIConfig, EmailConfig, ConfigValidator, FeatureFlags,
    ConfigurationRegistry, ConfigurationMerger
)


class TestEnvironmentEnum:
    """Test Environment enum."""
    
    def test_environment_development(self):
        """Test development environment."""
        env = Environment.DEVELOPMENT
        assert env.value == "development"
    
    def test_environment_production(self):
        """Test production environment."""
        env = Environment.PRODUCTION
        assert env.value == "production"
    
    def test_all_environments(self):
        """Test all environments."""
        assert len(Environment) == 4
        envs = {e.value for e in Environment}
        assert "development" in envs
        assert "testing" in envs


class TestDatabaseConfig:
    """Test DatabaseConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "gmail_agent"
    
    def test_custom_values(self):
        """Test custom values."""
        config = DatabaseConfig(
            host="db.example.com",
            port=3306,
            username="admin"
        )
        assert config.host == "db.example.com"
        assert config.port == 3306
        assert config.username == "admin"


class TestLoggingConfig:
    """Test LoggingConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.backup_count == 5
    
    def test_custom_values(self):
        """Test custom values."""
        config = LoggingConfig(level="DEBUG", backup_count=10)
        assert config.level == "DEBUG"
        assert config.backup_count == 10


class TestSecurityConfig:
    """Test SecurityConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = SecurityConfig()
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expiry_hours == 24
    
    def test_cors_origins(self):
        """Test CORS origins."""
        origins = ["http://localhost:3000", "https://example.com"]
        config = SecurityConfig(cors_origins=origins)
        assert config.cors_origins == origins


class TestAPIConfig:
    """Test APIConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 4
    
    def test_rate_limiting(self):
        """Test rate limiting."""
        config = APIConfig()
        assert config.rate_limit_requests == 1000
        assert config.rate_limit_window == 3600


class TestEmailConfig:
    """Test EmailConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = EmailConfig()
        assert config.max_batch_size == 100
        assert config.retry_attempts == 3
    
    def test_attachment_limits(self):
        """Test attachment limits."""
        config = EmailConfig()
        assert config.max_attachments == 10
        assert config.max_attachment_size == 26214400


class TestConfig:
    """Test main Config class."""
    
    def test_initialization_development(self):
        """Test initialization with development environment."""
        config = Config("development")
        assert config.debug is True
        assert config.environment == Environment.DEVELOPMENT
    
    def test_initialization_production(self):
        """Test initialization with production environment."""
        config = Config("production")
        assert config.debug is False
        assert config.environment == Environment.PRODUCTION
    
    def test_config_components(self):
        """Test all config components."""
        config = Config()
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.email, EmailConfig)
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        config = Config()
        config_dict = config.to_dict()
        assert "environment" in config_dict
        assert "database" in config_dict
        assert "api" in config_dict
    
    def test_to_json(self):
        """Test converting to JSON."""
        config = Config()
        json_str = config.to_json()
        data = json.loads(json_str)
        assert "environment" in data
        assert "database" in data
    
    def test_cache_settings(self):
        """Test cache settings."""
        config = Config()
        assert config.cache_ttl == 3600
        assert config.enable_cache is True
    
    def test_monitoring_settings(self):
        """Test monitoring settings."""
        config = Config()
        assert config.enable_monitoring is True
        assert config.enable_metrics is True
    
    def test_from_file_json(self):
        """Test loading from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"database": {"host": "db.local"}}, f)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                assert config.database.host == "db.local"
            finally:
                os.unlink(f.name)
    
    def test_from_file_not_found(self):
        """Test loading from non-existent file."""
        config = Config.from_file("/nonexistent/path.json")
        assert config is not None
    
    def test_load_from_environment(self):
        """Test loading from environment variables."""
        os.environ["GMAIL_AGENT_API_PORT"] = "9000"
        config = Config()
        assert config.api.port == 9000
        del os.environ["GMAIL_AGENT_API_PORT"]


class TestConfigValidator:
    """Test ConfigValidator."""
    
    def test_valid_config(self):
        """Test validation of valid config."""
        config = Config()
        errors = ConfigValidator.validate_config(config)
        assert len(errors) == 0
    
    def test_invalid_database_host(self):
        """Test validation with invalid database host."""
        config = Config()
        config.database.host = ""
        errors = ConfigValidator.validate_config(config)
        assert len(errors) > 0
        assert any("host" in e.lower() for e in errors)
    
    def test_invalid_port(self):
        """Test validation with invalid port."""
        config = Config()
        config.api.port = 99999
        errors = ConfigValidator.validate_config(config)
        assert len(errors) > 0
    
    def test_invalid_secret_key(self):
        """Test validation with invalid secret key."""
        config = Config()
        config.security.secret_key = "short"
        errors = ConfigValidator.validate_config(config)
        assert len(errors) > 0
    
    def test_invalid_retry_attempts(self):
        """Test validation with invalid retry attempts."""
        config = Config()
        config.email.retry_attempts = 0
        errors = ConfigValidator.validate_config(config)
        assert len(errors) > 0


class TestFeatureFlags:
    """Test FeatureFlags."""
    
    def test_default_flags(self):
        """Test default flags."""
        flags = FeatureFlags()
        assert flags.is_enabled("enable_api") is True
        assert flags.is_enabled("enable_webhooks") is False
    
    def test_enable_feature(self):
        """Test enabling feature."""
        flags = FeatureFlags()
        flags.enable_feature("enable_webhooks")
        assert flags.is_enabled("enable_webhooks") is True
    
    def test_disable_feature(self):
        """Test disabling feature."""
        flags = FeatureFlags()
        flags.disable_feature("enable_api")
        assert flags.is_enabled("enable_api") is False
    
    def test_toggle_feature(self):
        """Test toggling feature."""
        flags = FeatureFlags()
        result = flags.toggle_feature("enable_webhooks")
        assert result is True
        assert flags.is_enabled("enable_webhooks") is True
        
        result = flags.toggle_feature("enable_webhooks")
        assert result is False
        assert flags.is_enabled("enable_webhooks") is False
    
    def test_all_features(self):
        """Test all features."""
        flags = FeatureFlags()
        assert len(flags.flags) >= 8


class TestConfigurationRegistry:
    """Test ConfigurationRegistry."""
    
    def test_register_config(self):
        """Test registering configuration."""
        registry = ConfigurationRegistry()
        config = Config("development")
        registry.register("dev", config)
        assert registry.get_config("dev") == config
    
    def test_active_config(self):
        """Test setting active configuration."""
        registry = ConfigurationRegistry()
        dev_config = Config("development")
        prod_config = Config("production")
        
        registry.register("dev", dev_config)
        registry.register("prod", prod_config)
        
        assert registry.active_config == "dev"
        
        registry.set_active("prod")
        assert registry.active_config == "prod"
        assert registry.get_config().environment == Environment.PRODUCTION
    
    def test_get_active_config(self):
        """Test getting active configuration."""
        registry = ConfigurationRegistry()
        config = Config("development")
        registry.register("dev", config)
        
        active_config = registry.get_config()
        assert active_config.environment == Environment.DEVELOPMENT
    
    def test_get_config_not_found(self):
        """Test getting non-existent configuration."""
        registry = ConfigurationRegistry()
        with pytest.raises(ValueError):
            registry.get_config("nonexistent")
    
    def test_set_active_not_found(self):
        """Test setting non-existent configuration as active."""
        registry = ConfigurationRegistry()
        with pytest.raises(ValueError):
            registry.set_active("nonexistent")


class TestConfigurationMerger:
    """Test ConfigurationMerger."""
    
    def test_merge_configs(self):
        """Test merging configurations."""
        config1 = Config("development")
        config1.database.host = "db1.local"
        
        config2 = Config("testing")
        config2.api.port = 9000
        
        merged = ConfigurationMerger.merge_configs(config1, config2)
        assert merged is not None
    
    def test_merge_multiple(self):
        """Test merging multiple configurations."""
        configs = [Config() for _ in range(3)]
        merged = ConfigurationMerger.merge_configs(*configs)
        assert merged is not None


class TestConfigIntegration:
    """Integration tests for configuration."""
    
    def test_full_config_workflow(self):
        """Test full configuration workflow."""
        # Create config
        config = Config("development")
        
        # Validate config
        errors = ConfigValidator.validate_config(config)
        assert len(errors) == 0
        
        # Convert to dict and back
        config_dict = config.to_dict()
        assert config_dict is not None
    
    def test_registry_workflow(self):
        """Test registry workflow."""
        registry = ConfigurationRegistry()
        
        dev_config = Config("development")
        prod_config = Config("production")
        
        registry.register("dev", dev_config)
        registry.register("prod", prod_config)
        
        # Validate both
        assert ConfigValidator.validate_config(registry.get_config("dev")) == []
        
        registry.set_active("prod")
        assert registry.get_config().environment == Environment.PRODUCTION


class TestConfigEdgeCases:
    """Test edge cases."""
    
    def test_empty_secret_key(self):
        """Test empty secret key."""
        config = Config()
        config.security.secret_key = ""
        errors = ConfigValidator.validate_config(config)
        assert len(errors) > 0
    
    def test_zero_workers(self):
        """Test zero workers."""
        config = Config()
        config.api.workers = 0
        assert config.api.workers == 0
    
    def test_negative_port(self):
        """Test negative port."""
        config = Config()
        config.api.port = -1
        errors = ConfigValidator.validate_config(config)
        assert len(errors) > 0
    
    def test_large_pool_size(self):
        """Test large pool size."""
        config = Config()
        config.database.pool_size = 1000
        assert config.database.pool_size == 1000
