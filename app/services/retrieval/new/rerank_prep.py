# from db.models import Chunk


# class RerankPrep:
#     @staticmethod
#     def compute_final_score(
#         chunk: Chunk,
#         similarity: float,
#         query_contact_intent: float,
#     ) -> float:
#         score = similarity

#         # штраф за boilerplate
#         score -= chunk.avg_boilerplate_score * 0.15

#         # contact chunks полезны только если есть контактный intent
#         contact_bonus = chunk.avg_contact_score * query_contact_intent * 0.12
#         contact_penalty = chunk.avg_contact_score * (1.0 - query_contact_intent) * 0.10

#         score += contact_bonus
#         score -= contact_penalty

#         # content chunks слегка поднимаем
#         score += chunk.avg_content_score * 0.10

#         return score

#     @classmethod
#     def rerank_candidates(
#         cls,
#         candidates: list[dict],
#         query_contact_intent: float,
#     ) -> list[dict]:
#         rescored = []

#         for item in candidates:
#             chunk = item["chunk"]
#             similarity = item["similarity"]

#             final_score = cls.compute_final_score(
#                 chunk=chunk,
#                 similarity=similarity,
#                 query_contact_intent=query_contact_intent,
#             )

#             rescored.append({
#                 "chunk": chunk,
#                 "similarity": similarity,
#                 "final_score": final_score,
#             })

#         rescored.sort(key=lambda x: x["final_score"], reverse=True)
#         return rescored