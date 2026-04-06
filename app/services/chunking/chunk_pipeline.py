from sqlalchemy.orm import Session
from app.db.repositories import ChunkRepository
from app.services.chunking.block_loader import BlockLoader
from app.services.chunking.chunk_builder import ChunkBuilder
from app.services.section.section_builder import SectionBuilder


class ChunkPipeline:
    @classmethod
    def build_chunks_for_document(cls, session: Session, doc_id: str, max_words: int = 220) -> list[dict]:
        blocks = BlockLoader.load_doc_blocks(session, doc_id)
        sections = SectionBuilder.build_sections(blocks)

        chunks: list[dict] = []
        chunk_counter = 0

        for section in sections:
            heading = section["heading"]
            groups = ChunkBuilder.split_section_into_chunk_groups(section, max_words=max_words)

            for group in groups:
                group = ChunkBuilder.ensure_heading_in_group(heading, group)
                chunk = ChunkBuilder.build_chunk_from_blocks(
                    doc_id=doc_id,
                    chunk_index=chunk_counter,
                    blocks=group,
                    heading=heading,
                )

                if chunk["clean_text"].strip():
                    chunks.append(chunk)
                    chunk_counter += 1

        return chunks

    @classmethod
    def build_and_save_chunks_for_document(cls, session: Session, doc_id: str, max_words: int = 220) -> list[dict]:
        chunks = cls.build_chunks_for_document(session, doc_id, max_words=max_words)
        ChunkRepository.save_chunks(session, chunks)
        return chunks