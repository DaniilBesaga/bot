from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class Block:
    doc_id: str
    block_id: str
    company_id: Optional[str]
    page_number: int
    block_type: str
    raw_text: str
    bbox: tuple[float, float, float, float]
    position_index: int

    normalized_text: str = ""
    fingerprint_text: str = ""

    local_features: dict[str, Any] = field(default_factory=dict)
    global_features: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)