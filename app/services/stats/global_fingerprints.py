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

def build_fingerprint_position_stats(blocks: list[dict]) -> dict:
    stats = defaultdict(list)

    for block in blocks:
        fp = block["fingerprint_text"]
        stats[fp].append(block.get("position_index", 0))

    result = {}
    for fp, positions in stats.items():
        result[fp] = {
            "min_position": min(positions),
            "max_position": max(positions),
            "avg_position": sum(positions) / len(positions),
            "position_span": max(positions) - min(positions),
        }

    return result

def attach_global_features(
    blocks: list[dict],
    fp_stats: dict,
    fp_position_stats: dict
) -> None:
    for block in blocks:
        fp = block["fingerprint_text"]
        fp_global = fp_stats.get(fp, {})
        fp_pos = fp_position_stats.get(fp, {})

        block["global_features"] = {
            "global_block_count": fp_global.get("block_count", 1),
            "global_doc_count": fp_global.get("doc_count", 1),
            "avg_position_index_for_fp": fp_global.get("avg_position_index", 0.0),
            "avg_relative_top_for_fp": fp_global.get("avg_relative_top", 0.0),
            "avg_relative_bottom_for_fp": fp_global.get("avg_relative_bottom", 0.0),
            "most_common_block_type_for_fp": fp_global.get("most_common_block_type", "unknown"),
            "position_span_for_fp": fp_pos.get("position_span", 0),
        }