Error Handling
==============

All SDK errors inherit from :class:`~zoho_people.exceptions.ZohoPeopleError`.

Exception hierarchy
-------------------

.. code-block:: text

   ZohoPeopleError
   ├── ZohoPeopleAuthError          # 401 / 403 / invalid token
   ├── ZohoPeoplePermissionError    # role missing required permission
   ├── ZohoPeopleRateLimitError     # HTTP 429 (auto-retried by the client)
   ├── ZohoPeopleNotFoundError      # HTTP 404
   └── ZohoPeopleValidationError    # HTTP 400 / 422 / invalid params

Catching exceptions
-------------------

.. code-block:: python

   from zoho_people.exceptions import (
       ZohoPeopleAuthError,
       ZohoPeoplePermissionError,
       ZohoPeopleRateLimitError,
       ZohoPeopleNotFoundError,
       ZohoPeopleValidationError,
       ZohoPeopleError,
   )

   try:
       client.timesheet.add_timelog(...)

   except ZohoPeoplePermissionError:
       # Role missing permission in Zoho People settings
       print("Contact your Zoho People admin to enable the required permission.")

   except ZohoPeopleAuthError:
       # Token expired or revoked
       print("Re-authenticate: python main.py 1")

   except ZohoPeopleRateLimitError:
       # The SDK already retried max_retries times
       print("Too many requests — wait a moment and try again.")

   except ZohoPeopleValidationError as e:
       print(f"Invalid parameters: {e.message}")

   except ZohoPeopleError as e:
       print(f"API error {e.status_code}: {e.message}")

Exception attributes
--------------------

Every exception exposes:

- ``message`` — human-readable description
- ``status_code`` — HTTP status code (may be ``None``)
- ``error_code`` — Zoho internal error code (may be ``None``)
- ``details`` — additional context dict

Retry behaviour
---------------

:class:`~zoho_people.client.ZohoPeopleClient` automatically retries on
:class:`~zoho_people.exceptions.ZohoPeopleRateLimitError` up to ``max_retries``
times (default 3) with exponential back-off starting at ``retry_backoff`` seconds:

.. code-block:: python

   client = ZohoPeopleClient(
       auth=auth,
       max_retries=5,
       retry_backoff=2.0,   # 2s, 4s, 8s, 16s, 32s
   )
