from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from core.config import settings
from retrieval.query_expander import expand_query
from retrieval.vector_search import multi_domain_vector_search
from retrieval.keyword_search import keyword_search
from retrieval.reranker import rerank, compute_confidence
from retrieval.router import route_query

RRF_K = 60

# Le corpus indexé est presque exclusivement en français : router, expansion de
# requête et BM25 sont tous du texte/mots-clés français. Une requête en anglais
# ou en arabe échoue silencieusement à chaque étage (routage vers tous les
# domaines faute de mot-clé reconnu, 0 résultat BM25, cross-encoder comparant
# deux langues différentes) — confirmé empiriquement (confiance "insuffisant"
# systématique). On traduit donc la requête en français avant le pipeline de
# recherche ; la question originale et la langue de réponse restent inchangées
# pour la génération, seule la recherche elle-même passe par le français.
def _translate_query_to_french(query: str, lang: str) -> str:
    if lang == "fr":
        return query
    from generation.llm_client import generate
    try:
        translated = generate(
            "Traduis la question suivante en français, sans aucun commentaire ni "
            "explication. Réponds uniquement avec la traduction, rien d'autre. "
            "Conserve les nombres, dates et noms propres tels quels.",
            query,
        ).strip()
        return translated or query
    except Exception as e:
        logger.warning(f"Traduction de requête ({lang}→fr) échouée, recherche avec la requête originale : {e}")
        return query

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

def _search(variant: str, domains: list[str], n: int, user_id: str | None, doc_type: str | None, year: int | str | None, document_id: str | None) -> list[dict]:
    results = []
    results.extend(multi_domain_vector_search(variant, domains, n_results_per_domain=n, user_id=user_id, doc_type=doc_type, year=year, document_id=document_id))
    # L'index BM25 exclut structurellement les documents importés par les
    # utilisateurs (get_bm25_index ne charge que les chunks source != "user_upload")
    # — inutile de l'interroger quand on cible un document précis, il ne le
    # trouvera jamais.
    if not document_id:
        for domain in domains: results.extend(keyword_search(variant, domain, n_results=n, doc_type=doc_type, year=year))
    return results

def retrieve(query: str, top_k: int = None, forced_domains: list[str] = None, user_id: str | None = None, doc_type: str | None = None, year: int | str | None = None, document_id: str | None = None, lang: str = "fr") -> tuple[list[dict], float, str, list[str]]:
    top_k = top_k or settings.TOP_K_RETRIEVAL
    # Un filtre vide n'est pas un filtre : le front envoie "" quand « Tous types »
    # / « Toutes années » est sélectionné. Sans cette normalisation, Chroma
    # filtrait sur doc_type == "" (ou year == "") et ne trouvait plus rien.
    if isinstance(doc_type, str) and not doc_type.strip(): doc_type = None
    if isinstance(year, str) and not year.strip(): year = None
    query = _translate_query_to_french(query, lang)
    domains = forced_domains or route_query(query)
    logger.info(f"Retrieval — domaines : {domains}" + (f" | doc_type={doc_type}" if doc_type else "") + (f" | year={year}" if year else ""))
    variants = expand_query(query, 2) if settings.QUERY_EXPANSION_ENABLED else [query]
    n = max(3, top_k)
    all_lists = []
    with ThreadPoolExecutor(max_workers=min(len(variants), 3)) as ex:
        futures = {ex.submit(_search, v, domains, n, user_id, doc_type, year, document_id): v for v in variants}
        for f in as_completed(futures):
            try:
                res = f.result(timeout=settings.RETRIEVAL_TIMEOUT_SECONDS)
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
