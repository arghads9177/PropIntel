"""HTTP client for the eBuilder Property APIs."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from agentic.agents.api_models import (
    APIIntent,
    APIRequest,
    APIResponse,
    APIResponsePayload,
    ProjectSearchResponse,
    PropertyAvailabilityResponse,
    UnsoldPropertiesResponse,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class EbuilderClientConfig:
    base_url: str
    auth_token: str
    org_code: str
    timeout: int = 30  # seconds

    @classmethod
    def from_env(cls) -> "EbuilderClientConfig":
        base_url = os.getenv("EBUILDER_API_URL")
        auth_token = os.getenv("EBUILDER_AUTH_TOKEN")
        org_code = os.getenv("EBUILDER_ORG_CODE")
        if not base_url or not auth_token or not org_code:
            missing = [
                name
                for name, value in {
                    "EBUILDER_API_URL": base_url,
                    "EBUILDER_AUTH_TOKEN": auth_token,
                    "EBUILDER_ORG_CODE": org_code,
                }.items()
                if not value
            ]
            raise ValueError(f"Missing eBuilder config variables: {', '.join(missing)}")
        return cls(base_url=base_url.rstrip("/"), auth_token=auth_token, org_code=org_code)


class EbuilderClient:
    """Lightweight client wrapping the eBuilder API endpoints."""

    PROJECT_SEARCH = "/project/search"
    AVAILABILITY = "/towerproperty/availablePropertyForWebSite"
    UNSOLD = "/towerproperty/unsoldPropertiesOfProject"

    def __init__(self, config: Optional[EbuilderClientConfig] = None) -> None:
        self.config = config or EbuilderClientConfig.from_env()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": self.config.auth_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    # Public API -------------------------------------------------------

    def fetch(self, request: APIRequest) -> APIResponse:
        """Route request based on intent."""
        if request.intent in {APIIntent.PROJECT_METADATA}:
            payload = self._project_search(request)
        elif request.intent in {
            APIIntent.AVAILABILITY_BY_PROJECT,
            APIIntent.BOOKING_STATUS,
        }:
            payload = self._availability(request)
        elif request.intent in {
            APIIntent.AVAILABILITY_BY_CITY,
            APIIntent.AVAILABILITY_SUMMARY,
            APIIntent.PRICE_LOOKUP,
            APIIntent.PRICE_COMPARISON,
            APIIntent.UNSOLD_PROPERTIES,
        }:
            payload = self._unsold(request)
        else:
            payload = APIResponsePayload(
                status="unsupported_intent",
                data={"message": "Intent not supported by API client"},
                endpoint=None,
            )

        return APIResponse(intent=request.intent, payload=payload, metadata={"client": "ebuilder"})

    # Endpoint wrappers -----------------------------------------------

    def _project_search(self, request: APIRequest) -> APIResponsePayload:
        payload: Dict[str, Any] = {"ocode": self.config.org_code}
        if request.shortname:
            payload["shortname"] = request.shortname
        if request.branch:
            payload["branch"] = request.branch
        payload.update(request.extra_params)
        raw = self._post_json(self.PROJECT_SEARCH, payload)
        data = ProjectSearchResponse(projects=raw or [], count=len(raw or []))
        return APIResponsePayload(
            status="ok",
            data={"projects": data.projects, "count": data.count},
            endpoint=self.PROJECT_SEARCH,
            raw_response=raw,
        )

    def _availability(self, request: APIRequest) -> APIResponsePayload:
        payload: Dict[str, Any] = {"ocode": self.config.org_code}
        if request.shortname:
            payload["shortname"] = request.shortname
        if request.tower_name:
            payload["tname"] = request.tower_name
        if request.property_type:
            payload["ptype"] = request.property_type
        if request.property_name:
            payload["pname"] = request.property_name
        if request.branch:
            payload["branch"] = request.branch
        payload.update(request.extra_params)

        raw = self._post_json(self.AVAILABILITY, payload)
        raw = raw or {}
        data = PropertyAvailabilityResponse(
            summary=raw.get("summary", []),
            details=raw.get("details", []),
            garages=raw.get("garages", []),
        )
        return APIResponsePayload(
            status="ok",
            data={
                "summary": data.summary,
                "details": data.details,
                "garages": data.garages,
            },
            endpoint=self.AVAILABILITY,
            raw_response=raw,
        )

    def _unsold(self, request: APIRequest) -> APIResponsePayload:
        payload: Dict[str, Any] = {"ocode": self.config.org_code}
        if request.shortname:
            payload["shortname"] = request.shortname
        if request.branch:
            payload["branch"] = request.branch
        if request.property_type:
            payload["ptype"] = request.property_type
        if request.property_name:
            payload["pname"] = request.property_name
        payload.update(request.extra_params)

        raw = self._post_json(self.UNSOLD, payload)
        raw = raw or []
        data = UnsoldPropertiesResponse(properties=raw, count=len(raw))
        return APIResponsePayload(
            status="ok",
            data={"properties": data.properties, "count": data.count},
            endpoint=self.UNSOLD,
            raw_response=raw,
        )

    # HTTP helpers -----------------------------------------------------

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Any:
        url = f"{self.config.base_url}{path}"
        try:
            response = self.session.post(url, json=payload, timeout=self.config.timeout)
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()
        except requests.HTTPError as exc:  # pragma: no cover - depends on network
            LOGGER.error("eBuilder API error: status=%s body=%s", exc.response.status_code, exc.response.text)
            raise
        except requests.RequestException as exc:  # pragma: no cover - depends on network
            LOGGER.error("eBuilder network error: %s", exc)
            raise


def build_ebuilder_client(config: Optional[EbuilderClientConfig] = None) -> EbuilderClient:
    return EbuilderClient(config=config)
