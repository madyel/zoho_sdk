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

Format: `ZohoVertical.<scope_name>.<operation>`
Operations: `ALL` · `READ` · `CREATE` · `UPDATE` · `DELETE`

### Modules (`ZohoVertical.modules.*`)

| Scope | Description |
|-------|-------------|
| `ZohoVertical.modules.ALL` | Full access (CRUD) to all modules |
| `ZohoVertical.modules.READ` | Read records from all modules |
| `ZohoVertical.modules.CREATE` | Create records in all modules |
| `ZohoVertical.modules.UPDATE` | Update records in all modules |
| `ZohoVertical.modules.DELETE` | Delete records from all modules |
| `ZohoVertical.modules.<ModuleName>.ALL` | Full access to a specific module (e.g. `modules.Leads.ALL`) |
| `ZohoVertical.modules.<ModuleName>.READ` | Read-only access to a specific module |
| `ZohoVertical.modules.<ModuleName>.CREATE` | Create records in a specific module |
| `ZohoVertical.modules.<ModuleName>.UPDATE` | Update records in a specific module |
| `ZohoVertical.modules.<ModuleName>.DELETE` | Delete records in a specific module |

### Settings (`ZohoVertical.settings.*`)

| Scope | Description |
|-------|-------------|
| `ZohoVertical.settings.ALL` | Full access to all settings |
| `ZohoVertical.settings.modules.READ` | Read module metadata (list, schema) |
| `ZohoVertical.settings.modules.CREATE` | Create custom modules |
| `ZohoVertical.settings.modules.UPDATE` | Update module configuration |
| `ZohoVertical.settings.modules.DELETE` | Delete custom modules |
| `ZohoVertical.settings.fields.READ` | Read field definitions |
| `ZohoVertical.settings.fields.CREATE` | Create custom fields |
| `ZohoVertical.settings.fields.UPDATE` | Update field configuration |
| `ZohoVertical.settings.fields.DELETE` | Delete custom fields |
| `ZohoVertical.settings.layouts.READ` | Read layout definitions |
| `ZohoVertical.settings.layouts.CREATE` | Create layouts |
| `ZohoVertical.settings.layouts.UPDATE` | Update layouts |
| `ZohoVertical.settings.layouts.DELETE` | Delete layouts |
| `ZohoVertical.settings.custom_views.READ` | Read custom views |
| `ZohoVertical.settings.custom_views.CREATE` | Create custom views |
| `ZohoVertical.settings.custom_views.UPDATE` | Update custom views |
| `ZohoVertical.settings.custom_views.DELETE` | Delete custom views |
| `ZohoVertical.settings.related_lists.READ` | Read related lists |
| `ZohoVertical.settings.related_lists.UPDATE` | Update related lists |
| `ZohoVertical.settings.roles.READ` | Read roles |
| `ZohoVertical.settings.roles.CREATE` | Create roles |
| `ZohoVertical.settings.roles.UPDATE` | Update roles |
| `ZohoVertical.settings.roles.DELETE` | Delete roles |
| `ZohoVertical.settings.profiles.READ` | Read profiles |
| `ZohoVertical.settings.profiles.CREATE` | Create profiles |
| `ZohoVertical.settings.profiles.UPDATE` | Update profiles |
| `ZohoVertical.settings.profiles.DELETE` | Delete profiles |
| `ZohoVertical.settings.territories.READ` | Read territories |
| `ZohoVertical.settings.territories.CREATE` | Create territories |
| `ZohoVertical.settings.territories.UPDATE` | Update territories |
| `ZohoVertical.settings.territories.DELETE` | Delete territories |
| `ZohoVertical.settings.variables.READ` | Read global variables |
| `ZohoVertical.settings.variables.CREATE` | Create global variables |
| `ZohoVertical.settings.variables.UPDATE` | Update global variables |
| `ZohoVertical.settings.variables.DELETE` | Delete global variables |
| `ZohoVertical.settings.tags.READ` | Read tags |
| `ZohoVertical.settings.tags.CREATE` | Create tags |
| `ZohoVertical.settings.tags.UPDATE` | Update tags |
| `ZohoVertical.settings.tags.DELETE` | Delete tags |
| `ZohoVertical.settings.tab_groups.READ` | Read tab groups |
| `ZohoVertical.settings.tab_groups.UPDATE` | Update tab groups |
| `ZohoVertical.settings.macros.READ` | Read macros |
| `ZohoVertical.settings.macros.CREATE` | Create macros |
| `ZohoVertical.settings.macros.UPDATE` | Update macros |
| `ZohoVertical.settings.macros.DELETE` | Delete macros |
| `ZohoVertical.settings.custom_links.READ` | Read custom links |
| `ZohoVertical.settings.custom_links.CREATE` | Create custom links |
| `ZohoVertical.settings.custom_links.UPDATE` | Update custom links |
| `ZohoVertical.settings.custom_links.DELETE` | Delete custom links |
| `ZohoVertical.settings.custom_buttons.READ` | Read custom buttons |
| `ZohoVertical.settings.custom_buttons.CREATE` | Create custom buttons |
| `ZohoVertical.settings.custom_buttons.UPDATE` | Update custom buttons |
| `ZohoVertical.settings.custom_buttons.DELETE` | Delete custom buttons |
| `ZohoVertical.settings.currencies.READ` | Read currencies |
| `ZohoVertical.settings.currencies.CREATE` | Create currencies |
| `ZohoVertical.settings.currencies.UPDATE` | Update currencies |

### Bulk (`ZohoVertical.bulk.*`)

| Scope | Description |
|-------|-------------|
| `ZohoVertical.bulk.ALL` | Full access to bulk read/write APIs |
| `ZohoVertical.bulk.READ` | Download bulk read job results |
| `ZohoVertical.bulk.CREATE` | Create bulk read/write jobs |
| `ZohoVertical.bulk.UPDATE` | Update bulk jobs |
| `ZohoVertical.bulk.DELETE` | Delete bulk jobs |

### Notifications (`ZohoVertical.notifications.*`)

| Scope | Description |
|-------|-------------|
| `ZohoVertical.notifications.ALL` | Full access to notifications |
| `ZohoVertical.notifications.READ` | List notification channels |
| `ZohoVertical.notifications.CREATE` | Enable/subscribe notifications |
| `ZohoVertical.notifications.UPDATE` | Update notification channels |
| `ZohoVertical.notifications.DELETE` | Disable/delete notifications |

### Recommended scope sets

```
# Minimum read-only
ZohoVertical.modules.READ,ZohoVertical.settings.modules.READ,ZohoVertical.settings.fields.READ

# Full access (default for this SDK)
ZohoVertical.modules.ALL,ZohoVertical.settings.ALL,ZohoVertical.bulk.ALL

# Full access including notifications
ZohoVertical.modules.ALL,ZohoVertical.settings.ALL,ZohoVertical.bulk.ALL,ZohoVertical.notifications.ALL
```

---

## License

MIT
