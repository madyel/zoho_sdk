"""
Query API – COQL (CRM Object Query Language) for Zoho Vertical Studio v6.

Endpoint: POST /coql

COQL supports SELECT queries with WHERE, ORDER BY, GROUP BY, LIMIT / OFFSET,
JOINs via lookup dot-notation, and aggregate functions (COUNT, SUM, AVG, MIN, MAX).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class QueryAPI:
    """
    Execute COQL queries against Zoho Vertical Studio.

    Example
    -------
    >>> # Raw query string
    >>> result = client.query.execute(
    ...     "SELECT Last_Name, Email FROM Leads WHERE Last_Name IS NOT NULL LIMIT 0, 10"
    ... )
    >>> print(result["data"])

    >>> # Builder pattern
    >>> result = (
    ...     client.query
    ...     .select("Last_Name", "Email", "Created_Time")
    ...     .from_module("Leads")
    ...     .where("Last_Name IS NOT NULL")
    ...     .order_by("Created_Time", "DESC")
    ...     .limit(offset=0, count=50)
    ...     .run()
    ... )
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client
        self._reset()

    # ------------------------------------------------------------------
    # Raw execute
    # ------------------------------------------------------------------

    def execute(self, select_query: str) -> Dict[str, Any]:
        """
        Execute a raw COQL query string.

        Parameters
        ----------
        select_query : str
            Full COQL SELECT statement.

        Returns
        -------
        dict
            ``{"data": [...], "info": {"count": ..., "more_records": ...}}``
        """
        payload = {"select_query": select_query}
        return self._client.post("coql", json=payload)

    def execute_all(self, select_query: str, max_per_page: int = 200) -> List[dict]:
        """
        Auto-paginate a COQL query and return all matching records.

        The query must **not** already contain a LIMIT clause;
        this method appends one automatically.

        Note: Zoho COQL can paginate up to 10 000 records per unique criteria.
        """
        offset = 0
        all_data: List[dict] = []

        while True:
            paged_query = f"{select_query.rstrip()} LIMIT {offset}, {max_per_page}"
            result = self.execute(paged_query)
            records = result.get("data", [])
            all_data.extend(records)

            info = result.get("info", {})
            if not info.get("more_records", False):
                break
            offset += max_per_page

        return all_data

    # ------------------------------------------------------------------
    # Fluent builder
    # ------------------------------------------------------------------

    def _reset(self) -> "QueryAPI":
        self._fields: List[str] = []
        self._module: str = ""
        self._where: str = ""
        self._group_by: str = ""
        self._order_by: str = ""
        self._offset: int = 0
        self._count: int = 200
        return self

    def select(self, *fields: str) -> "QueryAPI":
        """Specify fields to SELECT. Supports aliases: ``"Last_Name AS name"``."""
        self._fields = list(fields)
        return self

    def from_module(self, module: str) -> "QueryAPI":
        """Specify the FROM module."""
        self._module = module
        return self

    def where(self, criteria: str) -> "QueryAPI":
        """
        Set the WHERE clause.

        Parameters
        ----------
        criteria : str
            e.g. ``"(Last_Name is not null and Email like '%zoho%')"``
        """
        self._where = criteria
        return self

    def group_by(self, *fields: str) -> "QueryAPI":
        """Set GROUP BY fields."""
        self._group_by = ", ".join(fields)
        return self

    def order_by(self, field: str, direction: str = "ASC") -> "QueryAPI":
        """Set ORDER BY field and direction (``ASC`` or ``DESC``)."""
        self._order_by = f"{field} {direction.upper()}"
        return self

    def limit(self, offset: int = 0, count: int = 200) -> "QueryAPI":
        """
        Set LIMIT clause.

        Parameters
        ----------
        offset : int
            Number of records to skip.
        count : int
            Number of records to fetch (max 2000).
        """
        self._offset = offset
        self._count = min(count, 2000)
        return self

    def build(self) -> str:
        """Build the COQL query string without executing it."""
        if not self._fields:
            raise ValueError("No fields specified. Call .select() first.")
        if not self._module:
            raise ValueError("No module specified. Call .from_module() first.")

        fields_str = ", ".join(
            f"'{f}'" if " " in f else f for f in self._fields
        )
        query = f"SELECT {fields_str} FROM {self._module}"

        if self._where:
            # Wrap in parens if not already
            w = self._where.strip()
            if not (w.startswith("(") and w.endswith(")")):
                w = f"({w})"
            query += f" WHERE {w}"

        if self._group_by:
            query += f" GROUP BY {self._group_by}"

        if self._order_by:
            query += f" ORDER BY {self._order_by}"

        query += f" LIMIT {self._offset}, {self._count}"

        return query

    def run(self) -> Dict[str, Any]:
        """Build and execute the query, then reset the builder."""
        q = self.build()
        self._reset()
        return self.execute(q)

    def run_all(self) -> List[dict]:
        """Build, execute with auto-pagination, then reset."""
        # Build without limit so execute_all can append its own
        if not self._fields:
            raise ValueError("No fields specified. Call .select() first.")
        if not self._module:
            raise ValueError("No module specified. Call .from_module() first.")

        fields_str = ", ".join(
            f"'{f}'" if " " in f else f for f in self._fields
        )
        query = f"SELECT {fields_str} FROM {self._module}"

        if self._where:
            w = self._where.strip()
            if not (w.startswith("(") and w.endswith(")")):
                w = f"({w})"
            query += f" WHERE {w}"

        if self._group_by:
            query += f" GROUP BY {self._group_by}"

        if self._order_by:
            query += f" ORDER BY {self._order_by}"

        self._reset()
        return self.execute_all(query, max_per_page=self._count or 200)
