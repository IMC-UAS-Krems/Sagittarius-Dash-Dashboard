from typing import Dict, Type, Any

from .base import BaseVisualization

visualization_registry: Dict[str, Type[BaseVisualization]] = {}

def register_visualization(viz_type: str):
    """Decorator to register a visualization class."""
    def decorator(cls):
        visualization_registry[viz_type] = cls
        return cls
    return decorator

def get_visualization_class(viz_type: str) -> Type[BaseVisualization]:
    """Get the visualization class for the given type."""
    if viz_type not in visualization_registry:
        raise ValueError(f"Unknown visualization type: {viz_type}")
    return visualization_registry[viz_type]

def create_visualization(viz_type: str, *args: Any, **kwargs: Any) -> BaseVisualization:
    cls = get_visualization_class(viz_type)
    return cls(*args, **kwargs)