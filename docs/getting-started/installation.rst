Installation
============

Requirements
------------

- Python 3.10 or newer
- A Zoho People account with API access

From PyPI
---------

.. code-block:: bash

   pip install zoho-people-sdk

With browser fallback (Playwright, for attendance without admin permissions):

.. code-block:: bash

   pip install "zoho-people-sdk[browser]"
   playwright install chromium

Development install
-------------------

.. code-block:: bash

   git clone https://github.com/giuseppeg92/zoho-people-sdk.git
   cd zoho-people-sdk
   pip install -e ".[dev]"
