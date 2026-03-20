# Zoho Vertical Studio SDK – Python

Python SDK for the **Zoho Vertical Studio REST APIs v6**.

Covers: Records CRUD, Metadata, Modules, COQL Query, Bulk Read/Write, Notifications.

---

## Installation

```bash
pip install requests          # only runtime dependency
# or, once published:
pip install zoho-vertical-sdk
```

---

## Quick Start

```python
from zoho_vertical_sdk import ZohoVerticalClient, ZohoOAuthToken

# Static access token
auth = ZohoOAuthToken(access_token="100xx.your_access_token_here")

# Auto-refresh via refresh token
auth = ZohoOAuthToken(
    client_id="1000.XXXXX",
    client_secret="yyyyyyy",
    refresh_token="1000.xxxxxxxx",
    accounts_url="https://accounts.zoho.eu",   # EU data centre
)

# Load from environment variables
# ZOHO_ACCESS_TOKEN, ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN
auth = ZohoOAuthToken.from_env()

client = ZohoVerticalClient(
    auth=auth,
    api_domain="https://zohoverticalapis.com",  # adjust for your DC
)
```

---

## Data Centre URLs

| Region  | API Domain                         | Accounts URL                    |
|---------|------------------------------------|---------------------------------|
| US      | `https://zohoverticalapis.com`     | `https://accounts.zoho.com`     |
| EU      | `https://zohoverticalapis.eu`      | `https://accounts.zoho.eu`      |
| IN      | `https://zohoverticalapis.in`      | `https://accounts.zoho.in`      |
| AU      | `https://zohoverticalapis.com.au`  | `https://accounts.zoho.com.au`  |
| JP      | `https://zohoverticalapis.jp`      | `https://accounts.zoho.jp`      |

---

## Modules API

```python
# List all modules
modules = client.modules.list_modules()
for m in modules:
    print(m["api_name"], "–", m["plural_label"])

# Filter by status
hidden = client.modules.list_modules(status="user_hidden")

# Get single module
lead_module = client.modules.get_module("Leads")
```

---

## Records API

### List Records

```python
resp = client.records.list(
    "Leads",
    fields=["Last_Name", "Email", "Phone"],
    page=1,
    per_page=50,
    sort_by="Created_Time",
    sort_order="desc",
)
for record in resp["data"]:
    print(record["Last_Name"], record.get("Email"))
```

### Auto-paginate (all records)

```python
all_leads = client.records.get_all("Leads", fields=["Last_Name", "Email"])
print(f"Total: {len(all_leads)} leads")
```

### Get by ID

```python
lead = client.records.get("Leads", "4876876000000123456")
print(lead["Last_Name"])
```

### Create

```python
results = client.records.create("Leads", [
    {"Last_Name": "Rossi", "Email": "m.rossi@example.com", "Phone": "+39 02 1234567"},
    {"Last_Name": "Bianchi", "Email": "l.bianchi@example.com"},
])
for r in results:
    if r["code"] == "SUCCESS":
        print("Created ID:", r["details"]["id"])
```

### Update

```python
results = client.records.update("Leads", [
    {"id": "4876876000000123456", "Email": "new.email@example.com"},
])
```

### Upsert

```python
results = client.records.upsert(
    "Leads",
    records=[{"Last_Name": "Verdi", "Email": "g.verdi@example.com"}],
    duplicate_check_fields=["Email"],
)
```

### Delete

```python
results = client.records.delete("Leads", ids=["4876876000000123456"])
```

### Search

```python
# By criteria
resp = client.records.search(
    "Leads",
    criteria="(Last_Name:equals:Rossi)",
    fields=["Last_Name", "Email"],
)

# By email
resp = client.records.search("Contacts", email="m.rossi@example.com")

# Full-text keyword
resp = client.records.search("Accounts", word="Acme")
```

### Related Records & Notes

```python
# Related Contacts of an Account
related = client.records.get_related("Accounts", "9876000001", "Contacts")

# Notes on a Lead
notes = client.records.get_notes("Leads", "4876876000000123456")

# Create a note
client.records.create_note(
    "Leads", "4876876000000123456",
    note_title="Follow-up",
    note_content="Called and left voicemail.",
)

# Attachments
attachments = client.records.get_attachments("Leads", "4876876000000123456")
```

---

## Metadata API

```python
# Fields
fields = client.metadata.get_fields("Leads")
for f in fields:
    print(f["api_name"], f["data_type"])

# Filter by type
lookups = client.metadata.get_fields("Contacts", field_type="lookup")

# Single field
field = client.metadata.get_field("Leads", "4876876000000014001")

# Layouts
layouts = client.metadata.get_layouts("Leads")

# Custom views
views = client.metadata.get_custom_views("Leads")

# Related lists
related_lists = client.metadata.get_related_lists("Accounts")
```

