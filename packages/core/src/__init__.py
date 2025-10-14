"""Core package source.

Domain-driven design implementation with clean architecture.
"""

# Import only what's needed to avoid circular imports
try:
    from . import entities
except ImportError:
    pass

try:
    from . import value_objects
except ImportError:
    pass

try:
    from . import interfaces
except ImportError:
    pass

__all__ = [
    "entities",
    "interfaces",
]
