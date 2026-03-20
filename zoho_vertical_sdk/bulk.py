"""
Bulk API – asynchronous bulk read/write operations.

Endpoints covered:
  POST   /bulk/read              – create a bulk-read job
  GET    /bulk/read/{job_id}     – get bulk-read job status
  GET    /bulk/read/{job_id}/result – download bulk-read result (CSV)
  DELETE /bulk/read/{job_id}     – delete a bulk-read job
  POST   /bulk/write             – create a bulk-write job
  GET    /bulk/write/{job_id}    – get bulk-write job status
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class BulkAPI:
    """
    Manage async bulk read / write jobs.

    Bulk Read Example
    -----------------
    >>> job = client.bulk.create_read_job(
    ...     module="Leads",
    ...     fields=["Last_Name", "Email"],
    ...     criteria="(Last_Name is not null)",
    ... )
    >>> job_id = job["data"][0]["details"]["id"]
    >>> # Poll until complete
    >>> status = client.bulk.wait_for_read_job(job_id)
    >>> csv_bytes = client.bulk.download_read_result(job_id)
    >>> with open("leads.csv", "wb") as f:
    ...     f.write(csv_bytes)
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Bulk Read
    # ------------------------------------------------------------------

    def create_read_job(
        self,
        module: str,
        fields: Optional[List[str]] = None,
        criteria: Optional[str] = None,
        page: int = 1,
        cvid: Optional[str] = None,
        file_type: str = "csv",
    ) -> Dict[str, Any]:
        """
        Create a bulk-read job.

        Parameters
        ----------
        module : str
            Module API name, e.g. ``"Leads"``.
        fields : list[str], optional
            Specific field API names to export. If omitted, all fields are exported.
        criteria : str, optional
            Filter criteria, e.g. ``"(Email is not null)"``.
        page : int
            Page number to export (each page = 200 000 records, max).
        cvid : str, optional
            Custom view ID to use as filter.
        file_type : str
            ``"csv"`` (default) or ``"ics"`` for events.
        """
        query: Dict[str, Any] = {
            "module": {"api_name": module},
            "file_type": file_type,
            "page": page,
        }
        if fields:
            query["fields"] = [{"api_name": f} for f in fields]
        if criteria:
            query["criteria"] = criteria
        if cvid:
            query["cvid"] = cvid

        payload = {"query": query}
        return self._client.post("bulk/read", json=payload)

    def get_read_job(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a bulk-read job."""
        return self._client.get(f"bulk/read/{job_id}")

    def download_read_result(self, job_id: str) -> bytes:
        """
        Download the result file of a completed bulk-read job.

        Returns
        -------
        bytes
            Raw CSV (or ICS) content.
        """
        url = self._client.build_url(f"bulk/read/{job_id}/result")
        headers = self._client.auth.auth_header()
        response = self._client._session.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        return response.content

    def delete_read_job(self, job_id: str) -> Dict[str, Any]:
        """Delete a bulk-read job."""
        return self._client.delete(f"bulk/read/{job_id}")

    def wait_for_read_job(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ) -> Dict[str, Any]:
        """
        Poll a bulk-read job until it completes or fails.

        Parameters
        ----------
        poll_interval : float
            Seconds between polls.
        timeout : float
            Max seconds to wait before raising ``TimeoutError``.

        Returns
        -------
        dict
            Final job status response.

        Raises
        ------
        TimeoutError
            If the job doesn't complete within ``timeout`` seconds.
        RuntimeError
            If the job ends in an error state.
        """
        deadline = time.time() + timeout

        while time.time() < deadline:
            resp = self.get_read_job(job_id)
            data_list = resp.get("data", [])
            if not data_list:
                raise RuntimeError(f"Unexpected response for job {job_id}: {resp}")

            state = data_list[0].get("state", "").upper()

            if state == "COMPLETED":
                return resp
            if state in ("FAILED", "DELETED"):
                raise RuntimeError(f"Bulk read job {job_id} ended with state: {state}")

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Bulk read job {job_id} did not complete within {timeout}s"
        )

    # ------------------------------------------------------------------
    # Bulk Write
    # ------------------------------------------------------------------

    def create_write_job(
        self,
        module: str,
        operation: str,
        resource: List[Dict[str, Any]],
        ignore_empty: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a bulk-write job.

        Parameters
        ----------
        module : str
            Module API name.
        operation : str
            ``"insert"``, ``"update"``, or ``"upsert"``.
        resource : list[dict]
            List of resource dicts each describing the file to upload.
            See Zoho docs for full schema.
        ignore_empty : bool
            Whether to ignore empty values in the uploaded file.
        """
        payload = {
            "operation": operation,
            "ignore_empty": ignore_empty,
            "resource": [
                {"type": "data", "module": {"api_name": module}, **r}
                for r in resource
            ],
        }
        return self._client.post("bulk/write", json=payload)

    def get_write_job(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a bulk-write job."""
        return self._client.get(f"bulk/write/{job_id}")

    def wait_for_write_job(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ) -> Dict[str, Any]:
        """Poll a bulk-write job until completion. Same semantics as wait_for_read_job."""
        deadline = time.time() + timeout

        while time.time() < deadline:
            resp = self.get_write_job(job_id)
            data_list = resp.get("data", [])
            if not data_list:
                raise RuntimeError(f"Unexpected response for job {job_id}: {resp}")

            state = data_list[0].get("state", "").upper()

            if state == "COMPLETED":
                return resp
            if state in ("FAILED", "DELETED"):
                raise RuntimeError(f"Bulk write job {job_id} ended with state: {state}")

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Bulk write job {job_id} did not complete within {timeout}s"
        )
