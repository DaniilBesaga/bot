from dataclasses import dataclass, field
from typing import Optional, Any

from sqlalchemy import Column, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Block(Base):
    __tablename__ = "document_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String, unique=True, index=True, nullable=False)
    doc_id = Column(String, index=True, nullable=False)
    page_number = Column(Integer, index=True)
    position_index = Column(Integer)
    
    # Metadata
    kind = Column(String, nullable=False)  # "text_block", "image_block", "table_block"
    role = Column(String, nullable=True)   # From your classify_primitive_blocks logic
    bbox = Column(JSON, nullable=True)     # Stores coordinates [x0, y0, x1, y1]
    
    # Text content (Populated by BlocksPreparation)
    raw_text = Column(Text, nullable=True, default="")
    normalized_text = Column(Text, nullable=True, default="")
    fingerprint_text = Column(Text, nullable=True, default="")