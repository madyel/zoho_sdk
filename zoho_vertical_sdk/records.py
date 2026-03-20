"""
Records API – CRUD operations on module records.

Endpoints covered:
  GET    /{module}              – list records
  GET    /{module}/{id}         – get record by id
  POST   /{module}              – create records
  PUT    /{module}              – update records (by id inside body)
  DELETE /{module}?ids=...      – delete records
  GET    /{module}/search       – search records
  GET    /{module}/{id}/{related_list}  – get related records
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class RecordsAPI:
    """
    Perform CRUD operations on Zoho Vertical Studio module records.

    Example
    -------
    >>> # List Leads
    >>> leads = client.records.list("Leads", page=1, per_page=10)
    >>> # Create a Lead
    >>> result = client.records.create("Leads", [{"Last_Name": "Rossi", "Email": "m.rossi@example.com"}])
    >>> # Update a Lead
    >>> result = client.records.update("Leads", [{"id": "123456", "Last_Name": "Bianchi"}])
    >>> # Delete Leads
    >>> result = client.records.delete("Leads", ids=["123456", "789012"])
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    def list(
        self,
        module: str,
        fields: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 200,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,  # "asc" | "desc"
        converted: Optional[bool] = None,
        approved: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve a paginated list of records from a module.

        Returns
        -------
        dict
            ``{"data": [...], "info": {"page": ..., "per_page": ..., "more_records": ...}}``
        """
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if fields:
            params["fields"] = ",".join(fields)
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order
        if converted is not None:
            params["converted"] = str(converted).lower()
        if approved is not None:
            params["approved"] = str(approved).lower()

        return self._client.get(module, params=params)

    def get(
        self,
        module: str,
        record_id: str,
        fields: Optional[List[str]] = None,
    ) -> dict:
        """
        Get a single record by its ID.

        Returns
        -------
        dict
            The record dict (first item in the ``data`` array).
        """
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        data = self._client.get(f"{module}/{record_id}", params=params or None)
        records = data.get("data", [])
        return records[0] if records else {}

    def get_all(
        self,
        module: str,
        fields: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        **kwargs,
    ) -> List[dict]:
        """
        Auto-paginate and yield ALL records from a module.

        Warning: can make many API calls for large datasets.
        """
        page = 1
        all_records: List[dict] = []

        while True:
            resp = self.list(
                module,
                fields=fields,
                page=page,
                per_page=200,
                sort_by=sort_by,
                sort_order=sort_order,
                **kwargs,
            )
            records = resp.get("data", [])
            all_records.extend(records)

            info = resp.get("info", {})
            if not info.get("more_records", False):
                break
            page += 1

        return all_records

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(self, module: str, records: List[dict]) -> List[dict]:
        """
        Create one or more records.

        Parameters
        ----------
        module : str
            Module API name, e.g. ``"Leads"``.
        records : list[dict]
            List of field-value dicts (max 100 per call).

        Returns
        -------
        list[dict]
            List of response items, each containing ``code``, ``message``,
            ``details`` (with ``id`` on success).
        """
        payload = {"data": records}
        resp = self._client.post(module, json=payload)
        return resp.get("data", [])

    def create_one(self, module: str, record: dict) -> dict:
        """Convenience wrapper to create a single record."""
        results = self.create(module, [record])
        return results[0] if results else {}

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, module: str, records: List[dict]) -> List[dict]:
        """
        Update one or more records. Each dict must contain ``"id"``.

        Returns
        -------
        list[dict]
            Response items with ``code`` and ``message``.
        """
        payload = {"data": records}
        resp = self._client.put(module, json=payload)
        return resp.get("data", [])

    def update_one(self, module: str, record_id: str, data: dict) -> dict:
        """Update a single record by ID."""
        data_with_id = {"id": record_id, **data}
        results = self.update(module, [data_with_id])
        return results[0] if results else {}

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert(
        self,
        module: str,
        records: List[dict],
        duplicate_check_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Create or update (upsert) records.

        Parameters
        ----------
        duplicate_check_fields : list[str], optional
            Fields used to detect duplicates.
        """
        params = {}
        if duplicate_check_fields:
            params["duplicate_check_fields"] = ",".join(duplicate_check_fields)

        payload = {"data": records}
        resp = self._client.post(
            f"{module}/upsert",
            json=payload,
            params=params or None,
        )
        return resp.get("data", [])

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, module: str, ids: List[str]) -> List[dict]:
        """
        Delete records by ID.

        Parameters
        ----------
        ids : list[str]
            Up to 100 record IDs.
        """
        params = {"ids": ",".join(ids)}
        resp = self._client.delete(module, params=params)
        return resp.get("data", [])

    def delete_one(self, module: str, record_id: str) -> dict:
        """Delete a single record."""
        results = self.delete(module, [record_id])
        return results[0] if results else {}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        module: str,
        criteria: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        word: Optional[str] = None,
        converted: Optional[bool] = None,
        approved: Optional[bool] = None,
        page: int = 1,
        per_page: int = 200,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Search records using criteria, email, phone, or word.

        Parameters
        ----------
        criteria : str, optional
            ZOQL-like criteria string, e.g. ``"(Last_Name:equals:Rossi)"``.
        email : str, optional
            Exact email match.
        phone : str, optional
            Exact phone match.
        word : str, optional
            Full-text keyword search.
        """
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if criteria:
            params["criteria"] = criteria
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        if word:
            params["word"] = word
        if converted is not None:
            params["converted"] = str(converted).lower()
        if approved is not None:
            params["approved"] = str(approved).lower()
        if fields:
            params["fields"] = ",".join(fields)

        return self._client.get(f"{module}/search", params=params)

    # ------------------------------------------------------------------
    # Related records
    # ------------------------------------------------------------------

    def get_related(
        self,
        module: str,
        record_id: str,
        related_list_api_name: str,
        page: int = 1,
        per_page: int = 200,
    ) -> Dict[str, Any]:
        """
        Retrieve related records for a parent record.

        Example
        -------
        >>> contacts = client.records.get_related("Accounts", "9876", "Contacts")
        """
        params = {"page": page, "per_page": per_page}
        return self._client.get(
            f"{module}/{record_id}/{related_list_api_name}",
            params=params,
        )

    # ------------------------------------------------------------------
    # Notes & Attachments (common sub-resources)
    # ------------------------------------------------------------------

    def get_notes(
        self,
        module: str,
        record_id: str,
        page: int = 1,
        per_page: int = 200,
    ) -> Dict[str, Any]:
        """Get notes attached to a record."""
        return self.get_related(module, record_id, "Notes", page, per_page)

    def create_note(
        self,
        module: str,
        record_id: str,
        note_title: str,
        note_content: str,
    ) -> dict:
        """Create a note on a record."""
        payload = {
            "data": [
                {
                    "Note_Title": note_title,
                    "Note_Content": note_content,
                    "Parent_Id": {
                        "module": {"api_name": module},
                        "id": record_id,
                    },
                }
            ]
        }
        resp = self._client.post("Notes", json=payload)
        results = resp.get("data", [])
        return results[0] if results else {}

    def get_attachments(
        self,
        module: str,
        record_id: str,
        page: int = 1,
        per_page: int = 200,
    ) -> Dict[str, Any]:
        """Get file attachments of a record."""
        return self.get_related(module, record_id, "Attachments", page, per_page)

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def get_timeline(
        self,
        module: str,
        record_id: str,
        page: int = 1,
        per_page: int = 200,
    ) -> Dict[str, Any]:
        """Retrieve the activity timeline for a record."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        return self._client.get(
            f"{module}/{record_id}/timeline",
            params=params,
        )
