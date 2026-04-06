
def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def compute_contact_score(block: dict) -> float:
    lf = block["local_features"]
    gf = block["global_features"]

    score = 0.0

    if lf["has_email"]:
        score += 0.35
    if lf["has_url"]:
        score += 0.20
    if lf["has_phone_like"]:
        score += 0.30

    score += min(lf["contact_term_count"] * 0.08, 0.20)
    score += min(lf["digit_ratio"] * 1.2, 0.15)

    if lf["is_short"]:
        score += 0.08

    # если блок часто повторяется глобально — это часто служебный контактный блок
    score += min(gf["global_doc_count"] / 12.0, 0.15)

    # если блок вверху страницы, это тоже частый паттерн для контактов/хедера
    if lf["relative_top"] < 0.15:
        score += 0.08

    return clamp01(score)

def compute_boilerplate_score(block: dict) -> float:
    lf = block["local_features"]
    gf = block["global_features"]

    score = 0.0

    score += min(gf["global_doc_count"] / 20.0, 0.35)
    score += min(gf["global_block_count"] / 30.0, 0.20)

    if lf["is_short"]:
        score += 0.08

    if lf["block_type"] in ("short_meta", "header", "footer"):
        score += 0.20

    if gf["global_doc_count"] >= 3:
        score += 0.12

    # если fingerprint почти всегда появляется в одинаковой позиции
    if gf["position_span_for_fp"] <= 1:
        score += 0.12

    # если блок обычно очень близко к верху или низу страницы
    if gf["avg_relative_top_for_fp"] < 0.12 or gf["avg_relative_bottom_for_fp"] > 0.88:
        score += 0.10

    return clamp01(score)

def compute_content_score(block: dict) -> float:
    lf = block["local_features"]
    gf = block["global_features"]

    score = 0.0

    word_count = lf["word_count"]
    if 8 <= word_count <= 120:
        score += 0.20
    elif 4 <= word_count < 8:
        score += 0.10

    if lf["block_type"] in ("paragraph", "list", "table_text", "heading"):
        score += 0.15

    if gf["global_doc_count"] <= 2:
        score += 0.15

    if not lf["has_email"] and not lf["has_url"] and not lf["has_phone_like"]:
        score += 0.05

    return clamp01(score)

def attach_scores(blocks: list[dict]) -> None:
    for block in blocks:
        block["contact_score"] = compute_contact_score(block)
        block["boilerplate_score"] = compute_boilerplate_score(block)
        block["content_score"] = compute_content_score(block)