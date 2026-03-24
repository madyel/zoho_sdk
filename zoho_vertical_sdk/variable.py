"""
VariableAPI  –  Zoho People Variable REST API
==============================================

Gestisce variabili e gruppi di variabili.

Endpoint Variabili:
    GET    /variable/getVariables
    GET    /variable/getVariable
    POST   /variable/addVariable
    POST   /variable/updateVariable
    DELETE /variable/deleteVariable
    GET    /variable/getVariablesByGroup

Endpoint Gruppi:
    GET    /variable/getVariableGroups
    GET    /variable/getVariableGroup
    POST   /variable/addVariableGroup
    PUT    /variable/updateVariableGroup
    DELETE /variable/deleteVariableGroup

Scope OAuth: ZohoPeople.variable.ALL
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class VariableAPI:
    """
    Wrapper per le API Zoho People Variable.

    Usato tramite:
        client.variable.get_all()
        client.variable.add("Budget2026", "50000", "1")
        client.variable.get_groups()
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Variabili
    # ------------------------------------------------------------------

    def get_all(self, page: int = 1, per_page: int = 200) -> List[Dict[str, Any]]:
        """
        Recupera tutte le variabili.

        Endpoint: GET /variable/getVariables
        """
        params: Dict[str, Any] = {"sIndex": page, "resLen": per_page}
        data     = self._client.get("v3/variable/getVariables", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get(self, variable_id: str) -> Dict[str, Any]:
        """
        Recupera una variabile specifica.

        Endpoint: GET /variable/getVariable
        """
        data     = self._client.get("v3/variable/getVariable",
                                    params={"variableId": variable_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    def add(self, name: str, value: str, var_type: str) -> Dict[str, Any]:
        """
        Crea una nuova variabile.

        Endpoint: POST /variable/addVariable

        Parameters
        ----------
        name : str
            Nome della variabile.
        value : str
            Valore iniziale.
        var_type : str
            Tipo (es. "1" = testo, "2" = numero).
        """
        payload: Dict[str, Any] = {"name": name, "value": value, "type": var_type}
        return self._client.form_post("v3/variable/addVariable", data=payload)

    def update(self, variable_id: str, value: str) -> Dict[str, Any]:
        """
        Aggiorna il valore di una variabile.

        Endpoint: POST /variable/updateVariable
        """
        payload: Dict[str, Any] = {"variableId": variable_id, "value": value}
        return self._client.form_post("v3/variable/updateVariable", data=payload)

    def delete(self, variable_id: str) -> Dict[str, Any]:
        """
        Elimina una variabile.

        Endpoint: DELETE /variable/deleteVariable
        """
        return self._client.delete("v3/variable/deleteVariable",
                                   params={"variableId": variable_id})

    def get_by_group(self, group_id: str) -> List[Dict[str, Any]]:
        """
        Recupera le variabili appartenenti a un gruppo.

        Endpoint: GET /variable/getVariablesByGroup
        """
        data     = self._client.get("v3/variable/getVariablesByGroup",
                                    params={"groupId": group_id})
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Gruppi
    # ------------------------------------------------------------------

    def get_groups(self) -> List[Dict[str, Any]]:
        """
        Recupera tutti i gruppi di variabili.

        Endpoint: GET /variable/getVariableGroups
        """
        data     = self._client.get("v3/variable/getVariableGroups")
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_group(self, group_id: str) -> Dict[str, Any]:
        """
        Recupera uno specifico gruppo.

        Endpoint: GET /variable/getVariableGroup
        """
        data     = self._client.get("v3/variable/getVariableGroup",
                                    params={"groupId": group_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    def add_group(self, group_name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea un nuovo gruppo di variabili.

        Endpoint: POST /variable/addVariableGroup
        """
        payload: Dict[str, Any] = {"groupName": group_name}
        if description:
            payload["description"] = description
        return self._client.form_post("v3/variable/addVariableGroup", data=payload)

    def update_group(self, group_id: str, group_name: str) -> Dict[str, Any]:
        """
        Aggiorna un gruppo di variabili.

        Endpoint: PUT /variable/updateVariableGroup
        """
        payload: Dict[str, Any] = {"groupId": group_id, "groupName": group_name}
        return self._client.put("v3/variable/updateVariableGroup", json=payload)

    def delete_group(self, group_id: str) -> Dict[str, Any]:
        """
        Elimina un gruppo di variabili.

        Endpoint: DELETE /variable/deleteVariableGroup
        """
        return self._client.delete("v3/variable/deleteVariableGroup",
                                   params={"groupId": group_id})
