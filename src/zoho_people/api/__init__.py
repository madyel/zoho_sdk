"""Zoho People API sub-modules."""
from .attendance import AttendanceAPI
from .employee   import EmployeeAPI
from .leave      import LeaveAPI
from .timesheet  import TimesheetAPI

__all__ = ["AttendanceAPI", "EmployeeAPI", "LeaveAPI", "TimesheetAPI"]
