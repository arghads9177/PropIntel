"""API agent node for live eBuilder property data.

The agent decides which eBuilder endpoint to call based on the inferred intent and
translates raw JSON responses into conversational summaries (inventory, price,
booking, and project metadata).

See EBUILDER_API_SPEC.md for endpoint documentation.
"""

from __future__ import annotations

import logging
import random
import time
from collections import defaultdict
from typing import Any, Dict, Optional, Protocol, Tuple

from agentic.agents.api_client import build_ebuilder_client
from agentic.agents.api_models import (
    APIIntent,
    APIRequest,
    APIResponse,
    APIResponsePayload,
    infer_api_intent,
)
from agentic.agents.base import AgentConfig, AgentNode, _prepare_agent_response
from agentic.workflow.state import AgentState

LOGGER = logging.getLogger(__name__)

# Common project aliases mapped to likely API shortnames. Helps override stale
# memory when users pivot to a different project mid-conversation.
PROJECT_ALIASES = {
    "alakananda apartment": "alakananda",
    "alakananda phase 2": "alakananda",
    "alakananda": "alakananda",
    "nilachal apartment": "nilachal",
    "nilachal": "nilachal",
    "shivalaya residency": "shivalaya",
    "shivalaya": "shivalaya",
    "kabi tirtha": "kabi tirtha",
    "kabitirtha": "kabi tirtha",
    "rajdeep apartment": "rajdeep",
    "geetanjali enclave": "geetanjali",
    "olivia enclave": "olivia",
    "elina tower": "elina",
    "omkar apartment": "omkar",
    "ashirwad apartment": "ashirwad",
    "aastha apartment": "aastha",
}


class PropertyAPIClient(Protocol):
    """Protocol implemented by real or stub API clients."""

    def fetch(self, request: APIRequest) -> APIResponse:  # pragma: no cover - interface only
        ...


