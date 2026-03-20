"""Custom exceptions for Zoho Vertical Studio SDK."""

from __future__ import annotations

from typing import Optional


class ZohoAPIError(Exception):
    """Base exception for all Zoho API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r})"
        )


class ZohoAuthError(ZohoAPIError):
    """Raised when authentication or authorization fails (HTTP 401/403)."""


class ZohoRateLimitError(ZohoAPIError):
    """Raised when the API rate limit is exceeded (HTTP 429)."""

    def __init__(self, message: str = "API rate limit exceeded", **kwargs):
        super().__init__(message, **kwargs)


class ZohoNotFoundError(ZohoAPIError):
    """Raised when the requested resource is not found (HTTP 404)."""


class ZohoValidationError(ZohoAPIError):
    """Raised when the request payload is invalid (HTTP 400)."""


class ZohoServerError(ZohoAPIError):
    """Raised on 5xx server errors."""