---

## Query API (COQL)

### Raw query

```python
result = client.query.execute(
    "SELECT Last_Name, Email, Created_Time "
    "FROM Leads "
    "WHERE (Last_Name is not null) "
    "ORDER BY Created_Time DESC "
    "LIMIT 0, 10"
)
for row in result["data"]:
    print(row)
```

### Fluent builder

```python
result = (
    client.query
    .select("Last_Name", "Email", "Account_Name.Account_Name")
    .from_module("Contacts")
    .where("(Email like '%example.com')")
    .order_by("Last_Name", "ASC")
    .limit(offset=0, count=50)
    .run()
)

# Auto-paginate all results
all_rows = (
    client.query
    .select("Last_Name", "Email")
    .from_module("Leads")
    .where("Last_Name is not null")
    .run_all()
)
```

### Aggregate / GROUP BY

```python
result = client.query.execute(
    "SELECT Lead_Status, COUNT(id) AS total "
    "FROM Leads "
    "GROUP BY Lead_Status "
    "LIMIT 0, 200"
)
```

### Cross-module JOIN via lookup dot-notation

```python
result = client.query.execute(
    "SELECT Last_Name, 'Account_Name.Account_Name', 'Account_Name.Phone' "
    "FROM Contacts "
    "WHERE (Account_Name.Industry = 'Technology') "
    "LIMIT 0, 100"
)
```

---

## Bulk API

### Bulk Read

```python
# 1. Create job
job = client.bulk.create_read_job(
    module="Leads",
    fields=["Last_Name", "Email", "Phone", "Created_Time"],
    criteria="(Created_Time >= '2025-01-01T00:00:00+00:00')",
)
job_id = job["data"][0]["details"]["id"]

# 2. Wait for completion
status = client.bulk.wait_for_read_job(job_id, poll_interval=5, timeout=300)

# 3. Download CSV
csv_bytes = client.bulk.download_read_result(job_id)
with open("leads_export.csv", "wb") as f:
    f.write(csv_bytes)

# 4. Cleanup
client.bulk.delete_read_job(job_id)
```

---

## Notifications API

```python
# Subscribe
channel = client.notifications.enable(
    channel_id="100000006800211",
    events=["Leads.create", "Leads.edit", "Leads.delete"],
    channel_expiry="2026-12-31T23:59:59+05:30",
    notify_url="https://myapp.example.com/webhooks/zoho",
    token="my_secret_token",
)

# List channels
channels = client.notifications.list_channels()

# Renew expiry
client.notifications.update(
    channel_id="100000006800211",
    channel_expiry="2027-06-30T23:59:59+05:30",
)

# Disable
client.notifications.disable_raw(["100000006800211"])
```

---

## Error Handling

```python
from zoho_vertical_sdk.exceptions import (
    ZohoAuthError,
    ZohoNotFoundError,
    ZohoRateLimitError,
    ZohoValidationError,
    ZohoAPIError,
)

try:
    lead = client.records.get("Leads", "nonexistent_id")
except ZohoNotFoundError:
    print("Record not found")
except ZohoAuthError:
    print("Check your OAuth token / scopes")
except ZohoRateLimitError:
    print("Rate limit hit – the SDK will auto-retry up to max_retries times")
except ZohoValidationError as e:
    print("Bad request:", e.message, e.details)
except ZohoAPIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

---

## Configuration

```python
client = ZohoVerticalClient(
    auth=auth,
    api_domain="https://zohoverticalapis.eu",   # EU data centre
    version="v6",
    timeout=60,           # HTTP timeout in seconds
    max_retries=3,        # Retry on rate-limit / 5xx
    retry_backoff=1.0,    # Base back-off (doubles each retry)
)
```

---

## Context Manager

```python
with ZohoVerticalClient(auth=auth, api_domain="https://zohoverticalapis.com") as client:
    leads = client.records.list("Leads")
# HTTP session is closed automatically
```

---

## OAuth Scopes Reference

| Capability        | Scope                                   |
|-------------------|-----------------------------------------|
| Read modules      | `ZohoVertical.settings.modules.READ`    |
| Read fields       | `ZohoVertical.settings.fields.READ`     |
| Read records      | `ZohoVertical.modules.ALL`              |
| Create/Update     | `ZohoVertical.modules.ALL`              |
| Bulk Read         | `ZohoVertical.bulk.READ`                |
| Bulk Write        | `ZohoVertical.bulk.CREATE`              |
| Notifications     | `ZohoVertical.modules.ALL`              |

---

## License

MIT
