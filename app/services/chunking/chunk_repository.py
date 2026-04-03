from sqlalchemy.orm import Session

from app.db.models import Chunk


class ChunkRepository:
    @staticmethod
    def save_chunks(session: Session, chunks: list[dict]) -> None:
        for ch in chunks:
            obj = Chunk(
                chunk_id=ch["chunk_id"],
                doc_id=ch["doc_id"],
                start_page=ch["start_page"],
                end_page=ch["end_page"],
                start_position_index=ch["start_position_index"],
                end_position_index=ch["end_position_index"],
                block_ids=ch["block_ids"],
                chunk_type=ch["chunk_type"],
                raw_text=ch["raw_text"],
                clean_text=ch["clean_text"],
                heading_text=ch["heading_text"],
                heading_fingerprint=ch["heading_fingerprint"],
                avg_contact_score=ch["avg_contact_score"],
                max_contact_score=ch["max_contact_score"],
                avg_boilerplate_score=ch["avg_boilerplate_score"],
                max_boilerplate_score=ch["max_boilerplate_score"],
                avg_content_score=ch["avg_content_score"],
                max_content_score=ch["max_content_score"],
            )
            session.merge(obj)

        session.commit()

    @staticmethod
    def load_chunks_by_doc_id(session: Session, doc_id: str) -> list[Chunk]:
        return (
            session.query(Chunk)
            .filter(Chunk.doc_id == doc_id)
            .order_by(Chunk.start_page.asc(), Chunk.start_position_index.asc())
            .all()
        )