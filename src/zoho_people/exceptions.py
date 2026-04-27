"""Typed exceptions for Zoho People SDK."""
from __future__ import annotations

from typing import Any, Optional


class ZohoPeopleError(Exception):
    """Base exception for all Zoho People SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        error_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message     = message
        self.status_code = status_code
        self.error_code  = error_code
        self.details     = details or {}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code})"
        )


class ZohoPeopleAuthError(ZohoPeopleError):
    """Authentication / authorization failure (HTTP 401/403 or Zoho error_code 9000)."""


class ZohoPeopleRateLimitError(ZohoPeopleError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str = "Zoho People rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ZohoPeopleNotFoundError(ZohoPeopleError):
    """Resource not found (HTTP 404)."""


class ZohoPeopleValidationError(ZohoPeopleError):
    """Invalid parameters (HTTP 400/422 or Zoho internal status=1)."""


class ZohoPeoplePermissionError(ZohoPeopleError):
    """Operation not permitted for the current user role."""
