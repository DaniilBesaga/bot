from sqlalchemy.orm import Session

from app.db.models import DocumentSection


class SectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        if not sections:
            return []

        self.db.add_all(sections)
        self.db.commit()

        for section in sections:
            self.db.refresh(section)

        return sections