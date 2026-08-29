"""
Temporal Filtering and Leakage Protection Module.

Enforces strict causal time boundaries: records occurring after `as_of_timestamp`
are filtered out BEFORE any feature aggregation or model evaluation occurs.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, TypeVar, Union

T = TypeVar("T")


def filter_by_timestamp(
    items: Iterable[T],
    as_of_timestamp: float,
    timestamp_getter: Optional[Callable[[T], float]] = None,
) -> List[T]:
    """
    Strictly filters a collection of time-indexed items to items with timestamp <= as_of_timestamp.

    Args:
        items: Iterable sequence of dataclasses, dicts, or objects.
        as_of_timestamp: Target time horizon.
        timestamp_getter: Optional extractor function. If None, inspects `.timestamp` or `['timestamp']`.

    Returns:
        List of items occurring on or before `as_of_timestamp`, ordered chronologically.
    """
    as_of = float(as_of_timestamp)
    filtered: List[T] = []

    for item in items:
        if timestamp_getter is not None:
            t = float(timestamp_getter(item))
        elif isinstance(item, dict):
            t = float(item.get("timestamp", 0.0))
        elif hasattr(item, "timestamp"):
            t = float(getattr(item, "timestamp"))
        else:
            raise AttributeError(f"Cannot extract timestamp from item of type {type(item)}")

        if t <= as_of:
            filtered.append(item)

    # Return chronologically sorted items
    if timestamp_getter is not None:
        return sorted(filtered, key=timestamp_getter)
    elif filtered and isinstance(filtered[0], dict):
        return sorted(filtered, key=lambda x: float(x.get("timestamp", 0.0)))
    elif filtered and hasattr(filtered[0], "timestamp"):
        return sorted(filtered, key=lambda x: float(getattr(x, "timestamp")))
    return filtered


def validate_zero_leakage(
    records: Sequence[Any],
    as_of_timestamp: float,
) -> bool:
    """
    Validates that no record in `records` has a timestamp strictly greater than `as_of_timestamp`.
    Raises a ValueError if future leakage is detected.
    """
    as_of = float(as_of_timestamp)
    for idx, r in enumerate(records):
        t = float(r.get("timestamp", 0.0) if isinstance(r, dict) else getattr(r, "timestamp", 0.0))
        if t > as_of:
            raise ValueError(
                f"Temporal Leakage Violation: Record at index {idx} has timestamp {t} > as_of_timestamp {as_of}!"
            )
    return True
