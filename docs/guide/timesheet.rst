Timesheet
=========

The recommended workflow is:

1. Add individual time logs with :meth:`~zoho_people.api.timesheet.TimesheetAPI.add_timelog`
2. Group them into a timesheet with :meth:`~zoho_people.api.timesheet.TimesheetAPI.create`
3. Submit for approval with :meth:`~zoho_people.api.timesheet.TimesheetAPI.modify`

.. code-block:: python

   import time

   user = "mario.rossi@company.com"
   work_days = ["2026-04-01", "2026-04-02", "2026-04-03"]

   # Step 1 — add time logs
   for day in work_days:
       client.timesheet.add_timelog(
           user=user,
           work_date=day,
           hours="08:00",
           job_name="My Project",
           billing_status="Billable",
       )
       time.sleep(0.6)   # respect rate limit (20 req/min)

   # Step 2 — create timesheet
   result = client.timesheet.create(
       user=user,
       name="Timesheet April 2026",
       from_date="01-04-2026",
       to_date="30-04-2026",
       date_format="dd-MM-yyyy",
       send_for_approval=False,
   )
   ts_id = result.get("timesheetId")

   # Step 3 — submit for approval
   client.timesheet.modify(ts_id, send_for_approval=True)

Listing timesheets
------------------

.. code-block:: python

   sheets = client.timesheet.list(
       user="mario.rossi@company.com",
       from_date="01-Apr-2026",
       to_date="30-Apr-2026",
       approval_status="all",
   )

Timesheet settings
------------------

.. code-block:: python

   settings = client.timesheet.get_settings()
   jobs = settings.get("jobs", [])
   for job in jobs:
       print(job.get("jobId"), job.get("jobName"))
