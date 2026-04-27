"""
Attendance API – Zoho People check-in/out and attendance reports.

Endpoints covered
-----------------
- ``POST attendance``                        – single check-in / check-out
- ``POST attendance/bulkImport``             – bulk attendance import
- ``GET  attendance/getUserReport``          – attendance report for a period
- ``GET  attendance/getAttendanceEntries``   – daily clock entries
- ``GET  attendance/getShiftConfiguration``  – shift configuration

Scope required: ``ZOHOPEOPLE.attendance.ALL``

.. note::
   The check-in / check-out write endpoints require the authenticated user to
   have the *"Check-in/Check-out"* or *"Regularize Attendance"* permission
   enabled in Zoho People → Settings → Attendance → Permissions.
   Read endpoints (``getUserReport``) work for all roles.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..client import ZohoPeopleClient

#: Date-time format expected by the check-in / check-out API.
CHECKIN_DATE_FORMAT: str = "dd/MM/yyyy HH:mm:ss"


class AttendanceAPI:
    """
    Read and write attendance records in Zoho People.

    Obtain an instance via :attr:`ZohoPeopleClient.attendance`.

    Examples
    --------
    Record a single check-in and check-out::

        client.attendance.checkin(
            email_id="mario.rossi@company.com",
            checkin="25/04/2026 09:00:00",
            checkout="25/04/2026 18:00:00",
        )

    Fetch the monthly attendance report::

        report = client.attendance.get_user_report(
            start_date="01/04/2026",
            end_date="30/04/2026",
            date_format="dd/MM/yyyy",
        )
    """

    def __init__(self, client: "ZohoPeopleClient") -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Check-in / Check-out
    # ------------------------------------------------------------------

    def checkin(
        self,
        checkin: str,
        checkout: Optional[str] = None,
        *,
        emp_id: Optional[str] = None,
        email_id: Optional[str] = None,
        map_id: Optional[str] = None,
        date_format: str = CHECKIN_DATE_FORMAT,
    ) -> dict[str, Any]:
        """
        Record a check-in (and optionally a check-out) for an employee.

        Parameters
        ----------
        checkin:
            Check-in datetime string, e.g. ``"25/04/2026 09:00:00"``.
        checkout:
            Check-out datetime string.  Omit to record only the entry.
        emp_id:
            Employee ID (e.g. ``"EMP001"`` or ``"IMP085"``).
        email_id:
            Employee e-mail address.
        map_id:
            Biometric device mapper ID.
        date_format:
            Datetime format (default ``"dd/MM/yyyy HH:mm:ss"``).

        Returns
        -------
        dict
            Zoho API response.

        Raises
        ------
        ValueError
            If none of *emp_id*, *email_id*, *map_id* is provided.
        """
        if not any([emp_id, email_id, map_id]):
            raise ValueError("At least one of emp_id, email_id, or map_id is required.")
        data: dict[str, Any] = {"dateFormat": date_format, "checkIn": checkin}
        if checkout:  data["checkOut"] = checkout
        if emp_id:    data["empId"]    = emp_id
        if email_id:  data["emailId"]  = email_id
        if map_id:    data["mapId"]    = map_id
        return self._client.post("attendance", data=data)

    def checkout(
        self,
        checkout: str,
        *,
        emp_id: Optional[str] = None,
        email_id: Optional[str] = None,
        map_id: Optional[str] = None,
        date_format: str = CHECKIN_DATE_FORMAT,
    ) -> dict[str, Any]:
        """
        Record a standalone check-out (employee already checked in).

        Raises
        ------
        ValueError
            If none of *emp_id*, *email_id*, *map_id* is provided.
        """
        if not any([emp_id, email_id, map_id]):
            raise ValueError("At least one of emp_id, email_id, or map_id is required.")
        data: dict[str, Any] = {"dateFormat": date_format, "checkOut": checkout}
        if emp_id:    data["empId"]   = emp_id
        if email_id:  data["emailId"] = email_id
        if map_id:    data["mapId"]   = map_id
        return self._client.post("attendance", data=data)

    # ------------------------------------------------------------------
    # Bulk import
    # ------------------------------------------------------------------

    def bulk_import(
        self,
        records: list[dict[str, Any]],
        date_format: str = "yyyy-MM-dd HH:mm:ss",
    ) -> dict[str, Any]:
        """
        Import multiple attendance records in a single request.

        Zoho processes check-in and check-out as **separate entries**, so each
        record should contain either ``checkIn`` or ``checkOut`` (not both)::

            records = [
                {"checkIn":  "2026-04-01 09:00:00"},
                {"checkOut": "2026-04-01 18:00:00"},
            ]
            client.attendance.bulk_import(records)

        Parameters
        ----------
        records:
            List of check-in / check-out dicts.
        date_format:
            Datetime format for all records (default ``"yyyy-MM-dd HH:mm:ss"``).

        Returns
        -------
        dict
            Import result; may contain an ``errorDates`` key on partial failure.
        """
        data = {"data": json.dumps(records), "dateFormat": date_format}
        result = self._client.post("attendance/bulkImport", data=data)
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def get_user_report(
        self,
        start_date: str,
        end_date: str,
        *,
        emp_id: Optional[str] = None,
        email_id: Optional[str] = None,
        map_id: Optional[str] = None,
        date_format: Optional[str] = None,
        start_index: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the attendance report for a date range.

        Without an employee identifier the response covers the authenticated user.
        Paginate with *start_index* in steps of 100.

        Parameters
        ----------
        start_date:
            Period start (e.g. ``"01/04/2026"``).
        end_date:
            Period end.
        date_format:
            Date format if different from the organisation default.
        start_index:
            Pagination offset (0, 100, 200, …).

        Returns
        -------
        list[dict]
            Each item contains ``employeeDetails`` and ``attendanceDetails``.
        """
        params: dict[str, Any] = {
            "sdate":      start_date,
            "edate":      end_date,
            "startIndex": start_index,
        }
        if emp_id:      params["empId"]      = emp_id
        if email_id:    params["emailId"]    = email_id
        if map_id:      params["mapId"]      = map_id
        if date_format: params["dateFormat"] = date_format

        result = self._client.get("attendance/getUserReport", params=params)
        if isinstance(result, list):
            return result
        return result.get("result", []) if isinstance(result, dict) else []

    def get_entries(
        self,
        date: str,
        *,
        emp_id: Optional[str] = None,
        email_id: Optional[str] = None,
        erecno: Optional[str] = None,
        map_id: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve individual clock events (in/out timestamps) for a single day.

        Parameters
        ----------
        date:
            Day string in the organisation's format or *date_format*.

        Returns
        -------
        list[dict]
            Clock entries with timestamps and metadata.
        """
        params: dict[str, Any] = {"date": date}
        if emp_id:      params["empId"]      = emp_id
        if email_id:    params["emailId"]    = email_id
        if erecno:      params["erecno"]     = erecno
        if map_id:      params["mapId"]      = map_id
        if date_format: params["dateFormat"] = date_format

        result = self._client.get("attendance/getAttendanceEntries", params=params)
        if isinstance(result, list):
            return result
        return result.get("result", []) if isinstance(result, dict) else []

    # ------------------------------------------------------------------
    # Shifts
    # ------------------------------------------------------------------

    def get_shift_configuration(
        self,
        start_date: str,
        end_date: str,
        *,
        emp_id: Optional[str] = None,
        email_id: Optional[str] = None,
        map_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retrieve the shift configuration for an employee over a period.

        Parameters
        ----------
        start_date:
            Period start in ``yyyy-MM-dd`` format.
        end_date:
            Period end in ``yyyy-MM-dd`` format.

        Returns
        -------
        dict
            Shift details: name, start/end times, weekends, public holidays.
        """
        params: dict[str, Any] = {"sdate": start_date, "edate": end_date}
        if emp_id:    params["empId"]   = emp_id
        if email_id:  params["emailId"] = email_id
        if map_id:    params["mapId"]   = map_id

        result = self._client.get("attendance/getShiftConfiguration", params=params)
        return result if isinstance(result, dict) else {}
