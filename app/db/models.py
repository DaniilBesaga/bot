import datetime
import uuid

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Boolean, DateTime, Float, Index, String, Text, Integer, ForeignKey, UniqueConstraint
from pgvector.sqlalchemy import Vector

from datetime import timezone

class Base(DeclarativeBase):
    pass

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))

    reranker_examples: Mapped[list["RerankerExample"]] = relationship(back_populates="chunk")
    reranker_predictions: Mapped[list["RerankerPrediction"]] = relationship(back_populates="chunk")


class RerankerModel(Base):
    __tablename__ = "reranker_models"
    __table_args__ = (
        UniqueConstraint("version", name="uq_reranker_model_version"),
        Index("ix_reranker_model_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    training_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("training_runs.id", ondelete="SET NULL"), nullable=True
    )

    version: Mapped[str] = mapped_column(String(100), nullable=False)
    base_model: Mapped[str] = mapped_column(String(255), nullable=False)

    architecture: Mapped[str] = mapped_column(Text, nullable=False)

    model_dir: Mapped[str] = mapped_column(String(1000), nullable=False)

    is_active: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    training_run: Mapped["TrainingRun | None"] = relationship(back_populates="models")

class TrainingRun(Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        Index("ix_training_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    task_name: Mapped[str] = mapped_column(String(100), nullable=False, default="reranker")
    base_model: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    train_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    val_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
        back_populates="training_run",
        cascade="all, delete-orphan",
    )


class RerankerExample(Base):
    __tablename__ = "reranker_examples"
    __table_args__ = (
        Index("ix_reranker_examples_split", "split"),
        Index("ix_reranker_examples_chunk_id", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    question: Mapped[str] = mapped_column(Text, nullable=False)

    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    chunk_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    label: Mapped[bool] = mapped_column(Boolean, nullable=False)

    split: Mapped[str] = mapped_column(String(20), nullable=False)  # train/val/test
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # manual/synthetic/clicked

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    chunk: Mapped["DocumentChunk | None"] = relationship(back_populates="reranker_examples")

class RerankerPrediction(Base):
    __tablename__ = "reranker_predictions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)

    label: Mapped[bool] = mapped_column(Boolean, nullable=False)

    test: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    chunk: Mapped["DocumentChunk | None"] = relationship(back_populates="reranker_predictions")