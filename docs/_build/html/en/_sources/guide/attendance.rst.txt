Attendance
==========

.. note::
   Write operations (check-in / check-out) require the *"Check-in/Check-out"*
   or *"Regularize Attendance"* permission enabled in
   **Zoho People → Settings → Attendance → Permissions** for the user's role.
   Read operations (``get_user_report``) work for all roles.

Check-in and check-out
----------------------

.. code-block:: python

   client.attendance.checkin(
       email_id="mario.rossi@company.com",
       checkin="25/04/2026 09:00:00",
       checkout="25/04/2026 18:00:00",
   )

   # Check-in only (check-out registered later)
   client.attendance.checkin(
       email_id="mario.rossi@company.com",
       checkin="25/04/2026 09:00:00",
   )

   # Check-out only
   client.attendance.checkout(
       email_id="mario.rossi@company.com",
       checkout="25/04/2026 18:00:00",
   )

Employee identifiers
~~~~~~~~~~~~~~~~~~~~

Exactly one of the following must be provided:

- ``emp_id`` — Employee ID (e.g. ``"IMP085"``)
- ``email_id`` — Employee e-mail
- ``map_id`` — Biometric device mapper ID

Bulk import
-----------

Pass check-in and check-out as **separate dicts** in the list:

.. code-block:: python

   records = [
       {"checkIn":  "2026-04-01 09:00:00"},
       {"checkOut": "2026-04-01 18:00:00"},
       {"checkIn":  "2026-04-02 09:00:00"},
       {"checkOut": "2026-04-02 17:00:00"},
   ]
   result = client.attendance.bulk_import(records)

   # Check for partial errors
   if "errorDates" in str(result):
       print("Some dates failed:", result)

.. warning::
   The internal ``ftime`` / ``ttime`` fields used by the Zoho People web UI
   are expressed in **milliseconds** from midnight (e.g. 09:00 → 32 400 000 ms).

Attendance report
-----------------

.. code-block:: python

   report = client.attendance.get_user_report(
       start_date="01/04/2026",
       end_date="30/04/2026",
       date_format="dd/MM/yyyy",
   )

   # report is a list of dicts with attendanceDetails per day
   for day, info in report[0].get("attendanceDetails", {}).items():
       print(day, info.get("Status"), info.get("TotalHours"))
