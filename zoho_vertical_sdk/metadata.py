"""
Metadata API – fields, layouts, custom views, related lists.

Endpoints covered:
  GET /settings/fields?module={api_name}
  GET /settings/fields/{field_id}?module={api_name}
  GET /settings/layouts?module={api_name}
  GET /settings/layouts/{layout_id}?module={api_name}
  GET /settings/custom_views?module={api_name}
  GET /settings/custom_views/{cv_id}?module={api_name}
  GET /settings/related_lists?module={api_name}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class MetadataAPI:
    """
    Access field/layout/custom-view/related-list metadata.

    Example
    -------
    >>> fields = client.metadata.get_fields("Leads")
    >>> layouts = client.metadata.get_layouts("Contacts")
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    def get_fields(
        self,
        module: str,
        field_type: Optional[str] = None,
    ) -> List[dict]:
        """
        Retrieve all fields of a module.

        Parameters
        ----------
        module : str
            Module API name, e.g. ``"Leads"``.
        field_type : str, optional
            Filter by field type, e.g. ``"lookup"``.
        """
        params: dict = {"module": module}
        if field_type:
            params["type"] = field_type

        data = self._client.get("settings/fields", params=params)
        return data.get("fields", [])

    def get_field(self, module: str, field_id: str) -> dict:
        """Get a single field's metadata by its ID."""
        data = self._client.get(
            f"settings/fields/{field_id}",
            params={"module": module},
        )
        fields = data.get("fields", [])
        return fields[0] if fields else {}

    # ------------------------------------------------------------------
    # Layouts
    # ------------------------------------------------------------------

    def get_layouts(self, module: str) -> List[dict]:
        """Retrieve all layouts for a module."""
        data = self._client.get("settings/layouts", params={"module": module})
        return data.get("layouts", [])

    def get_layout(self, module: str, layout_id: str) -> dict:
        """Get a single layout by its ID."""
        data = self._client.get(
            f"settings/layouts/{layout_id}",
            params={"module": module},
        )
        layouts = data.get("layouts", [])
        return layouts[0] if layouts else {}

    # ------------------------------------------------------------------
    # Custom Views
    # ------------------------------------------------------------------

    def get_custom_views(
        self,
        module: str,
        page: int = 1,
        per_page: int = 200,
    ) -> List[dict]:
        """Retrieve all custom views for a module."""
        params = {"module": module, "page": page, "per_page": per_page}
        data = self._client.get("settings/custom_views", params=params)
        return data.get("custom_views", [])

    def get_custom_view(self, module: str, cv_id: str) -> dict:
        """Get a single custom view by its ID."""
        data = self._client.get(
            f"settings/custom_views/{cv_id}",
            params={"module": module},
        )
        views = data.get("custom_views", [])
        return views[0] if views else {}

    # ------------------------------------------------------------------
    # Related Lists
    # ------------------------------------------------------------------

    def get_related_lists(self, module: str) -> List[dict]:
        """Retrieve all related lists for a module."""
        data = self._client.get(
            "settings/related_lists",
            params={"module": module},
        )
        return data.get("related_lists", [])
