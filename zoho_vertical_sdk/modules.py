"""
Modules API – wraps /settings/modules endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class ModulesAPI:
    """
    Access the Modules Settings API.

    Example
    -------
    >>> modules = client.modules.list_modules()
    >>> for m in modules:
    ...     print(m["api_name"], m["plural_label"])
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def list_modules(
        self,
        status: Optional[str] = None,
    ) -> List[dict]:
        """
        Retrieve all modules available in the account.

        Parameters
        ----------
        status : str, optional
            Filter by status: ``visible``, ``user_hidden``, ``system_hidden``,
            ``scheduled_for_deletion``. Multiple values comma-separated.

        Returns
        -------
        list[dict]
            List of module metadata dicts.
        """
        params = {}
        if status:
            params["status"] = status

        data = self._client.get("settings/modules", params=params or None)
        return data.get("modules", [])

    def get_module(self, api_name: str) -> dict:
        """
        Retrieve metadata for a single module.

        Parameters
        ----------
        api_name : str
            The module's API name, e.g. ``"Leads"``.
        """
        data = self._client.get(f"settings/modules/{api_name}")
        modules = data.get("modules", [])
        return modules[0] if modules else {}
