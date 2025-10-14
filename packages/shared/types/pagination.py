"""Pagination types and utilities.

This module provides types and utilities for handling paginated data.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar, Union, Dict, Any, Literal

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from .common import (
    T,
    PageSize,
    PageNumber,
    TotalCount,
    Offset,
    Limit,
    NonNegativeInt,
    PositiveInt
)

# Pagination type variables
TItem = TypeVar('TItem')

# Sort direction
SortDirection: TypeAlias = Literal['asc', 'desc']

@dataclass(frozen=True)
class Sort:
    """Sort specification for paginated queries."""
    
    field: str
    direction: SortDirection = 'asc'
    
    def __post_init__(self) -> None:
        if self.direction not in ('asc', 'desc'):
            raise ValueError(f"Sort direction must be 'asc' or 'desc', got: {self.direction}")
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            'field': self.field,
            'direction': self.direction
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> Sort:
        """Create Sort from dictionary."""
        return cls(
            field=data['field'],
            direction=data.get('direction', 'asc')  # type: ignore
        )
    
    @classmethod
    def asc(cls, field: str) -> Sort:
        """Create ascending sort."""
        return cls(field=field, direction='asc')
    
    @classmethod
    def desc(cls, field: str) -> Sort:
        """Create descending sort."""
        return cls(field=field, direction='desc')

@dataclass(frozen=True)
class Pagination:
    """Pagination parameters for queries."""
    
    page: PageNumber = 1
    size: PageSize = 20
    sorts: Optional[List[Sort]] = None
    
    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError(f"Page must be >= 1, got: {self.page}")
        if self.size < 1:
            raise ValueError(f"Size must be >= 1, got: {self.size}")
        if self.size > 1000:
            raise ValueError(f"Size must be <= 1000, got: {self.size}")
    
    @property
    def offset(self) -> Offset:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> Limit:
        """Get limit for database queries."""
        return self.size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            'page': self.page,
            'size': self.size
        }
        if self.sorts:
            result['sorts'] = [sort.to_dict() for sort in self.sorts]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Pagination:
        """Create Pagination from dictionary."""
        sorts = None
        if 'sorts' in data and data['sorts']:
            sorts = [Sort.from_dict(sort_data) for sort_data in data['sorts']]
        
        return cls(
            page=data.get('page', 1),
            size=data.get('size', 20),
            sorts=sorts
        )
    
    def next_page(self) -> Pagination:
        """Get pagination for next page."""
        return Pagination(
            page=self.page + 1,
            size=self.size,
            sorts=self.sorts
        )
    
    def prev_page(self) -> Optional[Pagination]:
        """Get pagination for previous page."""
        if self.page <= 1:
            return None
        return Pagination(
            page=self.page - 1,
            size=self.size,
            sorts=self.sorts
        )
    
    def with_page(self, page: PageNumber) -> Pagination:
        """Create new pagination with different page."""
        return Pagination(
            page=page,
            size=self.size,
            sorts=self.sorts
        )
    
    def with_size(self, size: PageSize) -> Pagination:
        """Create new pagination with different size."""
        return Pagination(
            page=self.page,
            size=size,
            sorts=self.sorts
        )
    
    def with_sorts(self, sorts: List[Sort]) -> Pagination:
        """Create new pagination with different sorts."""
        return Pagination(
            page=self.page,
            size=self.size,
            sorts=sorts
        )

@dataclass(frozen=True)
class PageInfo:
    """Information about pagination state."""
    
    page: PageNumber
    size: PageSize
    total_items: TotalCount
    total_pages: NonNegativeInt
    has_next: bool
    has_prev: bool
    
    @classmethod
    def from_pagination(cls, pagination: Pagination, total_items: TotalCount) -> PageInfo:
        """Create PageInfo from Pagination and total count."""
        total_pages = max(1, (total_items + pagination.size - 1) // pagination.size)
        
        return cls(
            page=pagination.page,
            size=pagination.size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'page': self.page,
            'size': self.size,
            'total_items': self.total_items,
            'total_pages': self.total_pages,
            'has_next': self.has_next,
            'has_prev': self.has_prev
        }

@dataclass(frozen=True)
class Page(Generic[TItem]):
    """Paginated data container."""
    
    items: List[TItem]
    page_info: PageInfo
    
    @property
    def is_empty(self) -> bool:
        """Check if page is empty."""
        return len(self.items) == 0
    
    @property
    def item_count(self) -> int:
        """Get number of items in this page."""
        return len(self.items)
    
    def map(self, func) -> Page:
        """Transform items in the page."""
        from typing import Callable
        mapped_items = [func(item) for item in self.items]
        return Page(items=mapped_items, page_info=self.page_info)
    
    def filter(self, predicate) -> Page[TItem]:
        """Filter items in the page (may change item count)."""
        from typing import Callable
        filtered_items = [item for item in self.items if predicate(item)]
        # Note: This changes the item count but keeps the same page_info
        # In practice, filtering should be done at the query level
        return Page(items=filtered_items, page_info=self.page_info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'items': [
                item.to_dict() if hasattr(item, 'to_dict') else item
                for item in self.items
            ],
            'page_info': self.page_info.to_dict()
        }
    
    @classmethod
    def empty(cls, pagination: Pagination) -> Page[TItem]:
        """Create an empty page."""
        page_info = PageInfo.from_pagination(pagination, 0)
        return cls(items=[], page_info=page_info)
    
    @classmethod
    def create(
        cls,
        items: List[TItem],
        pagination: Pagination,
        total_items: TotalCount
    ) -> Page[TItem]:
        """Create a page from items and pagination info."""
        page_info = PageInfo.from_pagination(pagination, total_items)
        return cls(items=items, page_info=page_info)

# Cursor-based pagination types
@dataclass(frozen=True)
class Cursor:
    """Cursor for cursor-based pagination."""
    
    value: str
    is_next: bool = True  # True for next, False for previous
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'value': self.value,
            'is_next': self.is_next
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Cursor:
        """Create Cursor from dictionary."""
        return cls(
            value=data['value'],
            is_next=data.get('is_next', True)
        )

@dataclass(frozen=True)
class CursorPagination:
    """Cursor-based pagination parameters."""
    
    cursor: Optional[Cursor] = None
    limit: Limit = 20
    sorts: Optional[List[Sort]] = None
    
    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError(f"Limit must be >= 1, got: {self.limit}")
        if self.limit > 1000:
            raise ValueError(f"Limit must be <= 1000, got: {self.limit}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {'limit': self.limit}
        if self.cursor:
            result['cursor'] = self.cursor.to_dict()
        if self.sorts:
            result['sorts'] = [sort.to_dict() for sort in self.sorts]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CursorPagination:
        """Create CursorPagination from dictionary."""
        cursor = None
        if 'cursor' in data and data['cursor']:
            cursor = Cursor.from_dict(data['cursor'])
        
        sorts = None
        if 'sorts' in data and data['sorts']:
            sorts = [Sort.from_dict(sort_data) for sort_data in data['sorts']]
        
        return cls(
            cursor=cursor,
            limit=data.get('limit', 20),
            sorts=sorts
        )

@dataclass(frozen=True)
class CursorPage(Generic[TItem]):
    """Cursor-based paginated data container."""
    
    items: List[TItem]
    next_cursor: Optional[Cursor]
    prev_cursor: Optional[Cursor]
    has_next: bool
    has_prev: bool
    
    @property
    def is_empty(self) -> bool:
        """Check if page is empty."""
        return len(self.items) == 0
    
    @property
    def item_count(self) -> int:
        """Get number of items in this page."""
        return len(self.items)
    
    def map(self, func) -> CursorPage:
        """Transform items in the page."""
        from typing import Callable
        mapped_items = [func(item) for item in self.items]
        return CursorPage(
            items=mapped_items,
            next_cursor=self.next_cursor,
            prev_cursor=self.prev_cursor,
            has_next=self.has_next,
            has_prev=self.has_prev
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            'items': [
                item.to_dict() if hasattr(item, 'to_dict') else item
                for item in self.items
            ],
            'has_next': self.has_next,
            'has_prev': self.has_prev
        }
        if self.next_cursor:
            result['next_cursor'] = self.next_cursor.to_dict()
        if self.prev_cursor:
            result['prev_cursor'] = self.prev_cursor.to_dict()
        return result
    
    @classmethod
    def empty(cls) -> CursorPage[TItem]:
        """Create an empty cursor page."""
        return cls(
            items=[],
            next_cursor=None,
            prev_cursor=None,
            has_next=False,
            has_prev=False
        )

# Utility functions
def validate_pagination(pagination: Optional[Pagination]) -> Pagination:
    """Validate and return default pagination if None."""
    if pagination is None:
        return Pagination()
    return pagination

def validate_cursor_pagination(pagination: Optional[CursorPagination]) -> CursorPagination:
    """Validate and return default cursor pagination if None."""
    if pagination is None:
        return CursorPagination()
    return pagination

# Type aliases for common pagination patterns
StringPage: TypeAlias = Page[str]
IntPage: TypeAlias = Page[int]
DictPage: TypeAlias = Page[Dict[str, Any]]

StringCursorPage: TypeAlias = CursorPage[str]
IntCursorPage: TypeAlias = CursorPage[int]
DictCursorPage: TypeAlias = CursorPage[Dict[str, Any]]

# Export all public types and functions
__all__ = [
    # Core types
    'Sort', 'Pagination', 'PageInfo', 'Page',
    
    # Cursor types
    'Cursor', 'CursorPagination', 'CursorPage',
    
    # Utility functions
    'validate_pagination', 'validate_cursor_pagination',
    
    # Type aliases
    'SortDirection', 'StringPage', 'IntPage', 'DictPage',
    'StringCursorPage', 'IntCursorPage', 'DictCursorPage',
]
