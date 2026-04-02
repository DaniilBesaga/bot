
from app.services.process_document.pipeline import Pipeline
from app.services.stats.global_fingerprints import build_global_fingerprint_stats


def build_block_statistics_and_scores(all_documents: list[dict]) -> list[dict]:
    blocks = Pipeline.prepare_blocks(all_documents)

    fp_stats = build_global_fingerprint_stats(blocks)
    fp_position_stats = build_fingerprint_position_stats(blocks)

    attach_global_features(blocks, fp_stats, fp_position_stats)
    attach_scores(blocks)

    return blocks