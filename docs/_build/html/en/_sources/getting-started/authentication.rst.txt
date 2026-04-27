Authentication
==============

zoho-people-sdk uses **OAuth 2.0** with automatic token refresh.

Obtaining credentials
---------------------

1. Go to `accounts.zoho.com/developerconsole <https://accounts.zoho.com/developerconsole>`_
2. Create a **Self Client**
3. Generate a code with the required scopes:

.. code-block:: text

   ZOHOPEOPLE.forms.ALL,ZOHOPEOPLE.attendance.ALL,
   ZOHOPEOPLE.timetracker.ALL,ZOHOPEOPLE.leave.ALL

4. Exchange the code for a **refresh token** using ``python main.py 1``

Environment variables
---------------------

Copy ``.env.example`` to ``.env`` and fill in your values:

.. code-block:: bash

   ZOHO_CLIENT_ID=1000.xxxxxxxxxx
   ZOHO_CLIENT_SECRET=xxxxxxxxxx
   ZOHO_REFRESH_TOKEN=1000.xxxxxxxxxx
   ZOHO_DATA_CENTRE=US          # US | EU | IN | AU | JP
   ZOHO_USER_EMAIL=you@company.com

Loading from environment
------------------------

.. code-block:: python

   from zoho_people import ZohoPeopleAuth, ZohoPeopleClient

   auth   = ZohoPeopleAuth.from_env()
   client = ZohoPeopleClient(auth=auth)

Explicit configuration
----------------------

.. code-block:: python

   auth = ZohoPeopleAuth(
       client_id="1000.xxx",
       client_secret="yyy",
       refresh_token="1000.zzz",
       data_centre="EU",
   )
   client = ZohoPeopleClient(auth=auth)

Data centres
------------

.. list-table::
   :header-rows: 1
   :widths: 10 15 30

   * - Region
     - Code
     - Accounts URL
   * - United States
     - ``US``
     - ``https://accounts.zoho.com``
   * - Europe
     - ``EU``
     - ``https://accounts.zoho.eu``
   * - India
     - ``IN``
     - ``https://accounts.zoho.in``
   * - Australia
     - ``AU``
     - ``https://accounts.zoho.com.au``
   * - Japan
     - ``JP``
     - ``https://accounts.zoho.jp``
