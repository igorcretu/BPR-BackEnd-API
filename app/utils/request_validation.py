"""Utility helpers for consistent request parsing and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Optional, Union

from flask import Request


@dataclass(frozen=True)
class PaginationParams:
    """Container for sanitized pagination parameters."""

    page: int
    per_page: int


def _coerce_positive_int(value: Optional[Union[int, str]], default: int, field: str) -> int:
    try:
        coerced = int(value) if value is not None else int(default)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        coerced = int(default)

    if coerced <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return coerced


def get_pagination_params(
    args: Mapping[str, str],
    *,
    default_page: int = 1,
    default_per_page: int = 20,
    max_per_page: int = 100,
) -> PaginationParams:
    """Extract and validate pagination params from a query parameter mapping."""

    page = _coerce_positive_int(args.get("page"), default_page, "page")
    per_page = _coerce_positive_int(args.get("per_page"), default_per_page, "per_page")
    per_page = min(per_page, max_per_page)
    return PaginationParams(page=page, per_page=per_page)


def parse_json_body(request: Request, required_fields: Optional[Iterable[str]] = None) -> dict:
    """Ensure the request contains JSON and optionally validate required fields."""

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be valid JSON")

    if required_fields:
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return payload


def validate_year(year: int, *, earliest: int = 1900, allow_future_years: int = 1) -> None:
    """Validate year bounds to avoid nonsensical values."""

    current_year = datetime.utcnow().year
    max_year = current_year + allow_future_years
    if not isinstance(year, int):
        raise ValueError("Year must be an integer")
    if year < earliest or year > max_year:
        raise ValueError(f"Year must be between {earliest} and {max_year}")


def validate_non_negative_number(field_name: str, value: Optional[float]) -> None:
    if value is None:
        raise ValueError(f"{field_name} is required")
    if float(value) < 0:
        raise ValueError(f"{field_name} cannot be negative")


def validate_positive_number(field_name: str, value: Optional[float]) -> None:
    if value is None:
        raise ValueError(f"{field_name} is required")
    if float(value) <= 0:
        raise ValueError(f"{field_name} must be greater than zero")


def normalize_string(value: Optional[str]) -> Optional[str]:
    """Return a trimmed string or None if empty."""

    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None
