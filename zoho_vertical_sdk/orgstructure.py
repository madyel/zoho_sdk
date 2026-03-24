"""
OrgStructureAPI  –  Zoho People Organization Structure REST API
================================================================

Gestisce l'organigramma aziendale.

Endpoint:
    GET  /orgstructure/getRecord
    GET  /orgstructure/getRecords
    POST /orgstructure/addRecord
    PUT  /orgstructure/updateRecord

Scope OAuth: ZohoPeople.orgstructure.ALL
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class OrgStructureAPI:
    """
    Wrapper per le API Zoho People Organization Structure.

    Usato tramite:
        client.orgstructure.get_records()
        client.orgstructure.get_record(record_id)
        client.orgstructure.add_record("Divisione IT", parent_entity_id="DEPT001")
        client.orgstructure.update_record(record_id, "IT & Digital")
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def get_record(self, record_id: str) -> Dict[str, Any]:
        """
        Recupera un singolo record dell'organigramma.

        Endpoint: GET /orgstructure/getRecord
        """
        data     = self._client.get("v3/orgstructure/getRecord", params={"recordId": record_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    def get_records(self, page: int = 1, per_page: int = 200) -> List[Dict[str, Any]]:
        """
        Recupera tutti i record dell'organigramma.

        Endpoint: GET /orgstructure/getRecords
        """
        params: Dict[str, Any] = {"sIndex": page, "resLen": per_page}
        data     = self._client.get("v3/orgstructure/getRecords", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def add_record(
        self,
        name: str,
        parent_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea un nuovo nodo nell'organigramma.

        Endpoint: POST /orgstructure/addRecord

        Parameters
        ----------
        name : str
            Nome dell'entità (es. "Divisione IT").
        parent_entity_id : str, optional
            ID dell'entità padre. Se omesso, crea un nodo radice.
        """
        payload: Dict[str, Any] = {"name": name}
        if parent_entity_id:
            payload["parentEntityId"] = parent_entity_id
        return self._client.form_post("v3/orgstructure/addRecord", data=payload)

    def update_record(
        self,
        record_id: str,
        name: str,
        parent_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna un nodo dell'organigramma.

        Endpoint: PUT /orgstructure/updateRecord
        """
        payload: Dict[str, Any] = {"recordId": record_id, "name": name}
        if parent_entity_id:
            payload["parentEntityId"] = parent_entity_id
        return self._client.put("v3/orgstructure/updateRecord", json=payload)
