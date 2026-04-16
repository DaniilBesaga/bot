def build_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks = []

    for chunk in chunks:
        source = chunk.get("file_name", "Sursă necunoscută")
        text_value = chunk.get("text", "")
        context_blocks.append(f"Sursă: {source}\n{text_value}\n\n")

    context = "\n\n --- \n\n".join(context_blocks)
    return f"""
    Ești asistentul companiei.
    Răspunde doar pe baza contextului de mai jos.
    Dacă nu există un răspuns exact în context, menționează acest lucru.
    Nu inventa caracteristici, prețuri, termene și condiții.

    Context:
    {context}

    Întrebare:
    {question}
    """.strip()

def build_prompt_question(chunks: list[dict]) -> str:
    context_blocks = []

    for chunk in chunks:
        source = chunk.get("file_name", "Sursă necunoscută")
        text_value = (chunk.get("chunk_text") or "").strip()
        context_blocks.append(f"Sursă: {source}\n{text_value}")

    context = "\n\n---\n\n".join(context_blocks)

    return f"""
        Generezi O SINGURĂ pereche întrebare-răspuns (question-answer) pentru antrenarea unui model retrieval/reranker.

        Reguli stricte:
        1. Întrebarea trebuie să fie în ACEEAȘI LIMBĂ ca și textul sursă.
        2. Nu traduce textul și nu traduce întrebarea în altă limbă.
        3. Răspunsul la întrebare trebuie să poată fi dedus EXCLUSIV din textul de mai jos.
        4. Nu folosi cunoștințe externe.
        5. Nu inventa nume de companii, branduri, modele sau caracteristici care nu se află în text.
        6. Dacă textul reprezintă informații de contact, o adresă, un subsol (footer), elemente de navigare, un bloc publicitar prea general, un fragment de tabel sau nu conține un fapt concret — returnează skip=true.
        7. Întrebarea trebuie să fie specifică și verificabilă.
        8. Răspunsul trebuie să fie scurt și să se regăsească explicit în text.
        9. Nu pune întrebări despre companie, adresă sau contacte, dacă textul nu este un fragment descriptiv cu sens.
        10. Dacă ai îndoieli — skip=true.

        Returnează strict JSON:
        {{
        "skip": true,
        "language": "",
        "question": "",
        "answer": "",
        "reason": ""
        }}

        sau

        {{
        "skip": false,
        "language": "ro / it / en / ...",
        "question": "...",
        "answer": "...",
        "reason": ""
        }}


        Context:
        {context}
        """.strip()

def build_prompt_validate(question: str, answer: str, chunk_text: str) -> str:
    chunk_text = (chunk_text or "").strip()

    return f"""
        Verifici calitatea unei perechi QA sintetice pentru antrenarea unui model retrieval/reranker.

        Verifică următoarele:
        1. Întrebarea este scrisă în aceeași limbă ca textul.
        2. La întrebare se poate răspunde exclusiv pe baza textului.
        3. Răspunsul se regăsește explicit în text.
        4. Întrebarea nu necesită cunoștințe externe.
        5. Întrebarea nu este prea generală, inventată sau de marketing.
        6. Textul nu este doar un bloc de contact, un subsol (footer), o adresă sau zgomot.

        Returnează strict JSON:
        {{
        "valid": true,
        "grounded": true,
        "answer_supported": true,
        "same_language": true,
        "reason": ""
        }}

        sau

        {{
        "valid": false,
        "grounded": false,
        "answer_supported": false,
        "same_language": false,
        "reason": ""
        }}

        Întrebare:
        {question}

        Răspuns:
        {answer}

        Text:
        \"\"\"
        {chunk_text}
        \"\"\"
        """.strip()

def build_translation_prompt_to_romanian(
    *,
    text: str,
    source_language: str,
) -> str:
    return f"""
Tradu în limba română textul tehnic de mai jos.

Reguli stricte:
1. Păstrează exact numele modelelor, codurile, articolele, RPM, unitățile de măsură, dimensiunile, presiunile, volumele, diametrele și valorile numerice.
2. Nu inventa nimic.
3. Nu omite detalii tehnice.
4. Nu rezuma și nu reformula excesiv.
5. Dacă textul conține termeni de marcă sau denumiri comerciale, păstrează-le.
6. Dacă textul este deja în română, întoarce-l practic neschimbat.
7. Nu adăuga explicații.
8. Întoarce strict JSON.

Returnează strict JSON:
{{
  "translated_text_ro": "...",
  "notes": ""
}}

Limba sursă: {source_language}

Text:
\"\"\"
{text}
\"\"\"
""".strip()