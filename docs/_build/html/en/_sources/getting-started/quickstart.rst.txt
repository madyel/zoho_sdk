Quick Start
===========

.. code-block:: python

   from zoho_people import ZohoPeopleAuth, ZohoPeopleClient

   auth   = ZohoPeopleAuth.from_env()
   client = ZohoPeopleClient(auth=auth)

   # --- Employees ---
   employees = client.employee.list()
   for emp in employees:
       print(emp.get("First Name"), emp.get("Email address"))

   # --- Timesheet: add a time log ---
   client.timesheet.add_timelog(
       user="mario.rossi@company.com",
       work_date="2026-04-25",
       hours="08:00",
       job_name="My Project",
   )

   # --- Leave: list pending requests ---
   pending = client.leave.get_pending(
       from_date="01-Apr-2026",
       to_date="30-Apr-2026",
   )
   for rid, leave in pending.get("records", {}).items():
       print(leave.get("From"), "→", leave.get("ApprovalStatus"))

   # --- Attendance: monthly report ---
   report = client.attendance.get_user_report(
       start_date="01/04/2026",
       end_date="30/04/2026",
       date_format="dd/MM/yyyy",
   )

Context manager
---------------

The client implements the context manager protocol, which closes the
underlying HTTP session automatically:

.. code-block:: python

   with ZohoPeopleClient(auth=auth) as client:
       employees = client.employee.list()
