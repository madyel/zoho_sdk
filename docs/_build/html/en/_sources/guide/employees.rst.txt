Employees
=========

Listing employees
-----------------

.. code-block:: python

   employees = client.employee.list()
   for emp in employees:
       print(emp.get("First Name"), emp.get("Last Name"), emp.get("Email address"))

   # Paginate
   batch = client.employee.list(s_index=201, rec_limit=200)

Searching
---------

.. code-block:: python

   # By email (direct API call)
   emp = client.employee.get_by_email("mario.rossi@company.com")

   # By Employee ID
   emp = client.employee.get_by_id("IMP085")

   # Full-text search (downloads list, filters client-side)
   results = client.employee.search("Rossi")
   for emp in results:
       print(emp.get("First Name"), emp.get("Last Name"))
