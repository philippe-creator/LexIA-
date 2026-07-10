from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from core.config import settings
from retrieval.query_expander import expand_query
from retrieval.vector_search import multi_domain_vector_search
from retrieval.keyword_search import keyword_search
from retrieval.reranker import rerank, compute_confidence
from retrieval.router import route_query

RRF_K = 60

def _rrf(lists: list[list[dict]]) -> list[dict]:
    scores, docs = {}, {}
    for lst in lists:
        for rank, doc in enumerate(lst):
            key = doc["text"][:120]
            scores[key] = scores.get(key, 0) + 1 / (RRF_K + rank + 1)
            if key not in docs: docs[key] = doc
    fused = []
    for key in sorted(scores, key=lambda x: scores[x], reverse=True):
        d = docs[key].copy(); d["rrf_score"] = round(scores[key], 6); fused.append(d)
    return fused

def _search(variant: str, domains: list[str], n: int, user_id: str | None) -> list[dict]:
    results = []
    results.extend(multi_domain_vector_search(variant, domains, n_results_per_domain=n, user_id=user_id))
    for domain in domains: results.extend(keyword_search(variant, domain, n_results=n))
    return results

def retrieve(query: str, top_k: int = None, forced_domains: list[str] = None, user_id: str | None = None) -> tuple[list[dict], float, str, list[str]]:
    top_k = top_k or settings.TOP_K_RETRIEVAL
    domains = forced_domains or route_query(query)
    logger.info(f"Retrieval — domaines : {domains}")
    variants = expand_query(query, 2) if settings.QUERY_EXPANSION_ENABLED else [query]
    n = max(3, top_k)
    all_lists = []
    with ThreadPoolExecutor(max_workers=min(len(variants), 3)) as ex:
        futures = {ex.submit(_search, v, domains, n, user_id): v for v in variants}
        for f in as_completed(futures):
            try:
                res = f.result(timeout=15)
                if res: all_lists.append(res)
            except Exception as e: logger.warning(f"Variante échouée : {e}")
    if not all_lists: return [], 0.0, "insuffisant", domains
    fused = _rrf(all_lists)
    seen, deduped = set(), []
    for doc in fused:
        key = doc["text"][:80]
        if key not in seen: seen.add(key); deduped.append(doc)
    reranked = rerank(query, deduped[:top_k * 2], top_k=top_k)
    score, label = compute_confidence(reranked)
    logger.info(f"Retrieval — {len(reranked)} passages | confiance: {label} ({score:.2f})")
    return reranked, score, label, domains
