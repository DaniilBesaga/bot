from sqlalchemy.orm import Session

from app.db.models import Block


class BlockLoader:
    @staticmethod
    def load_doc_blocks(session: Session, doc_id: str) -> list[Block]:
        return (
            session.query(Block)
            .filter(Block.doc_id == doc_id)
            .order_by(Block.page_number.asc(), Block.position_index.asc())
            .all()
        )