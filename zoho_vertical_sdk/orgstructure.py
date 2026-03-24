"""
OrgStructureAPI  –  Zoho People Organization Structure REST API v3
===================================================================

Endpoint:
    GET    v3/organization/entities           (lista entità)
    POST   v3/organization/entities           (crea entità)
    PUT    v3/organization/entities/{id}      (aggiorna entità)

Scope OAuth: ZOHOPEOPLE.orgstructure.READ / ZOHOPEOPLE.orgstructure.CREATE
             ZOHOPEOPLE.orgstructure.UPDATE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class OrgStructureAPI:
    """
    Wrapper per le API Zoho People Organization Structure v3.

    Usato tramite:
        client.orgstructure.get_entities()
        client.orgstructure.create_entity("Divisione IT", parent_entity_id="DEPT001")
        client.orgstructure.update_entity(entity_id, "IT & Digital")
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def get_entities(
        self,
        parent_entity_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Recupera le entità dell'organigramma.

        Endpoint: GET v3/organization/entities

        Parameters
        ----------
        parent_entity_id : str, optional
            ID dell'entità padre (per filtrare i figli diretti).
        limit : int
            Numero massimo di record.
        """
        params: Dict[str, Any] = {"limit": limit}
        if parent_entity_id:
            params["parent_entity_id"] = parent_entity_id
        data   = self._client.get("v3/organization/entities", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def create_entity(
        self,
        name: str,
        parent_entity_id: Optional[str] = None,
        head_employee_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea un nuovo nodo nell'organigramma.

        Endpoint: POST v3/organization/entities

        Parameters
        ----------
        name : str
            Nome dell'entità (es. "Divisione IT").
        parent_entity_id : str, optional
            ID dell'entità padre. Se omesso, crea un nodo radice.
        head_employee_id : str, optional
            ID Zoho del responsabile dell'entità.
        """
        payload: Dict[str, Any] = {"name": name}
        if parent_entity_id:
            payload["parent_entity_id"] = parent_entity_id
        if head_employee_id:
            payload["head_employee_id"] = head_employee_id
        return self._client.form_post("v3/organization/entities", data=payload)

    def update_entity(
        self,
        entity_id: str,
        name: str,
        head_employee_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna un nodo dell'organigramma.

        Endpoint: PUT v3/organization/entities/{entity_id}

        Parameters
        ----------
        entity_id : str
            ID dell'entità da aggiornare.
        name : str
            Nuovo nome dell'entità.
        head_employee_id : str, optional
            ID Zoho del nuovo responsabile.
        """
        payload: Dict[str, Any] = {"name": name}
        if head_employee_id:
            payload["head_employee_id"] = head_employee_id
        return self._client.put(f"v3/organization/entities/{entity_id}", json=payload)
