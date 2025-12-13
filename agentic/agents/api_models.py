"""Typed request/response models for the Property API agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional


class APIIntent(Enum):
    """Kind of API call the agent can perform."""

    BOOKING_STATUS = auto()
    PRICE_LOOKUP = auto()
    INVENTORY = auto()
    UNKNOWN = auto()


@dataclass
class APIRequest:
    """Normalized API call built from the user query."""

    intent: APIIntent
    property_name: Optional[str] = None
    tower_id: Optional[str] = None
    user_query: str = ""
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIResponsePayload:
    """Data returned by the downstream service."""

    status: str
    data: Dict[str, Any]


@dataclass
class APIResponse:
    """Structured agent response."""

    intent: APIIntent
    payload: APIResponsePayload
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = ["APIIntent", "APIRequest", "APIResponse", "APIResponsePayload"]
