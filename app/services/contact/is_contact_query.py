CONTACT_QUERY_KEYWORDS = [
    "email", "e-mail", "mail",
    "phone", "telefon", "tel", "fax",
    "contact", "contacts",
    "address", "adres", "website", "site", "web"
]

def is_contact_query(query: str) -> bool:
    q = query.lower()
    return any(keyword in q for keyword in CONTACT_QUERY_KEYWORDS)