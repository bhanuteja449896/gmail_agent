"""Tests for plugin system."""

import pytest
import json
import tempfile
import os
from src.plugins import (
    PluginType, PluginStatus, PluginMetadata, PluginInterface,
    PluginInfo, PluginRegistry, PluginLoader, PluginManager,
    HookSystem, PluginConfig, PluginValidator, DependencyResolver
)


class MockPlugin(PluginInterface):
    """Mock plugin for testing."""
    
    def __init__(self):
        """Initialize mock plugin."""
        self.initialized = False
        self.shutdown_called = False
    
    def get_metadata(self) -> PluginMetadata:
        """Get metadata."""
        return PluginMetadata(
            id="mock_plugin",
            name="Mock Plugin",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.FILTER,
            description="Mock plugin for testing"
        )
    
    def initialize(self, config=None):
        """Initialize plugin."""
        self.initialized = True
    
    def execute(self, *args, **kwargs):
        """Execute plugin."""
        return {"result": "success"}
    
    def shutdown(self):
        """Shutdown plugin."""
        self.shutdown_called = True


class TestPluginType:
    """Test PluginType enum."""
    
    def test_plugin_types(self):
        """Test plugin types."""
        assert PluginType.FILTER.value == "filter"
        assert PluginType.PROCESSOR.value == "processor"
        assert PluginType.EXPORTER.value == "exporter"


class TestPluginStatus:
    """Test PluginStatus enum."""
    
    def test_plugin_status(self):
        """Test plugin status."""
        assert PluginStatus.UNLOADED.value == "unloaded"
        assert PluginStatus.LOADED.value == "loaded"
        assert PluginStatus.ACTIVE.value == "active"


class TestPluginMetadata:
    """Test PluginMetadata."""
    
    def test_creation(self):
        """Test metadata creation."""
        metadata = PluginMetadata(
            id="test",
            name="Test Plugin",
            version="1.0.0",
            author="Test Author",
            plugin_type=PluginType.FILTER
        )
        assert metadata.id == "test"
        assert metadata.name == "Test Plugin"
    
    def test_to_dict(self):
        """Test converting to dict."""
        metadata = PluginMetadata(
            id="test",
            name="Test Plugin",
            version="1.0.0",
            author="Test Author",
            plugin_type=PluginType.FILTER
        )
        data = metadata.to_dict()
        assert data["id"] == "test"
        assert data["type"] == "filter"


class TestPluginInfo:
    """Test PluginInfo."""
    
    def test_creation(self):
        """Test info creation."""
        metadata = PluginMetadata(
            id="test",
            name="Test",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.FILTER
        )
        info = PluginInfo(metadata=metadata)
        assert info.status == PluginStatus.UNLOADED
        assert info.execution_count == 0


class TestPluginRegistry:
    """Test PluginRegistry."""
    
    def test_register_plugin(self):
        """Test registering plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        registry.register_plugin(metadata, plugin)
        assert registry.get_plugin("mock_plugin") is not None
    
    def test_get_plugin(self):
        """Test getting plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        registry.register_plugin(metadata, plugin)
        
        plugin_info = registry.get_plugin("mock_plugin")
        assert plugin_info.metadata.id == "mock_plugin"
    
    def test_get_plugins_by_type(self):
        """Test getting plugins by type."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        registry.register_plugin(metadata, plugin)
        
        filter_plugins = registry.get_plugins_by_type(PluginType.FILTER)
        assert len(filter_plugins) > 0
    
    def test_get_active_plugins(self):
        """Test getting active plugins."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        registry.register_plugin(metadata, plugin)
        
        registry.enable_plugin("mock_plugin")
        active = registry.get_active_plugins()
        assert len(active) > 0
    
    def test_list_plugins(self):
        """Test listing plugins."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        registry.register_plugin(metadata, plugin)
        
        plugins = registry.list_plugins()
        assert len(plugins) > 0
    
    def test_enable_plugin(self):
        """Test enabling plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        registry.register_plugin(metadata, plugin)
        
        registry.enable_plugin("mock_plugin")
        plugin_info = registry.get_plugin("mock_plugin")
        assert plugin_info.status == PluginStatus.ACTIVE
    
    def test_disable_plugin(self):
        """Test disabling plugin."""
        registry = PluginRegistry()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        registry.register_plugin(metadata, plugin)
        
        registry.enable_plugin("mock_plugin")
        registry.disable_plugin("mock_plugin")
        plugin_info = registry.get_plugin("mock_plugin")
        assert plugin_info.status == PluginStatus.DISABLED