class MockPropertyAPIClient:
    """In-memory stub that mimics the eBuilder API responses."""

    PROJECTS = [
        {
            "shortname": "SHIVALAYA",
            "fullname": "Shivalaya Residency",
            "branch": "ASANSOL",
            "status": "Running",
            "towers": 2,
            "projectfor": "Land",
            "approxcompletedate": "2026-09-30T00:00:00.000Z",
        },
        {
            "shortname": "BASU TOWER",
            "fullname": "Alakananda Apartment",
            "branch": "BANDEL",
            "status": "Running",
            "towers": 2,
            "projectfor": "Residential",
            "approxcompletedate": "2027-03-31T00:00:00.000Z",
        },
        {
            "shortname": "NILACHAL",
            "fullname": "Nilachal Apartment",
            "branch": "ASANSOL",
            "status": "Running",
            "towers": 1,
            "projectfor": "Residential",
            "approxcompletedate": "2026-12-31T00:00:00.000Z",
        },
        {
            "shortname": "KABI TIRTHA",
            "fullname": "Kabi Tirtha",
            "branch": "ASANSOL",
            "status": "Running",
            "towers": 4,
            "projectfor": "Residential",
            "approxcompletedate": "2027-06-30T00:00:00.000Z",
        },
    ]

    AVAILABILITY = {
        "SHIVALAYA": {
            "summary": [
                {"pname": "TYPE A", "total": 10, "booked": 8, "available": 2},
                {"pname": "TYPE B", "total": 10, "booked": 7, "available": 3},
            ],
            "details": [],
            "garages": [
                {"pname": "Covered Parking", "total": 5, "booked": 4, "available": 1},
            ],
        },
        "BASU TOWER": {
            "summary": [
                {"pname": "WING G", "total": 8, "booked": 5, "available": 3},
            ],
            "details": [],
            "garages": [
                {"pname": "Garage", "total": 3, "booked": 0, "available": 3},
            ],
        },
    }

    UNSOLD = [
        {
            "shortname": "SHIVALAYA",
            "branch": "ASANSOL",
            "tname": "Shivalaya",
            "ptype": "Flat",
            "pname": "4A",
            "floor": 4,
            "noofunit": 1,
            "area": 885,
            "builduparea": 708,
            "rate": 2950,
            "amount": 2610750,
        },
        {
            "shortname": "BASU TOWER",
            "branch": "BANDEL",
            "tname": "ALAKANANDA",
            "ptype": "Garage",
            "pname": "G-05",
            "floor": 0,
            "noofunit": 2,
            "area": 120,
            "rate": 180000,
            "amount": 360000,
        },
        {
            "shortname": "BASU TOWER",
            "branch": "BANDEL",
            "tname": "ALAKANANDA",
            "ptype": "Flat",
            "pname": "G-5",
            "floor": 0,
            "noofunit": 1,
            "area": 915,
            "builduparea": 732,
            "rate": 2500,
            "amount": 2287500,
        },
        {
            "shortname": "ALAKANANDA",
            "branch": "BANDEL",
            "tname": "ALAKANANDA",
            "ptype": "Flat",
            "pname": "B-2",
            "floor": 2,
            "noofunit": 2,
            "area": 980,
            "builduparea": 805,
            "rate": 3125,
            "amount": 3062500,
        },
        {
            "shortname": "ALAKANANDA",
            "branch": "BANDEL",
            "tname": "ALAKANANDA",
            "ptype": "Garage",
            "pname": "G-01",
            "floor": 0,
            "noofunit": 1,
            "area": 120,
            "rate": 180000,
            "amount": 180000,
        },
        {
            "shortname": "ALAKANANDA",
            "branch": "BANDEL",
            "tname": "ALAKANANDA",
            "ptype": "Garage",
            "pname": "G-03",
            "floor": 0,
            "noofunit": 1,
            "area": 120,
            "rate": 180000,
            "amount": 180000,
        },
        {
            "shortname": "ALAKANANDA",
            "branch": "BANDEL",
            "tname": "ALAKANANDA",
            "ptype": "Garage",
            "pname": "G-07",
            "floor": 0,
            "noofunit": 1,
            "area": 120,
            "rate": 180000,
            "amount": 180000,
        },
        {
            "shortname": "NILACHAL",
            "branch": "ASANSOL",
            "tname": "NILACHAL",
            "ptype": "Garage",
            "pname": "PARK-01",
            "floor": 0,
            "noofunit": 1,
            "area": 120,
            "rate": 185000,
            "amount": 185000,
        },
    ]

    def fetch(self, request: APIRequest) -> APIResponse:
        start = time.perf_counter()
        time.sleep(0.02)  # Simulate latency
        latency_ms = int((time.perf_counter() - start) * 1000)

        if request.intent == APIIntent.PROJECT_METADATA:
            projects = self._filter_projects(request)
            payload = APIResponsePayload(
                status="ok",
                data={"projects": projects, "count": len(projects)},
                endpoint="/project/search",
            )
        elif request.intent in {APIIntent.AVAILABILITY_BY_PROJECT, APIIntent.BOOKING_STATUS}:
            key = (request.shortname or "DEFAULT").upper()
            availability = self.AVAILABILITY.get(key)
            if availability is None:
                availability = {"summary": [], "details": [], "garages": []}
            payload = APIResponsePayload(
                status="ok",
                data=availability,
                endpoint="/towerproperty/availablePropertyForWebSite",
            )
        else:
            properties = self._filter_unsold(request)
            payload = APIResponsePayload(
                status="ok",
                data={"properties": properties, "count": len(properties)},
                endpoint="/towerproperty/unsoldPropertiesOfProject",
            )

        return APIResponse(
            intent=request.intent,
            payload=payload,
            metadata={
                "stub": True,
                "trace_id": f"stub-{random.randint(1000, 9999)}",
                "latency_ms": latency_ms,
            },
        )

    def _filter_projects(self, request: APIRequest) -> list[Dict[str, Any]]:
        projects = self.PROJECTS
        if request.shortname:
            # Support both exact shortname match and partial fullname match
            search_term = request.shortname.lower()
            projects = [
                p for p in projects 
                if p["shortname"].lower() == search_term or search_term in p.get("fullname", "").lower()
            ]
        if request.branch:
            projects = [p for p in projects if p.get("branch") == request.branch]
        return projects

    def _filter_unsold(self, request: APIRequest) -> list[Dict[str, Any]]:
        records = self.UNSOLD
        if request.shortname:
            records = [r for r in records if r.get("shortname", "").lower() == request.shortname.lower()]
        if request.branch:
            records = [r for r in records if r.get("branch") == request.branch]
        if request.property_type:
            records = [r for r in records if r.get("ptype") == request.property_type]
        if request.property_name:
            records = [r for r in records if r.get("pname", "").lower() == request.property_name.lower()]
        return records


