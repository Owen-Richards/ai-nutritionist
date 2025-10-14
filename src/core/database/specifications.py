"""Reusable specification implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generic, Iterable, TypeVar

from .abstractions import Specification

T = TypeVar("T")

__all__ = [
    "BaseSpecification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
]


@dataclass(frozen=True)
class BaseSpecification(Generic[T], Specification[T]):
    """Specification backed by a dict of equality filters."""

    filters: Dict[str, Any]

    def is_satisfied_by(self, candidate: T) -> bool:
        return all(getattr(candidate, key, object()) == value for key, value in self.filters.items())

    def to_filters(self) -> Dict[str, Any]:
        return dict(self.filters)

    def __and__(self, other: "Specification[T]") -> "AndSpecification[T]":
        return AndSpecification(self, other)

    def __or__(self, other: "Specification[T]") -> "OrSpecification[T]":
        return OrSpecification(self, other)

    def __invert__(self) -> "NotSpecification[T]":
        return NotSpecification(self)


@dataclass(frozen=True)
class CompositeSpecification(Generic[T], Specification[T]):
    left: Specification[T]
    right: Specification[T]

    def is_satisfied_by(self, candidate: T) -> bool:
        raise NotImplementedError

    def to_filters(self) -> Dict[str, Any]:
        raise NotImplementedError


class AndSpecification(CompositeSpecification[T]):
    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)

    def to_filters(self) -> Dict[str, Any]:
        filters = dict(self.left.to_filters())
        filters.update(self.right.to_filters())
        return filters


class OrSpecification(CompositeSpecification[T]):
    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)

    def to_filters(self) -> Dict[str, Any]:
        return {"": [self.left.to_filters(), self.right.to_filters()]}


class NotSpecification(Generic[T], Specification[T]):
    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)

    def to_filters(self) -> Dict[str, Any]:
        return {"": self._spec.to_filters()}

