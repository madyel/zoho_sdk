"""
Core HTTP client for Zoho People SDK.

Response format
---------------
Zoho People wraps most responses as::

    {"response": {"status": 0, "result": [...]}}

where ``status=0`` means success and ``status=1`` means an application-level
error.  Some older endpoints return a plain JSON list or dict.

URL routing
-----------
- ``v2/...`` paths  →  ``{base}/api/v2/...``         (no ``/people/`` prefix)
- All other paths   →  ``{base}/people/api/{path}``
"""
from __future__ import annotations

import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests import Response, Session

from .auth import ZohoPeopleAuth
from .exceptions import (
    ZohoPeopleAuthError,
    ZohoPeopleError,
    ZohoPeopleNotFoundError,
    ZohoPeoplePermissionError,
    ZohoPeopleRateLimitError,
    ZohoPeopleValidationError,
)
from .api.employee   import EmployeeAPI
from .api.attendance import AttendanceAPI
from .api.timesheet  import TimesheetAPI
from .api.leave      import LeaveAPI

# Zoho status=1 messages that mean "no data" rather than a real error
_NO_DATA_PHRASES: tuple[str, ...] = (
    "no data", "no record", "data not found",
    "no timesheet", "no leave", "record not found",
)


class ZohoPeopleClient:
    """
    Entry point for the Zoho People SDK.

    Parameters
    ----------
    auth : ZohoPeopleAuth
        Authentication object.
    timeout : int
        HTTP request timeout in seconds (default 30).
    max_retries : int
        Number of retries on rate-limit or transient errors (default 3).
    retry_backoff : float
        Base wait time (seconds) between retries, doubled on each attempt.

    Example
    -------
    >>> from zoho_people import ZohoPeopleClient, ZohoPeopleAuth
    >>> auth   = ZohoPeopleAuth.from_env()
    >>> client = ZohoPeopleClient(auth=auth)
    >>> emp    = client.employee.get_by_email("mario.rossi@company.com")
    """

    def __init__(
        self,
        auth: ZohoPeopleAuth,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> None:
        self.auth          = auth
        self.timeout       = timeout
        self.max_retries   = max_retries
        self.retry_backoff = retry_backoff

        self._session: Session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

        # Sub-APIs are instantiated lazily on first access
        self._employee:   Optional[EmployeeAPI]   = None
        self._attendance: Optional[AttendanceAPI] = None
        self._timesheet:  Optional[TimesheetAPI]  = None
        self._leave:      Optional[LeaveAPI]      = None

    # ------------------------------------------------------------------
    # Sub-API accessors
    # ------------------------------------------------------------------

    @property
    def employee(self) -> EmployeeAPI:
        if self._employee is None:
            self._employee = EmployeeAPI(self)
        return self._employee

    @property
    def attendance(self) -> AttendanceAPI:
        if self._attendance is None:
            self._attendance = AttendanceAPI(self)
        return self._attendance

    @property
    def timesheet(self) -> TimesheetAPI:
        if self._timesheet is None:
            self._timesheet = TimesheetAPI(self)
        return self._timesheet

    @property
    def leave(self) -> LeaveAPI:
        if self._leave is None:
            self._leave = LeaveAPI(self)
        return self._leave

    # ------------------------------------------------------------------
    # URL builder
    # ------------------------------------------------------------------

    def build_url(self, path: str) -> str:
        """
        Build the full request URL from a relative path.

        Paths starting with ``v2/`` use ``{base}/api/v2/...``.
        All other paths use ``{base}/people/api/...``.
        """
        p    = path.lstrip("/")
        base = (
            self.auth.base_url.rstrip("/") + "/api/"
            if p.startswith("v2/")
            else self.auth.base_url.rstrip("/") + "/people/api/"
        )
        return urljoin(base, p)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        """HTTP GET with automatic auth and retry."""
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> Any:
        """HTTP POST with automatic auth and retry."""
        return self._request("POST", path, params=params, data=data)

    # ------------------------------------------------------------------
    # Core request loop
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> Any:
        url      = self.build_url(path)
        attempts = 0

        while True:
            headers = self.auth.auth_header()
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    timeout=self.timeout,
                )
                return self._parse(response)

            except ZohoPeopleRateLimitError:
                if attempts >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff * (2 ** attempts))
                attempts += 1

            except ZohoPeopleError:
                raise

            except Exception as exc:
                if attempts >= self.max_retries:
                    raise ZohoPeopleError(f"Request failed: {exc}") from exc
                time.sleep(self.retry_backoff)
                attempts += 1

    # ------------------------------------------------------------------
    # Response parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse(response: Response) -> Any:  # noqa: C901
        if response.status_code == 204:
            return {}

        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        http = response.status_code

        if http in (200, 201):
            # Plain list (some endpoints return this directly)
            if isinstance(data, list):
                return data

            # Standard envelope: {"response": {"status": 0/1, ...}}
            if isinstance(data, dict) and "response" in data:
                inner   = data["response"]
                status  = inner.get("status")

                if status == 1:
                    errors  = inner.get("errors", [{}])
                    code    = errors[0].get("code") if isinstance(errors, list) and errors else None
                    message = inner.get("message", "Unknown error")

                    # "No data" responses are not real errors
                    if any(p in message.lower() for p in _NO_DATA_PHRASES):
                        return {"result": [], "records": {}, "message": message}

                    if code == 9000 or "permission" in message.lower():
                        raise ZohoPeoplePermissionError(
                            message, status_code=http, error_code=code
                        )
                    if "auth" in message.lower():
                        raise ZohoPeopleAuthError(
                            message, status_code=http, error_code=code
                        )
                    # Return empty envelope for other status=1 cases
                    return {"result": [], "records": {}, "message": message, "error_code": code}

                return inner  # status=0 → success

            return data  # non-standard format (attendance v1, leave v1, …)

        # HTTP error responses
        message = response.reason or "Unknown error"
        if isinstance(data, dict):
            message = (
                data.get("message")
                or data.get("error", {}).get("message", message)
                or message
            )

        if http in (401, 403):
            raise ZohoPeopleAuthError(message, status_code=http)
        if http == 404:
            raise ZohoPeopleNotFoundError(message, status_code=http)
        if http == 429:
            raise ZohoPeopleRateLimitError(status_code=http)
        if http in (400, 422):
            raise ZohoPeopleValidationError(message, status_code=http)
        raise ZohoPeopleError(message, status_code=http)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "ZohoPeopleClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
