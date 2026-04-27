"""
zoho-people-sdk
===============
Python SDK for the Zoho People REST API.

Quick start::

    from zoho_people import ZohoPeopleClient, ZohoPeopleAuth

    auth   = ZohoPeopleAuth.from_env()
    client = ZohoPeopleClient(auth=auth)

    # List employees
    employees = client.employee.list()

    # Add a time log
    client.timesheet.add_timelog(
        user="mario.rossi@company.com",
        work_date="2026-04-25",
        hours="08:00",
        job_name="My Project",
    )

    # Get pending leaves
    leaves = client.leave.get_pending(
        from_date="01-Apr-2026",
        to_date="30-Apr-2026",
    )
"""
from ._version import __version__
from .auth       import ZohoPeopleAuth
from .client     import ZohoPeopleClient
from .exceptions import (
    ZohoPeopleError,
    ZohoPeopleAuthError,
    ZohoPeopleNotFoundError,
    ZohoPeoplePermissionError,
    ZohoPeopleRateLimitError,
    ZohoPeopleValidationError,
)

__all__ = [
    "__version__",
    "ZohoPeopleAuth",
    "ZohoPeopleClient",
    "ZohoPeopleError",
    "ZohoPeopleAuthError",
    "ZohoPeopleNotFoundError",
    "ZohoPeoplePermissionError",
    "ZohoPeopleRateLimitError",
    "ZohoPeopleValidationError",
]