class APIAgent(AgentNode):
    """LangGraph node that delegates to a property API client."""

    def __init__(self, client: PropertyAPIClient | None = None, *, use_live_client: bool = True) -> None:
        self.client = client or self._build_default_client(use_live_client)
        self.config = AgentConfig(
            name="api_agent",
            description="Fetches live inventory, pricing, and booking data via eBuilder APIs",
        )

    def __call__(self, state: AgentState, **kwargs: Any) -> AgentState:
        request = self._build_request(state, **kwargs)
        
        # CRITICAL: Resolve project shortname first if user provided a name
        if request.shortname and request.intent != APIIntent.PROJECT_METADATA:
            request = self._resolve_project_shortname(request)
        
        response = self.client.fetch(request)
        answer, answer_meta = self._format_answer(response, request)

        metadata = {
            "agent": self.config.name,
            "intent": response.intent.name,
            **response.metadata,
            **answer_meta,
        }

        state.api_response = _prepare_agent_response(answer, metadata=metadata)
        self._update_memory(state, request)
        return state

    @staticmethod
    def _build_default_client(use_live_client: bool) -> PropertyAPIClient:
        if not use_live_client:
            return MockPropertyAPIClient()
        try:
            return build_ebuilder_client()
        except Exception as exc:  # pragma: no cover - depends on env
            LOGGER.warning("Falling back to mock API client: %s", exc)
            return MockPropertyAPIClient()

    def _build_request(self, state: AgentState, **overrides: Any) -> APIRequest:
        """Build APIRequest from state and overrides.
        
        Extracts filters from query and memory context.
        """
        query = state.query or overrides.get("query", "")
        intent = overrides.get("intent") or infer_api_intent(query)
        
        # Extract project/property context
        shortname = overrides.get("shortname")
        if not shortname:
            shortname = self._extract_project_from_query(query)
        if not shortname:
            shortname = self._extract_project(state)
        branch = overrides.get("branch") or self._extract_branch(query)
        property_type = overrides.get("property_type") or self._extract_property_type(query)
        tower_name = overrides.get("tower_name")
        property_name = overrides.get("property_name")
        
        return APIRequest(
            intent=intent,
            user_query=query,
            shortname=shortname,
            branch=branch,
            tower_name=tower_name,
            property_type=property_type,
            property_name=property_name,
            extra_params={k: v for k, v in overrides.items() 
                         if k not in {"intent", "shortname", "branch", "tower_name", "property_type", "property_name"}},
        )
    
    @staticmethod
    def _extract_branch(query: str) -> Optional[str]:
        """Extract city/branch from query."""
        lower = query.lower()
        if "asansol" in lower:
            return "ASANSOL"
        if "bandel" in lower:
            return "BANDEL"
        return None
    
    @staticmethod
    def _extract_property_type(query: str) -> Optional[str]:
        """Extract property type from query."""
        lower = query.lower()
        if "flat" in lower:
            return "Flat"
        if "garage" in lower or "parking" in lower:
            return "Garage"
        if "shop" in lower:
            return "Shop"
        return None

    @staticmethod
    def _extract_project(state: AgentState) -> Optional[str]:
        """Extract project shortname from memory or context."""
        facts = (state.memory or {}).get("facts", {})
        return facts.get("last_project")

    @staticmethod
    def _extract_project_from_query(query: str) -> Optional[str]:
        """Match known project aliases directly from the query text."""
        lowered = (query or "").lower()
        if not lowered:
            return None

        for alias, shortname in sorted(PROJECT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if alias in lowered:
                return shortname
        return None

    def _resolve_project_shortname(self, request: APIRequest) -> APIRequest:
        """
        Resolve project shortname by calling PROJECT_METADATA API.
        
        This ensures we have the correct API shortname even if user provided
        a partial name, fullname, or alias. Critical for data accuracy.
        """
        if not request.shortname:
            return request
        
        # Call project search to find the actual shortname
        search_request = APIRequest(
            intent=APIIntent.PROJECT_METADATA,
            user_query=request.user_query,
            shortname=request.shortname,
            branch=request.branch,
        )
        
        try:
            search_response = self.client.fetch(search_request)
            projects = (search_response.payload.data or {}).get("projects", [])
            
            if projects:
                # Use the first match's actual shortname
                actual_shortname = projects[0].get("shortname")
                if actual_shortname and actual_shortname != request.shortname:
                    LOGGER.info(f"Resolved '{request.shortname}' → '{actual_shortname}'")
                    # Create new request with resolved shortname
                    return APIRequest(
                        intent=request.intent,
                        user_query=request.user_query,
                        shortname=actual_shortname,
                        branch=request.branch,
                        tower_name=request.tower_name,
                        property_type=request.property_type,
                        property_name=request.property_name,
                        extra_params=request.extra_params,
                    )
        except Exception as exc:
            LOGGER.warning(f"Project resolution failed for '{request.shortname}': {exc}")
        
        return request

    def _format_answer(self, response: APIResponse, request: APIRequest) -> Tuple[str, Dict[str, Any]]:
        payload = response.payload
        base_meta: Dict[str, Any] = {
            "status": payload.status,
            "endpoint": payload.endpoint,
        }

        if payload.status != "ok":
            message = "I couldn't retrieve live data right now. Please try again in a moment."
            return message, base_meta

        data = payload.data or {}
        formatter_map = {
            APIIntent.PROJECT_METADATA: self._summarize_project_metadata,
            APIIntent.AVAILABILITY_BY_PROJECT: self._summarize_project_availability,
            APIIntent.BOOKING_STATUS: self._summarize_project_availability,
            APIIntent.AVAILABILITY_BY_CITY: self._summarize_city_availability,
            APIIntent.AVAILABILITY_SUMMARY: self._summarize_summary_availability,
            APIIntent.PRICE_LOOKUP: self._summarize_price_lookup,
            APIIntent.PRICE_COMPARISON: self._summarize_price_comparison,
            APIIntent.UNSOLD_PROPERTIES: self._summarize_unsold_list,
        }

        formatter = formatter_map.get(response.intent)
        if not formatter:
            message = "I don't have a dedicated live data source for that question yet."
            return message, base_meta

        answer, meta = formatter(data, request, response.intent)
        meta = {**base_meta, **meta}
        return answer, meta

    def _summarize_project_metadata(
        self, data: Dict[str, Any], request: APIRequest, _: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        projects = data.get("projects") or []
        if not projects:
            return "I couldn't find live metadata for that project.", {"project_count": 0}

        project = self._select_project_record(projects, request.shortname)
        name = project.get("fullname") or project.get("shortname") or "This project"
        shortname = project.get("shortname", "")
        branch = project.get("branch") or "an unspecified location"
        status = (project.get("status") or "Unknown").lower()
        towers = project.get("towers")
        project_for = project.get("projectfor")
        eta = self._format_date(project.get("approxcompletedate") or project.get("completedate"))

        lines = [
            f"{name} ({shortname}) in {branch} is currently {status}.",
        ]
        if towers:
            lines.append(f"It comprises {towers} tower(s).")
        if project_for:
            lines.append(f"Project type: {project_for}.")
        if eta:
            lines.append(f"Estimated completion: {eta}.")

        return "\n".join(lines), {
            "project_count": len(projects),
            "selected_project": shortname,
        }

    def _summarize_project_availability(
        self, data: Dict[str, Any], request: APIRequest, intent: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        summary = data.get("summary") or []
        if not summary:
            fallback = self._fallback_to_unsold(request)
            if fallback:
                return fallback
            project = request.shortname or "the requested project"
            return f"I couldn't find live availability data for {project}.", {"summary_count": 0}

        total_units = sum(item.get("total", 0) for item in summary)
        booked_units = sum(item.get("booked", 0) for item in summary)
        available_units = sum(item.get("available", 0) for item in summary)
        property_label = self._pluralize(request.property_type or "unit")
        project = request.shortname or "this project"

        lines = [
            f"{project} currently has {available_units} {property_label} available out of {total_units} total.",
        ]
        if intent == APIIntent.BOOKING_STATUS and total_units:
            percent = (booked_units / total_units) * 100 if total_units else 0
            lines.append(f"{booked_units} have been booked ({percent:.0f}% of inventory).")

        top_available = [item for item in summary if item.get("available", 0) > 0]
        if top_available:
            top_available.sort(key=lambda item: item.get("available", 0), reverse=True)
            highlights = ", ".join(
                f"{item['pname']} ({item['available']} available)" for item in top_available[:3]
            )
            lines.append(f"Available right now: {highlights}.")
        else:
            lines.append("All listed units are currently booked.")

        garages = data.get("garages") or []
        garage_available = sum(item.get("available", 0) for item in garages)
        if garage_available:
            lines.append(f"Parking availability: {garage_available} garage/parking slots free.")

        return "\n".join(lines), {
            "total_units": total_units,
            "available_units": available_units,
            "booked_units": booked_units,
            "garage_available": garage_available,
        }

    def _fallback_to_unsold(self, request: APIRequest) -> Optional[Tuple[str, Dict[str, Any]]]:
        if not request.shortname and not request.branch:
            return None

        fallback_request = APIRequest(
            intent=APIIntent.UNSOLD_PROPERTIES,
            user_query=request.user_query,
            shortname=request.shortname,
            branch=request.branch,
            tower_name=request.tower_name,
            property_type=request.property_type,
            property_name=request.property_name,
            extra_params=request.extra_params.copy(),
        )

        try:
            response = self.client.fetch(fallback_request)
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.debug("Unsold fallback failed: %s", exc)
            return None

        payload = response.payload
        properties = (payload.data or {}).get("properties") or []
        if payload.status != "ok" or not properties:
            return None

        answer, meta = self._summarize_unsold_list(payload.data, fallback_request, APIIntent.UNSOLD_PROPERTIES)
        meta["fallback_source"] = "unsold_properties"
        meta["original_intent"] = request.intent.name
        return answer, meta

    def _summarize_city_availability(
        self, data: Dict[str, Any], request: APIRequest, _: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        properties = data.get("properties") or []
        branch_label = (request.branch or "the selected area").title()
        if not properties:
            return f"I couldn't find unsold units in {branch_label} right now.", {"property_count": 0}

        project_totals: Dict[str, int] = defaultdict(int)
        type_totals: Dict[str, int] = defaultdict(int)
        for record in properties:
            units = record.get("noofunit") or 1
            project_totals[record.get("shortname", "Unknown")] += units
            type_totals[record.get("ptype", "Unit")] += units

        total_units = sum(project_totals.values())
        lines = [
            f"In {branch_label}, there are {total_units} unsold unit(s) across {len(project_totals)} projects.",
        ]

        top_projects = sorted(project_totals.items(), key=lambda item: item[1], reverse=True)[:3]
        lines.append(
            "Top availability: "
            + ", ".join(f"{name} ({count})" for name, count in top_projects)
            + "."
        )

        type_breakdown = ", ".join(
            f"{ptype}: {count}" for ptype, count in sorted(type_totals.items(), reverse=True)
        )
        lines.append(f"By property type: {type_breakdown}.")

        return "\n".join(lines), {
            "property_count": len(properties),
            "total_units": total_units,
            "project_coverage": len(project_totals),
        }

    def _summarize_summary_availability(
        self, data: Dict[str, Any], request: APIRequest, _: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        properties = data.get("properties") or []
        if not properties:
            return "I couldn't find any unsold units to compare right now.", {"property_count": 0}

        project_totals: Dict[str, int] = defaultdict(int)
        for record in properties:
            project_totals[record.get("shortname", "Unknown")] += record.get("noofunit", 1)

        top_project, units = max(project_totals.items(), key=lambda item: item[1])
        lines = [
            f"{top_project} currently has the highest unsold inventory with {units} unit(s).",
        ]

        secondaries = sorted(project_totals.items(), key=lambda item: item[1], reverse=True)[1:3]
        if secondaries:
            lines.append(
                "Other notable projects: "
                + ", ".join(f"{name} ({count})" for name, count in secondaries)
                + "."
            )

        if request.property_type:
            lines.append(f"Focus type: {request.property_type}.")

        return "\n".join(lines), {
            "property_count": len(properties),
            "top_project": top_project,
            "top_units": units,
        }

    def _summarize_price_lookup(
        self, data: Dict[str, Any], request: APIRequest, _: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        properties = data.get("properties") or []
        if not properties:
            return "I couldn't find pricing data for that query.", {"property_count": 0}

        selected = self._select_property(properties, request)
        rate = selected.get("rate")
        amount = selected.get("amount")
        area = selected.get("area")
        pname = selected.get("pname")
        project = selected.get("shortname")
        ptype = selected.get("ptype")

        message = (
            f"{ptype} {pname} in {project} is listed at {self._format_money(rate)} per sq.ft"
            f" with a total price of {self._format_money(amount)} for {area} sq.ft."
        )

        return message, {
            "property_count": len(properties),
            "selected_property": pname,
            "rate": rate,
            "amount": amount,
        }

    def _summarize_price_comparison(
        self, data: Dict[str, Any], request: APIRequest, _: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        properties = data.get("properties") or []
        if not properties:
            return "No pricing data is available for comparison yet.", {"property_count": 0}

        sorted_props = sorted(properties, key=lambda record: record.get("rate", 0), reverse=True)[:3]
        lines = ["Top quoted rates:"]
        for record in sorted_props:
            lines.append(
                f"- {record.get('shortname')} {record.get('pname')} ({record.get('ptype')}): "
                f"{self._format_money(record.get('rate'))} / sq.ft"
            )

        return "\n".join(lines), {
            "property_count": len(properties),
            "compared_projects": len(sorted_props),
        }

    def _summarize_unsold_list(
        self, data: Dict[str, Any], request: APIRequest, _: APIIntent
    ) -> Tuple[str, Dict[str, Any]]:
        properties = data.get("properties") or []
        if not properties:
            return "Great news—there are no unsold units matching that filter right now.", {"property_count": 0}

        lines = ["Unsold units currently available:"]
        for record in properties[:5]:
            lines.append(
                f"- {record.get('shortname')} {record.get('pname')} ({record.get('ptype')}) "
                f"at {self._format_money(record.get('rate'))}/sq.ft; total {self._format_money(record.get('amount'))}."
            )

        return "\n".join(lines), {
            "property_count": len(properties),
            "reported_projects": len({r.get('shortname') for r in properties}),
        }

    def _select_project_record(self, projects: list[Dict[str, Any]], shortname: Optional[str]) -> Dict[str, Any]:
        if shortname:
            lowered = shortname.lower()
            for project in projects:
                if project.get("shortname", "").lower() == lowered:
                    return project
        return projects[0]

    def _select_property(self, properties: list[Dict[str, Any]], request: APIRequest) -> Dict[str, Any]:
        if request.property_name:
            lowered = request.property_name.lower()
            for record in properties:
                if record.get("pname", "").lower() == lowered:
                    return record
        if request.shortname:
            lowered = request.shortname.lower()
            for record in properties:
                if record.get("shortname", "").lower() == lowered:
                    return record
        return properties[0]

    def _update_memory(self, state: AgentState, request: APIRequest) -> None:
        if not request.shortname:
            return
        memory = state.memory or {}
        facts = memory.setdefault("facts", {})
        facts["last_project"] = request.shortname
        state.memory = memory

    @staticmethod
    def _pluralize(noun: str) -> str:
        noun = noun.strip()
        if noun.lower().endswith("s"):
            return noun
        return f"{noun}s"

    @staticmethod
    def _format_date(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return value[:10]

    @staticmethod
    def _format_money(value: Any) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value) if value is not None else "N/A"
        return f"₹{number:,.0f}"


def build_api_agent(client: PropertyAPIClient | None = None, *, use_live_client: bool = True) -> APIAgent:
    return APIAgent(client=client, use_live_client=use_live_client)
