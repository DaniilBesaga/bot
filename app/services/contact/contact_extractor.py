from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+', re.IGNORECASE)
URL_RE = re.compile(r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)', re.IGNORECASE)
PHONE_RE = re.compile(r'(\+?\d[\d\-\.\(\)\/\s]{6,}\d)')
IMAGE_LINE_RE = re.compile(r'!\[.*?\]\(.*?\)')


CONTACT_KEYWORDS = [
    "email", "e-mail", "mail",
    "tel", "telefon", "phone", "mob", "mobile",
    "fax",
    "web", "website", "webpage", "site", "www",
    "address", "adresă", "adresa", "str.", "street", "via", 'strada',
    "contact", "contacts",
]


@dataclass
class ContactBlockCandidate:
    raw_text: str
    normalized_text: str
    score: int


class ContactChunkExtractor:
    @classmethod
    def extract_blocks(cls, text: str) -> list[ContactBlockCandidate]:
        if not text or not text.strip():
            return []

        lines = cls._prepare_lines(text)
        if not lines:
            return []

        candidate_indexes = [i for i, line in enumerate(lines) if cls._is_contact_line(line)]
        if not candidate_indexes:
            return []

        groups = cls._group_neighbor_indexes(candidate_indexes)

        blocks: list[ContactBlockCandidate] = []
        for group in groups:
            block_lines = cls._expand_and_collect(lines, group)
            block_text = "\n".join(block_lines).strip()

            if not block_text:
                continue

            block_score = cls._score_block(block_text)
            if block_score < 2:
                continue

            normalized = cls._normalize_contact_block(block_text)

            blocks.append(
                ContactBlockCandidate(
                    raw_text=block_text,
                    normalized_text=normalized,
                    score=block_score,
                )
            )

        return cls._dedupe_blocks(blocks)

    @classmethod
    def _prepare_lines(cls, text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if IMAGE_LINE_RE.fullmatch(cleaned):
                continue
            lines.append(cleaned)
        return lines

    @classmethod
    def _is_contact_line(cls, line: str) -> bool:
        line_l = line.lower()

        if any(keyword in line_l for keyword in CONTACT_KEYWORDS):
            return True

        if EMAIL_RE.search(line):
            return True

        if URL_RE.search(line):
            return True

        if PHONE_RE.search(line):
            return True

        return False

    @classmethod
    def _group_neighbor_indexes(cls, indexes: list[int]) -> list[list[int]]:
        if not indexes:
            return []

        groups = []
        current = [indexes[0]]

        for idx in indexes[1:]:
            if idx <= current[-1] + 1:
                current.append(idx)
            else:
                groups.append(current)
                current = [idx]

        groups.append(current)
        return groups

    @classmethod
    def _expand_and_collect(cls, lines: list[str], group: list[int]) -> list[str]:
        start = max(0, group[0] - 1)
        end = min(len(lines), group[-1] + 2)

        collected = []
        for i in range(start, end):
            line = lines[i].strip()
            if not line:
                continue

            # отбрасываем явно длинные описательные абзацы
            if len(line) > 350 and not cls._is_contact_line(line):
                continue

            collected.append(line)

        return collected

    @classmethod
    def _score_block(cls, text: str) -> int:
        score = 0

        emails = EMAIL_RE.findall(text)
        urls = URL_RE.findall(text)
        phones = PHONE_RE.findall(text)

        score += len(emails) * 3
        score += len(urls) * 2
        score += len(phones) * 2

        text_l = text.lower()
        for keyword in CONTACT_KEYWORDS:
            if keyword in text_l:
                score += 1

        return score

    @classmethod
    def _normalize_contact_block(cls, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        normalized_lines = []

        for line in lines:
            line = re.sub(r"\s+", " ", line).strip()
            normalized_lines.append(line)

        return "\n".join(normalized_lines)

    @classmethod
    def _dedupe_blocks(cls, blocks: list[ContactBlockCandidate]) -> list[ContactBlockCandidate]:
        unique: list[ContactBlockCandidate] = []
        seen = set()

        for block in blocks:
            key = block.normalized_text.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(block)

        return unique