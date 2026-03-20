"""
Core HTTP client for Zoho Vertical Studio SDK.

All API sub-classes share a single ZohoVerticalClient instance that handles:
- Base URL construction
- Auth header injection
- Response parsing
- Error mapping
- Optional retry on rate-limit / transient errors
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from requests import Response, Session

from .auth import ZohoOAuthToken
from .exceptions import (
    ZohoAPIError,
    ZohoAuthError,
    ZohoNotFoundError,
    ZohoRateLimitError,
    ZohoServerError,
    ZohoValidationError,
)
from .modules import ModulesAPI
from .records import RecordsAPI
from .metadata import MetadataAPI
from .query import QueryAPI
from .bulk import BulkAPI
from .notifications import NotificationsAPI


class ZohoVerticalClient:
    """
    Entry point for the Zoho Vertical Studio v6 SDK.

    Parameters
    ----------
    auth : ZohoOAuthToken
        Authentication object. Create one with a static token or refresh credentials.
    api_domain : str
        Base API domain, e.g. ``https://zohoverticalapis.com``
    version : str
        API version, default ``v6``.
    timeout : int
        HTTP timeout in seconds.
    max_retries : int
        How many times to retry on rate-limit / 5xx (0 = no retry).
    retry_backoff : float
        Base back-off in seconds between retries.

    Example
    -------
    >>> from zoho_vertical_sdk import ZohoVerticalClient, ZohoOAuthToken
    >>> auth = ZohoOAuthToken(access_token="100xx.abc123")
    >>> client = ZohoVerticalClient(auth=auth, api_domain="https://zohoverticalapis.com")
    >>> modules = client.modules.list_modules()
    """

    DEFAULT_API_DOMAIN = "https://people.zoho.com"
    DEFAULT_VERSION = "v6"

    def __init__(
        self,
        auth: ZohoOAuthToken,
        api_domain: str = DEFAULT_API_DOMAIN,
        version: str = DEFAULT_VERSION,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        self.auth = auth
        self.api_domain = api_domain.rstrip("/")
        self.version = version
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._session: Session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        # Lazily-initialised sub-APIs
        self._modules: Optional[ModulesAPI] = None
        self._records: Optional[RecordsAPI] = None
        self._metadata: Optional[MetadataAPI] = None
        self._query: Optional[QueryAPI] = None
        self._bulk: Optional[BulkAPI] = None
        self._notifications: Optional[NotificationsAPI] = None

    # ------------------------------------------------------------------
    # Sub-API accessors
    # ------------------------------------------------------------------

    @property
    def modules(self) -> ModulesAPI:
        if self._modules is None:
            self._modules = ModulesAPI(self)
        return self._modules

    @property
    def records(self) -> RecordsAPI:
        if self._records is None:
            self._records = RecordsAPI(self)
        return self._records

    @property
    def metadata(self) -> MetadataAPI:
        if self._metadata is None:
            self._metadata = MetadataAPI(self)
        return self._metadata

    @property
    def query(self) -> QueryAPI:
        if self._query is None:
            self._query = QueryAPI(self)
        return self._query

    @property
    def bulk(self) -> BulkAPI:
        if self._bulk is None:
            self._bulk = BulkAPI(self)
        return self._bulk

    @property
    def notifications(self) -> NotificationsAPI:
        if self._notifications is None:
            self._notifications = NotificationsAPI(self)
        return self._notifications

    # ------------------------------------------------------------------
    # URL helper
    # ------------------------------------------------------------------

    def build_url(self, path: str) -> str:
        """Construct full URL from a relative path."""
        base = f"{self.api_domain}/people/api/"
        # Strip leading slash to avoid double-slash
        return urljoin(base, path.lstrip("/"))

    # ------------------------------------------------------------------
    # HTTP verbs
    # ------------------------------------------------------------------

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        return self._request("POST", path, json=json, params=params)

    def put(self, path: str, json: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        return self._request("PUT", path, json=json, params=params)

    def patch(self, path: str, json: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        return self._request("PATCH", path, json=json, params=params)

    def delete(self, path: str, params: Optional[Dict] = None) -> Any:
        return self._request("DELETE", path, params=params)

    # ------------------------------------------------------------------
    # Core request logic
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Any:
        url = self.build_url(path)
        headers = self.auth.auth_header()

        attempts = 0
        last_error: Optional[Exception] = None

        while attempts <= self.max_retries:
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )
                return self._handle_response(response)
            except ZohoRateLimitError as exc:
                last_error = exc
                if attempts < self.max_retries:
                    wait = self.retry_backoff * (2 ** attempts)
                    time.sleep(wait)
                    attempts += 1
                    # Refresh auth header in case token expired mid-flight
                    headers = self.auth.auth_header()
                    continue
                raise
            except ZohoServerError as exc:
                last_error = exc
                if attempts < self.max_retries:
                    wait = self.retry_backoff * (2 ** attempts)
                    time.sleep(wait)
                    attempts += 1
                    continue
                raise
            except ZohoAPIError:
                raise
            except Exception as exc:  # network errors etc.
                last_error = exc
                if attempts < self.max_retries:
                    time.sleep(self.retry_backoff)
                    attempts += 1
                    continue
                raise ZohoAPIError(f"Request failed: {exc}") from exc

        raise ZohoAPIError(f"All retries exhausted") from last_error

    # ------------------------------------------------------------------
    # Response handler
    # ------------------------------------------------------------------

    @staticmethod
    def _handle_response(response: Response) -> Any:
        status = response.status_code

        # 204 No Content
        if status == 204:
            return {}

        # Try to parse JSON
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if status == 200 or status == 201:
            return data

        # Extract Zoho-level error details
        error_code = None
        message = response.reason or "Unknown error"

        if isinstance(data, dict):
            # Zoho error response shape: {"code":"...", "message":"...", "details":{}}
            # or {"data":[{"code":"...", "message":"...", "details":{}}]}
            if "code" in data:
                error_code = data.get("code")
                message = data.get("message", message)
            elif "data" in data and isinstance(data["data"], list) and data["data"]:
                first = data["data"][0]
                error_code = first.get("code")
                message = first.get("message", message)

        kwargs = dict(
            status_code=status,
            error_code=error_code,
            details=data if isinstance(data, dict) else {},
        )

        if status == 401 or status == 403:
            raise ZohoAuthError(message, **kwargs)
        if status == 404:
            raise ZohoNotFoundError(message, **kwargs)
        if status == 429:
            raise ZohoRateLimitError(message, **kwargs)
        if status == 400 or status == 422:
            raise ZohoValidationError(message, **kwargs)
        if status >= 500:
            raise ZohoServerError(message, **kwargs)

        raise ZohoAPIError(message, **kwargs)

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "ZohoVerticalClient":
        return self

    def __exit__(self, *_) -> None:
        self._session.close()

    def close(self) -> None:
        self._session.close()
