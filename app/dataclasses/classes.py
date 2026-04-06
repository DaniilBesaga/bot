from dataclasses import dataclass, field
from typing import Any

@dataclass
class Primitive:
    kind: str
    bbox: tuple[float, float, float, float]
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class LayoutRegion:
    kind: str
    bbox: tuple[float, float, float, float]
    members: list[Primitive] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

@dataclass
class ContentBlock:
    kind: str
    role: str
    bbox: tuple[float, float, float, float]
    text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)