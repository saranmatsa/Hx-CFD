"""
Tool Registry for managing all tool adapters.

The registry maintains a collection of all known tools and their adapters,
providing a central point for tool discovery and management.
"""

from typing import Dict, List, Optional, Type, Callable
from datetime import datetime

from .base import ToolAdapter, DependencyInfo, DependencyStatus, DependencyCategory


class ToolRegistry:
    """
    Central registry for all tool adapters.
    
    The registry provides:
    - Registration of tool adapters
    - Lookup by name, category, or priority
    - Bulk operations on all tools
    - Caching of detection results
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._adapters: Dict[str, ToolAdapter] = {}
        self._categories: Dict[DependencyCategory, List[str]] = {}
        self._cache: Dict[str, tuple[DependencyInfo, datetime]] = {}
        self._cache_ttl_seconds = 60  # Cache TTL
        self._initialized = True
    
    def register(self, adapter: ToolAdapter) -> None:
        """
        Register a tool adapter.
        
        Args:
            adapter: The tool adapter to register.
        """
        name = adapter.name.lower()
        if name in self._adapters:
            raise ValueError(f"Tool '{name}' is already registered")
        
        self._adapters[name] = adapter
        
        # Add to category index
        category = adapter.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool adapter.
        
        Args:
            name: Name of the tool to unregister.
            
        Returns:
            True if unregistered, False if not found.
        """
        name = name.lower()
        if name not in self._adapters:
            return False
        
        adapter = self._adapters[name]
        category = adapter.category
        
        # Remove from category index
        if category in self._categories and name in self._categories[category]:
            self._categories[category].remove(name)
        
        # Remove from adapters
        del self._adapters[name]
        
        # Clear cache
        self._cache.pop(name, None)
        
        return True
    
    def get(self, name: str) -> Optional[ToolAdapter]:
        """
        Get a tool adapter by name.
        
        Args:
            name: Name of the tool.
            
        Returns:
            The tool adapter, or None if not found.
        """
        return self._adapters.get(name.lower())
    
    def get_all(self) -> List[ToolAdapter]:
        """
        Get all registered tool adapters.
        
        Returns:
            List of all tool adapters.
        """
        return list(self._adapters.values())
    
    def get_by_category(self, category: DependencyCategory) -> List[ToolAdapter]:
        """
        Get all tools in a category.
        
        Args:
            category: The category to filter by.
            
        Returns:
            List of tools in the category.
        """
        names = self._categories.get(category, [])
        return [self._adapters[name] for name in names if name in self._adapters]
    
    def get_by_priority(self, priority: str) -> List[ToolAdapter]:
        """
        Get all tools with a specific priority.
        
        Args:
            priority: The priority to filter by.
            
        Returns:
            List of tools with the priority.
        """
        return [
            adapter for adapter in self._adapters.values()
            if adapter.priority.value == priority
        ]
    
    def get_info(self, name: str, use_cache: bool = True) -> Optional[DependencyInfo]:
        """
        Get dependency info for a tool.
        
        Args:
            name: Name of the tool.
            use_cache: Whether to use cached results.
            
        Returns:
            DependencyInfo, or None if not found.
        """
        name = name.lower()
        
        # Check cache
        if use_cache and name in self._cache:
            info, timestamp = self._cache[name]
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age < self._cache_ttl_seconds:
                return info
        
        # Get from adapter
        adapter = self.get(name)
        if adapter is None:
            return None
        
        info = adapter.get_info()
        
        # Update cache
        self._cache[name] = (info, datetime.utcnow())
        
        return info
    
    def get_all_info(self, use_cache: bool = True) -> List[DependencyInfo]:
        """
        Get dependency info for all tools.
        
        Args:
            use_cache: Whether to use cached results.
            
        Returns:
            List of DependencyInfo for all tools.
        """
        return [
            self.get_info(name, use_cache)
            for name in self._adapters.keys()
        ]
    
    def get_status_summary(self) -> Dict[str, int]:
        """
        Get a summary of tool statuses.
        
        Returns:
            Dictionary with counts by status.
        """
        summary: Dict[str, int] = {
            "total": len(self._adapters),
            "installed": 0,
            "missing": 0,
            "broken": 0,
            "wrong_version": 0,
            "misconfigured": 0,
            "unknown": 0,
        }
        
        for name in self._adapters:
            info = self.get_info(name)
            if info:
                summary[info.status.value] = summary.get(info.status.value, 0) + 1
        
        return summary
    
    def clear_cache(self, name: Optional[str] = None) -> None:
        """
        Clear the cache.
        
        Args:
            name: Specific tool to clear, or None for all.
        """
        if name:
            self._cache.pop(name.lower(), None)
        else:
            self._cache.clear()
    
    def __len__(self) -> int:
        return len(self._adapters)
    
    def __contains__(self, name: str) -> bool:
        return name.lower() in self._adapters
    
    def __iter__(self):
        return iter(self._adapters.values())


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(adapter: ToolAdapter) -> None:
    """Register a tool with the global registry."""
    get_registry().register(adapter)


def get_tool(name: str) -> Optional[ToolAdapter]:
    """Get a tool from the global registry."""
    return get_registry().get(name)


def get_all_tools() -> List[ToolAdapter]:
    """Get all tools from the global registry."""
    return get_registry().get_all()