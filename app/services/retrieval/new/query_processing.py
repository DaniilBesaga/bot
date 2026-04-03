import re


class QueryProcessing:

    CONTACT_HINTS = [
        "tel", "telefon", "fax", "email", "e-mail", "contact", "office", "www", "webpage", "phone"
    ]
    @staticmethod
    def normalize_query(text: str) -> str:
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @classmethod
    def estimate_contact_intent(cls, query: str) -> float:
        q = query.lower()
        score = 0.0

        for word in cls.CONTACT_HINTS:
            if word in q:
                score += 0.2

        return min(score, 1.0)