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