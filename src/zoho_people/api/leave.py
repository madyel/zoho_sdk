"""
Leave API – time-off requests and leave balance in Zoho People.

Endpoints covered
-----------------
- ``GET  forms/leave/getRecords``                           – list leave requests (v1)
- ``GET  forms/leave/getDataByID``                          – single leave request
- ``POST forms/leave/addLeave``                             – submit a leave request
- ``POST forms/leave/updateLeave``                          – update a leave request
- ``POST forms/leave/approveLeave``                         – approve / reject
- ``POST forms/leave/cancelLeave``                          – cancel a request
- ``GET  v2/leavetracker/reports/bookedAndBalance``         – leave balance report
- ``GET  v2/leavetracker/leaves/records``                   – filtered records (v2)

Scope required: ``ZOHOPEOPLE.leave.ALL``
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..client import ZohoPeopleClient

#: ApprovalStatus values that represent an active (non-cancelled) leave.
ACTIVE_STATUSES: frozenset[str] = frozenset({
    "pending", "approved", "in sospeso", "waiting", "submitted",
})


class LeaveAPI:
    """
    Manage leave and time-off requests in Zoho People.

    Obtain an instance via :attr:`ZohoPeopleClient.leave`.

    Examples
    --------
    List approved leaves for April::

        leaves = client.leave.list(
            from_date="01-Apr-2026",
            to_date="30-Apr-2026",
            approval_status="Approved",
        )

    Submit a leave request::

        client.leave.apply(
            leave_type_id="413124000000645719",
            from_date="04-May-2026",
            to_date="05-May-2026",
            reason="Vacation",
        )
    """

    def __init__(self, client: "ZohoPeopleClient") -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        approval_status: Optional[str] = None,
        emp_id: Optional[str] = None,
        leave_type: Optional[str] = None,
        s_index: int = 1,
        rec_limit: int = 200,
    ) -> dict[str, Any]:
        """
        Retrieve leave requests from the v1 endpoint.

        Parameters
        ----------
        from_date:
            Period start in the organisation's date format.
        to_date:
            Period end.
        approval_status:
            ``"Approved"`` | ``"Pending"`` | ``"Rejected"`` | ``"Cancelled"``
        emp_id:
            Filter by employee ID or e-mail.
        leave_type:
            Filter by leave type name or ID.
        s_index:
            Pagination start index (default 1).
        rec_limit:
            Records per page, max 200.

        Returns
        -------
        dict
            ``{"records": {record_id: {...}}}``
        """
        params: dict[str, Any] = {
            "sIndex":    s_index,
            "rec_limit": min(rec_limit, 200),
        }
        if from_date:       params["from"]           = from_date
        if to_date:         params["to"]             = to_date
        if approval_status: params["approvalStatus"] = approval_status
        if emp_id:          params["empId"]          = emp_id
        if leave_type:      params["leaveType"]      = leave_type

        result = self._client.get("forms/leave/getRecords", params=params)
        return result if isinstance(result, dict) else {}

    def get(self, record_id: str) -> dict[str, Any]:
        """
        Retrieve details for a single leave request.

        Parameters
        ----------
        record_id:
            Leave request record ID.
        """
        result = self._client.get(
            "forms/leave/getDataByID",
            params={"recordId": record_id},
        )
        return result if isinstance(result, dict) else {}

    def get_balance(
        self,
        emp_ids: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retrieve leave balance and booked days per leave type (up to 30 employees).

        Parameters
        ----------
        emp_ids:
            Employee IDs or e-mails.  Defaults to the authenticated user.
        from_date:
            Period start date.
        to_date:
            Period end date.
        """
        params: dict[str, Any] = {}
        if emp_ids:   params["empId"]    = ",".join(emp_ids)
        if from_date: params["fromDate"] = from_date
        if to_date:   params["toDate"]   = to_date

        result = self._client.get(
            "v2/leavetracker/reports/bookedAndBalance", params=params
        )
        return result if isinstance(result, dict) else {}

    def get_pending(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        data_select: str = "MINE",
    ) -> dict[str, Any]:
        """
        Retrieve leave requests pending approval (v2 endpoint).

        Parameters
        ----------
        from_date:
            Period start (``"dd-MMM-yyyy"``).  **Required by the API.**
        to_date:
            Period end.
        data_select:
            ``"MINE"`` (default) | ``"SUB"`` | ``"ALL"``

        Returns
        -------
        dict
            ``{"records": {record_id: {...}}}``
        """
        return self._get_v2_records(["PENDING"], from_date, to_date, data_select)

    def get_approved_and_pending(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        data_select: str = "MINE",
    ) -> dict[str, Any]:
        """
        Retrieve both approved and pending leave records.

        Useful for excluding active leave days from attendance / timesheet
        calculations.

        Returns
        -------
        dict
            ``{"records": {record_id: {...}}}``
        """
        return self._get_v2_records(
            ["APPROVED", "PENDING"], from_date, to_date, data_select
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def apply(
        self,
        leave_type_id: str,
        from_date: str,
        to_date: str,
        reason: Optional[str] = None,
        emp_id: Optional[str] = None,
        from_session: Optional[int] = None,
        to_session: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Submit a leave request.

        Parameters
        ----------
        leave_type_id:
            Leave type ID — retrieve available types via :meth:`get_balance`.
        from_date:
            Start date in the organisation's date format.
        to_date:
            End date.
        reason:
            Optional reason text.
        emp_id:
            Employee ID when applying on behalf of someone else.
        from_session:
            Session start (1 = morning, 2 = afternoon, …).
        to_session:
            Session end.

        Returns
        -------
        dict
            Zoho API response with the new record ID.
        """
        payload: dict[str, Any] = {
            "leaveTypeId": leave_type_id,
            "from":        from_date,
            "to":          to_date,
        }
        if reason:                   payload["reason"]      = reason
        if emp_id:                   payload["empId"]       = emp_id
        if from_session is not None: payload["fromSession"] = from_session
        if to_session   is not None: payload["toSession"]   = to_session

        result = self._client.post(
            "forms/leave/addLeave",
            data={"inputData": json.dumps(payload)},
        )
        return result if isinstance(result, dict) else {}

    def update(self, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing leave request."""
        result = self._client.post(
            "forms/leave/updateLeave",
            data={"inputData": json.dumps(data), "recordId": record_id},
        )
        return result if isinstance(result, dict) else {}

    def approve(
        self,
        record_id: str,
        status: str = "Approved",
        comments: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Approve or reject a leave request.

        Parameters
        ----------
        record_id:
            Leave request record ID.
        status:
            ``"Approved"`` | ``"Rejected"``
        comments:
            Optional approval / rejection comment.
        """
        data: dict[str, Any] = {"recordId": record_id, "status": status}
        if comments: data["comments"] = comments
        result = self._client.post("forms/leave/approveLeave", data=data)
        return result if isinstance(result, dict) else {}

    def cancel(self, record_id: str, reason: Optional[str] = None) -> dict[str, Any]:
        """Cancel a leave request."""
        data: dict[str, Any] = {"recordId": record_id}
        if reason: data["reason"] = reason
        result = self._client.post("forms/leave/cancelLeave", data=data)
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_v2_records(
        self,
        statuses: list[str],
        from_date: Optional[str],
        to_date: Optional[str],
        data_select: str,
    ) -> dict[str, Any]:
        """Fetch leave records from the v2 endpoint with a status filter."""
        params: dict[str, Any] = {
            "approvalStatus": json.dumps(statuses),
            "dataSelect":     data_select,
            "limit":          200,
        }
        if from_date: params["from"] = from_date
        if to_date:   params["to"]   = to_date

        try:
            result = self._client.get("v2/leavetracker/leaves/records", params=params)
        except Exception:
            return {"records": {}}
        return result if isinstance(result, dict) else {"records": {}}
