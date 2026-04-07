from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedBlock:
    block_type: str
    text: str | None
    markdown: str | None
    page_number: int | None
    order_index: int
    heading_level: int | None = None
    heading_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedDocument:
    file_name: str
    markdown_full: str | None
    text_full: str | None
    blocks: list[NormalizedBlock]
    raw_items: dict | None = None