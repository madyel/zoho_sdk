"""
Zoho Vertical Studio SDK v6
Python SDK for Zoho Vertical Studio REST APIs v6
"""

from .client import ZohoVerticalClient
from .auth import ZohoOAuthToken
from .exceptions import (
    ZohoAPIError,
    ZohoAuthError,
    ZohoRateLimitError,
    ZohoNotFoundError,
    ZohoValidationError,
)
from .modules import ModulesAPI
from .records import RecordsAPI
from .metadata import MetadataAPI
from .query import QueryAPI
from .bulk import BulkAPI
from .notifications import NotificationsAPI
from .attendance import PeopleAttendanceAPI, time_to_seconds, seconds_to_time
from .timesheet import PeopleTimesheetAPI
from .employee import PeopleEmployeeAPI
from .leave import PeopleLeaveAPI

__version__ = "1.0.0"
__author__ = "Zoho Vertical SDK"

__all__ = [
    "ZohoVerticalClient",
    "ZohoOAuthToken",
    "ZohoAPIError",
    "ZohoAuthError",
    "ZohoRateLimitError",
    "ZohoNotFoundError",
    "ZohoValidationError",
    "ModulesAPI",
    "RecordsAPI",
    "MetadataAPI",
    "QueryAPI",
    "BulkAPI",
    "NotificationsAPI",
    "PeopleAttendanceAPI",
    "time_to_seconds",
    "seconds_to_time",
    "PeopleTimesheetAPI",
    "PeopleEmployeeAPI",
    "PeopleLeaveAPI",
]
