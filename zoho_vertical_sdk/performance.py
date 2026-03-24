"""
PerformanceAPI  –  Zoho People Performance REST API v3
=======================================================

Endpoint:
    GET    v3/performance/settings/kras           (libreria KRA)
    POST   v3/performance/settings/kras           (aggiunge KRA)
    GET    v3/performance/settings/competencies   (libreria competenze)
    GET    v3/performance/settings/skills         (libreria skill)

Scope OAuth: ZOHOPEOPLE.performance.READ / ZOHOPEOPLE.performance.CREATE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class PerformanceAPI:
    """
    Wrapper per le API Zoho People Performance v3.

    Usato tramite:
        client.performance.get_kras()
        client.performance.add_kra("Sviluppo prodotto", description="...", weightage=30)
        client.performance.get_competencies()
        client.performance.get_skills()
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # KRA (Key Result Areas)
    # ------------------------------------------------------------------

    def get_kras(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Recupera la libreria KRA.

        Endpoint: GET v3/performance/settings/kras
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        data   = self._client.get("v3/performance/settings/kras", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def add_kra(
        self,
        name: str,
        description: Optional[str] = None,
        weightage: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Aggiunge una KRA alla libreria.

        Endpoint: POST v3/performance/settings/kras

        Parameters
        ----------
        name : str
            Nome della KRA.
        description : str, optional
            Descrizione.
        weightage : float, optional
            Peso percentuale (es. 30 per 30%).
        """
        payload: Dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if weightage is not None:
            payload["weightage"] = weightage
        return self._client.form_post("v3/performance/settings/kras", data=payload)

    # ------------------------------------------------------------------
    # Competenze
    # ------------------------------------------------------------------

    def get_competencies(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Recupera la libreria delle competenze.

        Endpoint: GET v3/performance/settings/competencies
        """
        params: Dict[str, Any] = {"limit": limit}
        data   = self._client.get("v3/performance/settings/competencies", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Skill
    # ------------------------------------------------------------------

    def get_skills(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Recupera la libreria skill.

        Endpoint: GET v3/performance/settings/skills
        """
        params: Dict[str, Any] = {"limit": limit}
        data   = self._client.get("v3/performance/settings/skills", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []
