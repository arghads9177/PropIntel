"""Typed request/response models for the Property API agent.

This module defines intents, request/response schemas for eBuilder APIs:
- Project metadata (branch, status, timelines)
- Property availability (booked/available counts per tower/floor)
- Unsold properties (full details with rate/amount)

Query patterns mapped to API agent:
- Inventory: "How many flats available in X?", "Which project has most garages?"
- Price/Rate: "What is the rate of shop in Y?", "Price per sqft in Z?"
- Availability by city: "Available flats in Asansol/Bandel?"
- Booking status: "How many units sold in project X?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class APIIntent(Enum):
    """Kind of API call the agent can perform."""

    # Project-level queries
    PROJECT_METADATA = auto()  # Basic project info (status, branch, timelines)
    
    # Inventory & availability queries
    AVAILABILITY_BY_PROJECT = auto()  # Count of available/booked units in specific project
    AVAILABILITY_BY_CITY = auto()  # Available properties filtered by branch/city
    AVAILABILITY_SUMMARY = auto()  # Cross-project summary (which has most available)
    
    # Price & rate queries
    PRICE_LOOKUP = auto()  # Rate per unit, total amount for specific property
    PRICE_COMPARISON = auto()  # Compare rates across projects
    
    # Booking queries
    BOOKING_STATUS = auto()  # Booked vs total for project/tower
    UNSOLD_PROPERTIES = auto()  # Detailed list of unsold units with rates
    
    # Fallback
    UNKNOWN = auto()


@dataclass
class APIRequest:
    """Normalized API call built from the user query."""

    intent: APIIntent
    user_query: str = ""
    
    # Query filters
    shortname: Optional[str] = None  # Project shortname
    branch: Optional[str] = None  # City/branch filter (Asansol, Bandel)
    tower_name: Optional[str] = None  # Tower identifier
    property_type: Optional[str] = None  # Flat, Garage, Shop
    property_name: Optional[str] = None  # Specific property like TYPE A, 4A
    
    # Additional context
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectSearchResponse:
    """Response from /project/search endpoint."""
    
    projects: List[Dict[str, Any]]
    count: int = 0


@dataclass
class PropertyAvailabilityResponse:
    """Response from /towerproperty/availablePropertyForWebSite."""
    
    summary: List[Dict[str, Any]] = field(default_factory=list)  # Per property type totals
    details: List[Dict[str, Any]] = field(default_factory=list)  # Floor-level breakdown
    garages: List[Dict[str, Any]] = field(default_factory=list)  # Garage/parking info


@dataclass
class UnsoldPropertiesResponse:
    """Response from /towerproperty/unsoldPropertiesOfProject."""
    
    properties: List[Dict[str, Any]]
    count: int = 0


@dataclass
class APIResponsePayload:
    """Data returned by the downstream service."""

    status: str
    data: Dict[str, Any]
    endpoint: Optional[str] = None  # Which API was called
    raw_response: Optional[Any] = None  # Original response for debugging


@dataclass
class APIResponse:
    """Structured agent response."""

    intent: APIIntent
    payload: APIResponsePayload
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "APIIntent",
    "APIRequest",
    "APIResponse",
    "APIResponsePayload",
    "ProjectSearchResponse",
    "PropertyAvailabilityResponse",
    "UnsoldPropertiesResponse",
    "infer_api_intent",
]


def infer_api_intent(query: str) -> APIIntent:
    """Map free-form text to an API intent using lightweight heuristics."""
    lowered = (query or "").lower()

    # Price/rate queries
    if any(term in lowered for term in ("price", "cost", "rate", "amount", "per sqft", "per sq")):
        if "compar" in lowered:
            return APIIntent.PRICE_COMPARISON
        return APIIntent.PRICE_LOOKUP

    # Availability/inventory queries
    if any(term in lowered for term in ("available", "unsold", "vacant", "inventory")):
        if any(city in lowered for city in ("asansol", "bandel", "city", "branch")):
            return APIIntent.AVAILABILITY_BY_CITY
        if any(word in lowered for word in ("which", "most", "maximum", "highest", "compare")):
            return APIIntent.AVAILABILITY_SUMMARY
        return APIIntent.AVAILABILITY_BY_PROJECT

    # Booking/sold queries
    if any(term in lowered for term in ("book", "booking", "sold", "booked", "units sold")):
        return APIIntent.BOOKING_STATUS

    # Property count queries
    if any(term in lowered for term in ("how many", "count", "number of")):
        if any(term in lowered for term in ("flat", "garage", "shop", "unit")):
            return APIIntent.AVAILABILITY_BY_PROJECT

    # Project info queries
    if any(term in lowered for term in ("project", "status", "branch", "company", "tower")):
        if "status" in lowered or "detail" in lowered:
            return APIIntent.PROJECT_METADATA

    return APIIntent.UNKNOWN
