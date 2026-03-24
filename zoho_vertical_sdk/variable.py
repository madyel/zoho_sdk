"""
VariableAPI  –  Zoho People Variable REST API v3
=================================================

Endpoint Variabili:
    GET    v3/settings/variables              (lista variabili)
    GET    v3/settings/variables/{id}         (singola variabile)
    POST   v3/settings/variables              (crea variabile)
    PUT    v3/settings/variables/{id}         (aggiorna variabile)
    DELETE v3/settings/variables/{id}         (elimina variabile)

Endpoint Gruppi:
    GET    v3/settings/variablegroups         (lista gruppi)
    POST   v3/settings/variablegroups         (crea gruppo)

Scope OAuth: ZOHOPEOPLE.variable.READ / ZOHOPEOPLE.variable.CREATE
             ZOHOPEOPLE.variable.UPDATE / ZOHOPEOPLE.variable.DELETE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class VariableAPI:
    """
    Wrapper per le API Zoho People Variable v3.

    Usato tramite:
        client.variable.get_all()
        client.variable.get(variable_id)
        client.variable.add("Budget2026", "50000", variable_group_id="GRP-1")
        client.variable.update(variable_id, value="60000")
        client.variable.delete(variable_id)
        client.variable.get_groups()
        client.variable.add_group("Finance", description="...")
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Variabili
    # ------------------------------------------------------------------

    def get_all(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Recupera tutte le variabili.

        Endpoint: GET v3/settings/variables
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        data   = self._client.get("v3/settings/variables", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def get(self, variable_id: str) -> Dict[str, Any]:
        """
        Recupera una variabile specifica.

        Endpoint: GET v3/settings/variables/{variable_id}
        """
        data   = self._client.get(f"v3/settings/variables/{variable_id}")
        result = data.get("data", data.get("response", {}).get("result", data))
        return result if isinstance(result, dict) else data

    def add(
        self,
        name: str,
        value: str,
        variable_group_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea una nuova variabile.

        Endpoint: POST v3/settings/variables

        Parameters
        ----------
        name : str
            Nome della variabile.
        value : str
            Valore iniziale.
        variable_group_id : str, optional
            ID del gruppo di appartenenza.
        description : str, optional
            Descrizione della variabile.
        """
        payload: Dict[str, Any] = {"name": name, "value": value}
        if variable_group_id:
            payload["variable_group_id"] = variable_group_id
        if description:
            payload["description"] = description
        return self._client.form_post("v3/settings/variables", data=payload)

    def update(
        self,
        variable_id: str,
        value: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna il valore di una variabile.

        Endpoint: PUT v3/settings/variables/{variable_id}
        """
        payload: Dict[str, Any] = {}
        if value is not None:
            payload["value"] = value
        if description is not None:
            payload["description"] = description
        return self._client.put(f"v3/settings/variables/{variable_id}", json=payload)

    def delete(self, variable_id: str) -> Dict[str, Any]:
        """
        Elimina una variabile.

        Endpoint: DELETE v3/settings/variables/{variable_id}
        """
        return self._client.delete(f"v3/settings/variables/{variable_id}")

    # ------------------------------------------------------------------
    # Gruppi
    # ------------------------------------------------------------------

    def get_groups(self) -> List[Dict[str, Any]]:
        """
        Recupera tutti i gruppi di variabili.

        Endpoint: GET v3/settings/variablegroups
        """
        data   = self._client.get("v3/settings/variablegroups")
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def add_group(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea un nuovo gruppo di variabili.

        Endpoint: POST v3/settings/variablegroups
        """
        payload: Dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        return self._client.form_post("v3/settings/variablegroups", data=payload)
