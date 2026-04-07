import datetime
import uuid

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import JSON, UUID, Boolean, Column, DateTime, Float, Index, String, Text, Integer, ForeignKey, UniqueConstraint
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID, JSONB

from datetime import timezone

class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="local_file")
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    parser_name: Mapped[str] = mapped_column(String(50), nullable=False, default="llamaparse")
    parser_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    markdown_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    sections = relationship("DocumentSection", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_id_chunk_index", "document_id", "chunk_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("document_sections.id", ondelete="SET NULL"), nullable=True)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")

    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_path: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    document = relationship("Document", back_populates="chunks")
    section = relationship("DocumentSection", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan", uselist=False)

    reranker_examples: Mapped[list["RerankerExample"]] = relationship(
        "RerankerExample",
        back_populates="chunk",
    )

    reranker_predictions: Mapped[list["RerankerPrediction"]] = relationship(
        "RerankerPrediction",
        back_populates="chunk",
    )

class DocumentSection(Base):
    __tablename__ = "document_sections"
    __table_args__ = (
        Index("ix_document_sections_document_id_order_index", "document_id", "order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    section_type: Mapped[str] = mapped_column(String(50), nullable=False)  
    # heading / paragraph / list / table / code / quote / page_break

    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    heading_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    heading_path: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document = relationship("Document", back_populates="sections")
    chunks = relationship("DocumentChunk", back_populates="section")

from pgvector.sqlalchemy import Vector


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)

    chunk = relationship("DocumentChunk", back_populates="embedding")

import uuid
import datetime

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TrainingRun(Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        Index("ix_training_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    task_name: Mapped[str] = mapped_column(String(100), nullable=False, default="reranker")
    base_model: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    train_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    val_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    test_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    train_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    val_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    val_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    models: Mapped[list["RerankerModel"]] = relationship(
        "RerankerModel",
        back_populates="training_run",
        cascade="all, delete-orphan",
    )


class RerankerModel(Base):
    __tablename__ = "reranker_models"
    __table_args__ = (
        UniqueConstraint("version", name="uq_reranker_model_version"),
        Index("ix_reranker_models_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    training_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    version: Mapped[str] = mapped_column(String(100), nullable=False)
    base_model: Mapped[str] = mapped_column(String(255), nullable=False)

    # Если это JSON-конфиг архитектуры, лучше JSONB
    architecture: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    model_dir: Mapped[str] = mapped_column(String(1000), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    training_run: Mapped["TrainingRun | None"] = relationship(
        "TrainingRun",
        back_populates="models",
    )

    predictions: Mapped[list["RerankerPrediction"]] = relationship(
        "RerankerPrediction",
        back_populates="model",
        cascade="all, delete-orphan",
    )


class RerankerExample(Base):
    __tablename__ = "reranker_examples"
    __table_args__ = (
        Index("ix_reranker_examples_split", "split"),
        Index("ix_reranker_examples_chunk_id", "chunk_id"),
        Index("ix_reranker_examples_source", "source"),
        Index("ix_reranker_examples_label", "label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    question: Mapped[str] = mapped_column(Text, nullable=False)

    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    chunk_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    label: Mapped[bool] = mapped_column(Boolean, nullable=False)

    split: Mapped[str] = mapped_column(String(20), nullable=False)  # train / val / test
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # manual / synthetic / clicked

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    chunk: Mapped["DocumentChunk | None"] = relationship(
        "DocumentChunk",
        back_populates="reranker_examples",
    )


class RerankerPrediction(Base):
    __tablename__ = "reranker_predictions"
    __table_args__ = (
        Index("ix_reranker_predictions_chunk_id", "chunk_id"),
        Index("ix_reranker_predictions_model_id", "model_id"),
        Index("ix_reranker_predictions_is_test", "is_test"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reranker_models.id", ondelete="SET NULL"),
        nullable=True,
    )

    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)

    # Я бы тут хранил именно score, а не только bool
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Если хочешь оставить бинарное решение
    label: Mapped[bool] = mapped_column(Boolean, nullable=False)

    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    model: Mapped["RerankerModel | None"] = relationship(
        "RerankerModel",
        back_populates="predictions",
    )

    chunk: Mapped["DocumentChunk | None"] = relationship(
        "DocumentChunk",
        back_populates="reranker_predictions",
    )