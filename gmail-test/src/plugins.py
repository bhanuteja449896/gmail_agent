"""Plugin system for extensibility."""

import logging
import importlib
import inspect
import json
from typing import Any, Dict, List, Optional, Type, Callable
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import sys
import os

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Plugin types."""
    FILTER = "filter"
    PROCESSOR = "processor"
    EXPORTER = "exporter"
    IMPORTER = "importer"
    TRANSFORMER = "transformer"
    VALIDATOR = "validator"
    ANALYZER = "analyzer"
    CUSTOM = "custom"


class PluginStatus(Enum):
    """Plugin status."""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    version: str
    author: str
    plugin_type: PluginType
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "type": self.plugin_type.value,
            "description": self.description,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "config": self.config
        }


class PluginInterface(ABC):
    """Base plugin interface."""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any] = None) -> None:
        """Initialize plugin."""
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute plugin."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown plugin."""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        return True


@dataclass
class PluginInfo:
    """Plugin information."""
    metadata: PluginMetadata
    status: PluginStatus = PluginStatus.UNLOADED
    instance: Optional[PluginInterface] = None
    loaded_at: Optional[str] = None
    error: Optional[str] = None
    execution_count: int = 0
    last_execution_time: Optional[str] = None


class PluginRegistry:
    """Registry for managing plugins."""
    
    def __init__(self):
        """Initialize registry."""
        self.plugins: Dict[str, PluginInfo] = {}
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register_plugin(self, metadata: PluginMetadata, instance: PluginInterface = None) -> None:
        """Register plugin."""
        plugin_info = PluginInfo(
            metadata=metadata,
            instance=instance
        )
        
        self.plugins[metadata.id] = plugin_info
        logger.info(f"Registered plugin: {metadata.id}")
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin by ID."""
        return self.plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInfo]:
        """Get plugins by type."""
        return [p for p in self.plugins.values() if p.metadata.plugin_type == plugin_type]
    
    def get_active_plugins(self) -> List[PluginInfo]:
        """Get active plugins."""
        return [p for p in self.plugins.values() if p.status == PluginStatus.ACTIVE]
    
    def list_plugins(self) -> List[PluginMetadata]:
        """List all plugin metadata."""
        return [p.metadata for p in self.plugins.values()]
    
    def enable_plugin(self, plugin_id: str) -> None:
        """Enable plugin."""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].status = PluginStatus.ACTIVE
            logger.info(f"Enabled plugin: {plugin_id}")
    
    def disable_plugin(self, plugin_id: str) -> None:
        """Disable plugin."""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].status = PluginStatus.DISABLED
            logger.info(f"Disabled plugin: {plugin_id}")


class PluginLoader:
    """Load plugins from various sources."""
    
    def __init__(self, registry: PluginRegistry):
        """Initialize loader."""
        self.registry = registry
    
    def load_from_file(self, file_path: str) -> bool:
        """Load plugin from file."""
        try:
            spec = importlib.util.spec_from_file_location("plugin_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for PluginInterface implementations
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj != PluginInterface:
                    instance = obj()
                    metadata = instance.get_metadata()
                    self.registry.register_plugin(metadata, instance)
                    logger.info(f"Loaded plugin from file: {metadata.id}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")
            return False
    
    def load_from_directory(self, directory_path: str) -> int:
        """Load plugins from directory."""
        count = 0
        try:
            for filename in os.listdir(directory_path):
                if filename.endswith('.py') and not filename.startswith('_'):
                    file_path = os.path.join(directory_path, filename)
                    if self.load_from_file(file_path):
                        count += 1
        except Exception as e:
            logger.error(f"Failed to load plugins from directory: {e}")
        
        return count
    
    def load_from_module(self, module_name: str) -> bool:
        """Load plugin from module."""
        try:
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj != PluginInterface:
                    instance = obj()
                    metadata = instance.get_metadata()
                    self.registry.register_plugin(metadata, instance)
                    logger.info(f"Loaded plugin from module: {metadata.id}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to load plugin from module {module_name}: {e}")
            return False


class PluginManager:
    """Manage plugin lifecycle."""
    
    def __init__(self):
        """Initialize manager."""
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
    
    def load_plugin(self, plugin_id: str, config: Dict[str, Any] = None) -> bool:
        """Load and initialize plugin."""
        plugin_info = self.registry.get_plugin(plugin_id)
        if not plugin_info:
            logger.warning(f"Plugin not found: {plugin_id}")
            return False
        
        try:
            if not plugin_info.instance:
                logger.warning(f"Plugin has no instance: {plugin_id}")
                return False
            
            # Validate config
            if config and not plugin_info.instance.validate_config(config):
                logger.warning(f"Invalid plugin config: {plugin_id}")
                return False
            
            # Initialize
            plugin_info.instance.initialize(config)
            plugin_info.status = PluginStatus.ACTIVE
            plugin_info.loaded_at = str(__import__('datetime').datetime.now())
            
            logger.info(f"Loaded plugin: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error = str(e)
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload plugin."""
        plugin_info = self.registry.get_plugin(plugin_id)
        if not plugin_info:
            return False
        
        try:
            if plugin_info.instance:
                plugin_info.instance.shutdown()
            plugin_info.status = PluginStatus.UNLOADED
            logger.info(f"Unloaded plugin: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False
    
    def execute_plugin(self, plugin_id: str, *args, **kwargs) -> Any:
        """Execute plugin."""
        plugin_info = self.registry.get_plugin(plugin_id)
        if not plugin_info:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        if plugin_info.status != PluginStatus.ACTIVE:
            raise RuntimeError(f"Plugin not active: {plugin_id}")
        
        try:
            result = plugin_info.instance.execute(*args, **kwargs)
            plugin_info.execution_count += 1
            plugin_info.last_execution_time = str(__import__('datetime').datetime.now())
            return result
        except Exception as e:
            logger.error(f"Failed to execute plugin {plugin_id}: {e}")
            raise
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin information."""
        return self.registry.get_plugin(plugin_id)


class HookSystem:
    """System for plugin hooks."""
    
    def __init__(self):
        """Initialize hook system."""
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register hook callback."""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append(callback)
        logger.info(f"Registered hook: {hook_name}")
    
    def unregister_hook(self, hook_name: str, callback: Callable) -> None:
        """Unregister hook callback."""
        if hook_name in self.hooks:
            self.hooks[hook_name].remove(callback)
    
    def execute_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute all callbacks for a hook."""
        results = []
        if hook_name in self.hooks:
            for callback in self.hooks[hook_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Hook callback error: {e}")
        
        return results
    
    def get_hooks(self, hook_name: str) -> List[Callable]:
        """Get hooks for name."""
        return self.hooks.get(hook_name, [])


class PluginConfig:
    """Plugin configuration management."""
    
    def __init__(self, config_file: str = None):
        """Initialize config."""
        self.config: Dict[str, Any] = {}
        if config_file:
            self.load_from_file(config_file)
    
    def load_from_file(self, file_path: str) -> None:
        """Load config from file."""
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith('.json'):
                    self.config = json.load(f)
                # Add YAML support if needed
            logger.info(f"Loaded plugin config: {file_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def get_plugin_config(self, plugin_id: str) -> Dict[str, Any]:
        """Get configuration for plugin."""
        return self.config.get(plugin_id, {})
    
    def set_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> None:
        """Set configuration for plugin."""
        self.config[plugin_id] = config
    
    def save_to_file(self, file_path: str) -> None:
        """Save config to file."""
        try:
            with open(file_path, 'w') as f:
                if file_path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
            logger.info(f"Saved plugin config: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


class PluginValidator:
    """Validate plugins."""
    
    @staticmethod
    def validate_metadata(metadata: PluginMetadata) -> List[str]:
        """Validate plugin metadata."""
        errors = []
        
        if not metadata.id:
            errors.append("Plugin ID is required")
        if not metadata.name:
            errors.append("Plugin name is required")
        if not metadata.version:
            errors.append("Plugin version is required")
        if not metadata.author:
            errors.append("Plugin author is required")
        
        return errors
    
    @staticmethod
    def validate_interface(plugin_class: Type[PluginInterface]) -> bool:
        """Validate plugin implements interface."""
        required_methods = ['get_metadata', 'initialize', 'execute', 'shutdown']
        
        for method in required_methods:
            if not hasattr(plugin_class, method):
                logger.warning(f"Plugin missing method: {method}")
                return False
        
        return True


class DependencyResolver:
    """Resolve plugin dependencies."""
    
    def __init__(self, registry: PluginRegistry):
        """Initialize resolver."""
        self.registry = registry
    
    def resolve_dependencies(self, plugin_id: str) -> List[str]:
        """Resolve plugin dependencies."""
        plugin_info = self.registry.get_plugin(plugin_id)
        if not plugin_info:
            return []
        
        dependencies = []
        for dep in plugin_info.metadata.dependencies:
            if self.registry.get_plugin(dep):
                dependencies.append(dep)
                # Recursively resolve
                dependencies.extend(self.resolve_dependencies(dep))
        
        return list(set(dependencies))  # Remove duplicates
    
    def check_circular_dependency(self, plugin_id: str, visited: set = None) -> bool:
        """Check for circular dependencies."""
        if visited is None:
            visited = set()
        
        if plugin_id in visited:
            return True
        
        visited.add(plugin_id)
        plugin_info = self.registry.get_plugin(plugin_id)
        
        if plugin_info:
            for dep in plugin_info.metadata.dependencies:
                if self.check_circular_dependency(dep, visited):
                    return True
        
        return False