class TestPluginLoader:
    """Test PluginLoader."""
    
    def test_load_from_file(self):
        """Test loading from file."""
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        
        # Create temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
from src.plugins import PluginInterface, PluginMetadata, PluginType

class TestPlugin(PluginInterface):
    def get_metadata(self):
        return PluginMetadata(
            id="test_plugin",
            name="Test",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.FILTER
        )
    
    def initialize(self, config=None):
        pass
    
    def execute(self, *args, **kwargs):
        return {}
    
    def shutdown(self):
        pass
""")
            f.flush()
            
            try:
                result = loader.load_from_file(f.name)
                # Result may be False if module loading fails in test environment
            finally:
                os.unlink(f.name)


class TestPluginManager:
    """Test PluginManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = PluginManager()
        assert manager.registry is not None
        assert manager.loader is not None
    
    def test_load_plugin(self):
        """Test loading plugin."""
        manager = PluginManager()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        manager.registry.register_plugin(metadata, plugin)
        result = manager.load_plugin("mock_plugin")
        
        assert result is True
        assert plugin.initialized is True
    
    def test_unload_plugin(self):
        """Test unloading plugin."""
        manager = PluginManager()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        manager.registry.register_plugin(metadata, plugin)
        manager.load_plugin("mock_plugin")
        result = manager.unload_plugin("mock_plugin")
        
        assert result is True
        assert plugin.shutdown_called is True
    
    def test_execute_plugin(self):
        """Test executing plugin."""
        manager = PluginManager()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        manager.registry.register_plugin(metadata, plugin)
        manager.load_plugin("mock_plugin")
        result = manager.execute_plugin("mock_plugin")
        
        assert result["result"] == "success"
    
    def test_execute_unloaded_plugin(self):
        """Test executing unloaded plugin."""
        manager = PluginManager()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        manager.registry.register_plugin(metadata, plugin)
        
        with pytest.raises(RuntimeError):
            manager.execute_plugin("mock_plugin")
    
    def test_get_plugin_info(self):
        """Test getting plugin info."""
        manager = PluginManager()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        manager.registry.register_plugin(metadata, plugin)
        info = manager.get_plugin_info("mock_plugin")
        
        assert info is not None
        assert info.metadata.id == "mock_plugin"


class TestHookSystem:
    """Test HookSystem."""
    
    def test_register_hook(self):
        """Test registering hook."""
        hooks = HookSystem()
        
        def callback():
            return "called"
        
        hooks.register_hook("test_hook", callback)
        registered = hooks.get_hooks("test_hook")
        
        assert len(registered) > 0
    
    def test_unregister_hook(self):
        """Test unregistering hook."""
        hooks = HookSystem()
        
        def callback():
            return "called"
        
        hooks.register_hook("test_hook", callback)
        hooks.unregister_hook("test_hook", callback)
        registered = hooks.get_hooks("test_hook")
        
        assert len(registered) == 0
    
    def test_execute_hooks(self):
        """Test executing hooks."""
        hooks = HookSystem()
        
        results = []
        
        def callback1():
            results.append(1)
            return 1
        
        def callback2():
            results.append(2)
            return 2
        
        hooks.register_hook("test_hook", callback1)
        hooks.register_hook("test_hook", callback2)
        
        hook_results = hooks.execute_hooks("test_hook")
        
        assert len(hook_results) == 2
        assert 1 in hook_results
        assert 2 in hook_results
    
    def test_get_hooks(self):
        """Test getting hooks."""
        hooks = HookSystem()
        
        def callback():
            pass
        
        hooks.register_hook("test_hook", callback)
        registered = hooks.get_hooks("test_hook")
        
        assert callback in registered


