from collections import defaultdict, Counter

def build_global_fingerprint_stats(blocks: list[dict]) -> dict:
    stats = defaultdict(lambda: {
        "block_count": 0,
        "doc_ids": set(),
        "position_indices": [],
        "relative_tops": [],
        "relative_bottoms": [],
        "block_types": Counter(),
        "page_numbers": [],
    })

    for block in blocks:
        fp = block["fingerprint_text"]
        lf = block["local_features"]

        s = stats[fp]
        s["block_count"] += 1
        s["doc_ids"].add(block["doc_id"])
        s["position_indices"].append(block.get("position_index", 0))
        s["relative_tops"].append(lf.get("relative_top", 0.0))
        s["relative_bottoms"].append(lf.get("relative_bottom", 0.0))
        s["block_types"][block.get("block_type", "unknown")] += 1
        s["page_numbers"].append(block.get("page_number", 0))

    final_stats = {}

    for fp, s in stats.items():
        final_stats[fp] = {
            "block_count": s["block_count"],
            "doc_count": len(s["doc_ids"]),
            "avg_position_index": sum(s["position_indices"]) / len(s["position_indices"]) if s["position_indices"] else 0.0,
            "avg_relative_top": sum(s["relative_tops"]) / len(s["relative_tops"]) if s["relative_tops"] else 0.0,
            "avg_relative_bottom": sum(s["relative_bottoms"]) / len(s["relative_bottoms"]) if s["relative_bottoms"] else 0.0,
            "most_common_block_type": s["block_types"].most_common(1)[0][0] if s["block_types"] else "unknown",
            "min_page": min(s["page_numbers"]) if s["page_numbers"] else 0,
            "max_page": max(s["page_numbers"]) if s["page_numbers"] else 0,
        }

    return final_stats