Leave
=====

Listing leave requests
----------------------

.. code-block:: python

   # All approved leaves for a period
   leaves = client.leave.list(
       from_date="01-Apr-2026",
       to_date="30-Apr-2026",
       approval_status="Approved",
   )

   # Pending requests only (v2 endpoint)
   pending = client.leave.get_pending(
       from_date="01-Apr-2026",
       to_date="30-Apr-2026",
   )

   # Both approved and pending (useful to exclude from attendance)
   active = client.leave.get_approved_and_pending(
       from_date="01-Apr-2026",
       to_date="30-Apr-2026",
   )

Leave balance
-------------

.. code-block:: python

   balance = client.leave.get_balance()
   for leave_type, info in balance.items():
       print(leave_type, "→ available:", info.get("balance"))

Applying for leave
------------------

.. code-block:: python

   client.leave.apply(
       leave_type_id="413124000000645719",
       from_date="04-May-2026",
       to_date="05-May-2026",
       reason="Annual leave",
   )

Approving / rejecting
---------------------

.. code-block:: python

   client.leave.approve(
       record_id="439215000012345678",
       status="Approved",
       comments="Approved. Enjoy!",
   )

   # Reject
   client.leave.approve(
       record_id="439215000012345679",
       status="Rejected",
       comments="Conflicting project deadline.",
   )

Cancelling
----------

.. code-block:: python

   client.leave.cancel(
       record_id="439215000012345678",
       reason="Plans changed",
   )
