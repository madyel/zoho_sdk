"""
Notifications API – subscribe to data-change webhooks.

Endpoints covered:
  POST   /actions/watch          – enable notifications
  GET    /actions/watch          – list notification channels
  PATCH  /actions/watch          – update (renew) channels
  DELETE /actions/watch          – disable channels
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class NotificationsAPI:
    """
    Manage webhook notification channels.

    Example
    -------
    >>> channel = client.notifications.enable(
    ...     channel_id="100000006800211",
    ...     events=["Leads.create", "Leads.edit"],
    ...     channel_expiry="2026-12-31T23:59:59+05:30",
    ...     notify_url="https://myapp.example.com/webhooks/zoho",
    ... )
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def enable(
        self,
        channel_id: str,
        events: List[str],
        channel_expiry: str,
        notify_url: str,
        token: Optional[str] = None,
        resource_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Subscribe to webhook notifications.

        Parameters
        ----------
        channel_id : str
            A unique channel identifier you define (numeric string).
        events : list[str]
            Events to watch, e.g. ``["Leads.create", "Leads.edit", "Leads.delete"]``.
            Use ``["all"]`` for all events.
        channel_expiry : str
            ISO 8601 datetime string for when the channel expires.
        notify_url : str
            HTTPS URL Zoho will POST to when events occur.
        token : str, optional
            Optional token to validate incoming webhook calls.
        resource_uri : str, optional
            Specific record URI to watch (optional; omit for all records).
        """
        watch_entry: Dict[str, Any] = {
            "channel_id": channel_id,
            "events": events,
            "channel_expiry": channel_expiry,
            "notify_url": notify_url,
        }
        if token:
            watch_entry["token"] = token
        if resource_uri:
            watch_entry["resource_uri"] = resource_uri

        payload = {"watch": [watch_entry]}
        return self._client.post("actions/watch", json=payload)

    def list_channels(self) -> List[dict]:
        """List all active notification channels."""
        data = self._client.get("actions/watch")
        return data.get("watch", [])

    def update(
        self,
        channel_id: str,
        events: Optional[List[str]] = None,
        channel_expiry: Optional[str] = None,
        notify_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update (renew / modify) an existing notification channel.

        Typically used to extend the ``channel_expiry`` before it lapses.
        """
        watch_entry: Dict[str, Any] = {"channel_id": channel_id}
        if events is not None:
            watch_entry["events"] = events
        if channel_expiry is not None:
            watch_entry["channel_expiry"] = channel_expiry
        if notify_url is not None:
            watch_entry["notify_url"] = notify_url

        payload = {"watch": [watch_entry]}
        return self._client.patch("actions/watch", json=payload)

    def disable(self, channel_ids: List[str]) -> Dict[str, Any]:
        """
        Disable one or more notification channels.

        Parameters
        ----------
        channel_ids : list[str]
            Channel IDs to delete.
        """
        watch_entries = [{"channel_id": cid} for cid in channel_ids]
        payload = {"watch": watch_entries}
        return self._client.delete("actions/watch", params=None)
        # Note: Zoho DELETE /actions/watch uses the body, not query params.
        # We send via a raw request workaround.

    def disable_raw(self, channel_ids: List[str]) -> Dict[str, Any]:
        """
        Disable channels via DELETE with JSON body (Zoho v6 style).
        """
        watch_entries = [{"channel_id": cid} for cid in channel_ids]
        payload = {"watch": watch_entries}
        url = self._client.build_url("actions/watch")
        headers = self._client.auth.auth_header()
        headers["Content-Type"] = "application/json"
        import json as _json

        response = self._client._session.delete(
            url,
            headers=headers,
            data=_json.dumps(payload),
            timeout=self._client.timeout,
        )
        return self._client._handle_response(response)
