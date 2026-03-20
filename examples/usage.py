"""
examples/usage.py – Comprehensive example of the Zoho Vertical Studio SDK.

Run:
    ZOHO_ACCESS_TOKEN=100xx.xxx python examples/usage.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zoho_vertical_sdk import ZohoVerticalClient, ZohoOAuthToken
from zoho_vertical_sdk.exceptions import ZohoAPIError, ZohoNotFoundError


def main():
    # ------------------------------------------------------------------ #
    # 1. Authentication                                                    #
    # ------------------------------------------------------------------ #
    auth = ZohoOAuthToken.from_env()
    # or:
    # auth = ZohoOAuthToken(access_token=os.environ["ZOHO_ACCESS_TOKEN"])
    # auth = ZohoOAuthToken(
    #     client_id="1000.XXXXX",
    #     client_secret="yyyyyyy",
    #     refresh_token="1000.xxxxxxxx",
    # )

    client = ZohoVerticalClient(
        auth=auth,
        api_domain=os.getenv("ZOHO_API_DOMAIN", "https://zohoverticalapis.com"),
    )

    # ------------------------------------------------------------------ #
    # 2. Modules                                                           #
    # ------------------------------------------------------------------ #
    print("=== Modules ===")
    modules = client.modules.list_modules()
    api_modules = [m for m in modules if m.get("api_supported")]
    print(f"API-supported modules: {[m['api_name'] for m in api_modules[:8]]}")

    # ------------------------------------------------------------------ #
    # 3. Metadata                                                          #
    # ------------------------------------------------------------------ #
    print("\n=== Fields for Leads ===")
    fields = client.metadata.get_fields("Leads")
    print(f"Total fields: {len(fields)}")
    for f in fields[:5]:
        print(f"  {f['api_name']:30} {f['data_type']}")

    # ------------------------------------------------------------------ #
    # 4. Records – List                                                    #
    # ------------------------------------------------------------------ #
    print("\n=== Leads (first 5) ===")
    resp = client.records.list(
        "Leads",
        fields=["Last_Name", "Email", "Lead_Status"],
        per_page=5,
        sort_by="Created_Time",
        sort_order="desc",
    )
    for r in resp.get("data", []):
        print(f"  {r.get('Last_Name', '?'):20} {r.get('Email', '')}")

    # ------------------------------------------------------------------ #
    # 5. Records – Search                                                  #
    # ------------------------------------------------------------------ #
    print("\n=== Search Leads ===")
    try:
        search_resp = client.records.search(
            "Leads",
            criteria="(Lead_Status:equals:New)",
            fields=["Last_Name", "Email"],
            per_page=3,
        )
        print(f"  Found: {len(search_resp.get('data', []))} records")
    except ZohoAPIError as e:
        print(f"  Search error: {e.message}")

    # ------------------------------------------------------------------ #
    # 6. COQL Query                                                        #
    # ------------------------------------------------------------------ #
    print("\n=== COQL Query ===")
    try:
        result = (
            client.query
            .select("Last_Name", "Email", "Lead_Status")
            .from_module("Leads")
            .where("(Last_Name is not null)")
            .order_by("Last_Name", "ASC")
            .limit(offset=0, count=5)
            .run()
        )
        for row in result.get("data", []):
            print(f"  {row.get('Last_Name', '?'):20} {row.get('Lead_Status', '')}")
    except ZohoAPIError as e:
        print(f"  Query error: {e.message}")

    # ------------------------------------------------------------------ #
    # 7. Records – Create / Update / Delete (demo only – not executed)     #
    # ------------------------------------------------------------------ #
    print("\n=== CRUD Demo (skipped to avoid data changes) ===")
    print("  # Create:")
    print("  results = client.records.create('Leads', [{'Last_Name': 'Rossi', 'Email': 'rossi@ex.com'}])")
    print("  # Update:")
    print("  client.records.update('Leads', [{'id': '<id>', 'Email': 'new@ex.com'}])")
    print("  # Delete:")
    print("  client.records.delete('Leads', ids=['<id>'])")

    print("\nDone ✓")


if __name__ == "__main__":
    main()