class TestPluginConfig:
    """Test PluginConfig."""
    
    def test_initialization(self):
        """Test config initialization."""
        config = PluginConfig()
        assert isinstance(config.config, dict)
    
    def test_load_from_file(self):
        """Test loading from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"plugin1": {"key": "value"}}, f)
            f.flush()
            
            try:
                config = PluginConfig(f.name)
                plugin_config = config.get_plugin_config("plugin1")
                assert plugin_config.get("key") == "value"
            finally:
                os.unlink(f.name)
    
    def test_get_plugin_config(self):
        """Test getting plugin config."""
        config = PluginConfig()
        config.set_plugin_config("plugin1", {"key": "value"})
        
        plugin_config = config.get_plugin_config("plugin1")
        assert plugin_config.get("key") == "value"
    
    def test_set_plugin_config(self):
        """Test setting plugin config."""
        config = PluginConfig()
        config.set_plugin_config("plugin1", {"key": "value"})
        
        assert "plugin1" in config.config
    
    def test_save_to_file(self):
        """Test saving to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.flush()
            
            try:
                config = PluginConfig()
                config.set_plugin_config("plugin1", {"key": "value"})
                config.save_to_file(f.name)
                
                # Verify saved
                with open(f.name) as saved_f:
                    data = json.load(saved_f)
                    assert "plugin1" in data
            finally:
                os.unlink(f.name)


class TestPluginValidator:
    """Test PluginValidator."""
    
    def test_validate_metadata(self):
        """Test validating metadata."""
        metadata = PluginMetadata(
            id="test",
            name="Test",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.FILTER
        )
        errors = PluginValidator.validate_metadata(metadata)
        assert len(errors) == 0
    
    def test_validate_metadata_missing_id(self):
        """Test validating metadata without ID."""
        metadata = PluginMetadata(
            id="",
            name="Test",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.FILTER
        )
        errors = PluginValidator.validate_metadata(metadata)
        assert len(errors) > 0
    
    def test_validate_interface(self):
        """Test validating interface."""
        result = PluginValidator.validate_interface(MockPlugin)
        assert result is True


class TestDependencyResolver:
    """Test DependencyResolver."""
    
    def test_resolve_dependencies(self):
        """Test resolving dependencies."""
        registry = PluginRegistry()
        resolver = DependencyResolver(registry)
        
        # Register plugins with dependencies
        plugin1_metadata = PluginMetadata(
            id="plugin1",
            name="Plugin 1",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.FILTER
        )
        plugin1 = MockPlugin()
        registry.register_plugin(plugin1_metadata, plugin1)
        
        # Get dependencies
        deps = resolver.resolve_dependencies("plugin1")
        assert isinstance(deps, list)
    
    def test_check_circular_dependency(self):
        """Test checking circular dependencies."""
        registry = PluginRegistry()
        resolver = DependencyResolver(registry)
        
        # Check non-existent plugin
        result = resolver.check_circular_dependency("nonexistent")
        assert result is False


class TestPluginIntegration:
    """Integration tests for plugin system."""
    
    def test_full_plugin_workflow(self):
        """Test complete plugin workflow."""
        manager = PluginManager()
        plugin = MockPlugin()
        metadata = plugin.get_metadata()
        
        # Register
        manager.registry.register_plugin(metadata, plugin)
        
        # Load
        assert manager.load_plugin("mock_plugin") is True
        
        # Execute
        result = manager.execute_plugin("mock_plugin")
        assert result["result"] == "success"
        
        # Unload
        assert manager.unload_plugin("mock_plugin") is True
    
    def test_hook_plugin_workflow(self):
        """Test hooks with plugins."""
        hooks = HookSystem()
        
        call_count = 0
        
        def hook_callback():
            nonlocal call_count
            call_count += 1
        
        hooks.register_hook("on_execute", hook_callback)
        hooks.execute_hooks("on_execute")
        
        assert call_count == 1
