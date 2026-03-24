"""
PerformanceAPI  –  Zoho People Performance REST API
====================================================

Gestisce competenze, KRA e skill per le valutazioni delle prestazioni.

Endpoint Competenze:
    GET    /performance/getCompetencies
    POST   /performance/addCompetency
    PUT    /performance/updateCompetency
    DELETE /performance/deleteCompetency

Endpoint KRA:
    GET    /performance/getKRAs
    POST   /performance/addKRA
    PUT    /performance/updateKRA
    DELETE /performance/deleteKRA

Endpoint Skill:
    GET    /performance/getSkills
    POST   /performance/addSkill
    PUT    /performance/updateSkill
    DELETE /performance/deleteSkill

Scope OAuth: ZohoPeople.performance.ALL
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class PerformanceAPI:
    """
    Wrapper per le API Zoho People Performance.

    Usato tramite:
        client.performance.get_competencies()
        client.performance.add_competency("Leadership", "Team leadership skill")
        client.performance.get_kras()
        client.performance.get_skills()
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Competenze
    # ------------------------------------------------------------------

    def get_competencies(self, page: int = 1, per_page: int = 200) -> List[Dict[str, Any]]:
        """
        Recupera la libreria delle competenze.

        Endpoint: GET /performance/getCompetencies
        """
        params: Dict[str, Any] = {"sIndex": page, "resLen": per_page}
        data     = self._client.get("v3/performance/getCompetencies", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def add_competency(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggiunge una competenza alla libreria.

        Endpoint: POST /performance/addCompetency
        """
        payload: Dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        return self._client.form_post("v3/performance/addCompetency", data=payload)

    def update_competency(
        self,
        competency_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna una competenza.

        Endpoint: PUT /performance/updateCompetency
        """
        payload: Dict[str, Any] = {"competencyId": competency_id, "name": name}
        if description:
            payload["description"] = description
        return self._client.put("v3/performance/updateCompetency", json=payload)

    def delete_competency(self, competency_id: str) -> Dict[str, Any]:
        """
        Elimina una competenza.

        Endpoint: DELETE /performance/deleteCompetency
        """
        return self._client.delete("v3/performance/deleteCompetency",
                                   params={"competencyId": competency_id})

    # ------------------------------------------------------------------
    # KRA (Key Result Areas)
    # ------------------------------------------------------------------

    def get_kras(self, page: int = 1) -> List[Dict[str, Any]]:
        """
        Recupera la libreria KRA.

        Endpoint: GET /performance/getKRAs
        """
        params: Dict[str, Any] = {"sIndex": page}
        data     = self._client.get("v3/performance/getKRAs", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def add_kra(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggiunge una KRA alla libreria.

        Endpoint: POST /performance/addKRA
        """
        payload: Dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        return self._client.form_post("v3/performance/addKRA", data=payload)

    def update_kra(
        self,
        kra_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna una KRA.

        Endpoint: PUT /performance/updateKRA
        """
        payload: Dict[str, Any] = {"kraId": kra_id, "name": name}
        if description:
            payload["description"] = description
        return self._client.put("v3/performance/updateKRA", json=payload)

    def delete_kra(self, kra_id: str) -> Dict[str, Any]:
        """
        Elimina una KRA.

        Endpoint: DELETE /performance/deleteKRA
        """
        return self._client.delete("v3/performance/deleteKRA", params={"kraId": kra_id})

    # ------------------------------------------------------------------
    # Skill
    # ------------------------------------------------------------------

    def get_skills(self, page: int = 1) -> List[Dict[str, Any]]:
        """
        Recupera la libreria skill.

        Endpoint: GET /performance/getSkills
        """
        params: Dict[str, Any] = {"sIndex": page}
        data     = self._client.get("v3/performance/getSkills", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def add_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        Aggiunge una skill alla libreria.

        Endpoint: POST /performance/addSkill
        """
        payload: Dict[str, Any] = {"skillName": skill_name}
        return self._client.form_post("v3/performance/addSkill", data=payload)

    def update_skill(self, skill_id: str, skill_name: str) -> Dict[str, Any]:
        """
        Aggiorna una skill.

        Endpoint: PUT /performance/updateSkill
        """
        payload: Dict[str, Any] = {"skillId": skill_id, "skillName": skill_name}
        return self._client.put("v3/performance/updateSkill", json=payload)

    def delete_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Elimina una skill.

        Endpoint: DELETE /performance/deleteSkill
        """
        return self._client.delete("v3/performance/deleteSkill", params={"skillId": skill_id})
