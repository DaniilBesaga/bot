def build_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks = []

    for chunk in chunks:
        source = chunk.get("file_name", "Unknown Source")
        text_value = chunk.get("text", "")
        context_blocks.append(f"Источник: {source}\n{text_value}\n\n")

    context = "\n\n --- \n\n".join(context_blocks)
    return f"""
    Ты ассистент компании.
    Отвечай только на основе контекста ниже.
    Если точного ответа в контексте нет, так и скажи.
    Не выдумывай характеристики, цены, сроки и условия.

    Контекст:
    {context}

    Вопрос:
    {question}
    """.strip()

def build_prompt_question(chunks: list[dict]) -> str:
    context_blocks = []

    for chunk in chunks:
        source = chunk.get("file_name", "Unknown Source")
        text_value = (chunk.get("chunk_text") or "").strip()
        context_blocks.append(f"Источник: {source}\n{text_value}")

    context = "\n\n---\n\n".join(context_blocks)

    return f"""
        Ты генерируешь ОДНУ question-answer пару для обучения retrieval/reranker модели.

        Строгие правила:
        1. Вопрос должен быть на ТОМ ЖЕ ЯЗЫКЕ, что и исходный текст.
        2. Не переводи текст и не переводи вопрос на другой язык.
        3. Вопрос должен быть отвечаем ИСКЛЮЧИТЕЛЬНО по тексту ниже.
        4. Нельзя использовать внешние знания.
        5. Нельзя придумывать названия компаний, брендов, моделей, характеристик, которых нет в тексте.
        6. Если текст является контактной информацией, адресом, футером, навигацией, слишком общим рекламным блоком, обрывком таблицы или не содержит конкретного факта — верни skip=true.
        7. Вопрос должен быть конкретным и проверяемым.
        8. Ответ должен быть коротким и явно содержаться в тексте.
        9. Не задавай вопросы про компанию, адрес, контакты, если текст не является осмысленным описательным фрагментом.
        10. Если сомневаешься — skip=true.

        Верни строго JSON:
        {{
        "skip": true,
        "language": "",
        "question": "",
        "answer": "",
        "reason": ""
        }}

        или

        {{
        "skip": false,
        "language": "ro / it / en / ...",
        "question": "...",
        "answer": "...",
        "reason": ""
        }}


        Контекст:
        {context}
        """.strip()

def build_prompt_validate(question: str, answer: str, chunk_text: str) -> str:
    chunk_text = (chunk_text or "").strip()

    return f"""
        Ты проверяешь качество synthetic QA-пары для обучения retrieval/reranker модели.

        Проверь:
        1. Вопрос написан на том же языке, что и текст.
        2. На вопрос можно ответить исключительно по тексту.
        3. Ответ явно содержится в тексте.
        4. Вопрос не требует внешних знаний.
        5. Вопрос не является слишком общим, выдуманным или маркетинговым.
        6. Текст не является просто контактным блоком, футером, адресом или шумом.

        Верни строго JSON:
        {{
        "valid": true,
        "grounded": true,
        "answer_supported": true,
        "same_language": true,
        "reason": ""
        }}

        или

        {{
        "valid": false,
        "grounded": false,
        "answer_supported": false,
        "same_language": false,
        "reason": ""
        }}

        Вопрос:
        {question}

        Ответ:
        {answer}

        Текст:
        \"\"\"
        {chunk_text}
        \"\"\"
        """.strip()