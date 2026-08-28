"""
Vector Search — recherche sémantique dense dans les corpus Chroma.
"""
from processing.indexer import get_collection
from processing.embedder import embed_query
from loguru import logger


def _is_visible(metadata: dict, user_id: str | None) -> bool:
    """Un chunk issu d'un upload privé n'est visible que par son propriétaire."""
    if metadata.get("source") != "user_upload":
        return True
    return metadata.get("user_id") == user_id


def _build_where(doc_type: str | None, year: int | str | None, document_id: str | None = None) -> dict | None:
    """Construit la clause `where` Chroma pour les filtres avancés (type de
    document, année, document précis). Enveloppe explicitement dans "$and" pour
    rester valide quelle que soit la version de chromadb (certaines exigent
    cette forme dès qu'il y a plus d'une condition)."""
    conds = []
    if doc_type:
        conds.append({"doc_type": doc_type})
    if year:
        conds.append({"year": str(year)})
    if document_id:
        conds.append({"document_id": document_id})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def vector_search(
    query: str,
    domain: str,
    n_results: int = 5,
    user_id: str | None = None,
    doc_type: str | None = None,
    year: int | str | None = None,
    document_id: str | None = None,
) -> list[dict]:
    """
    Recherche sémantique dans le corpus d'un domaine.
    Retourne une liste de résultats triés par similarité décroissante.
    Les documents uploadés par un autre utilisateur sont exclus des résultats.
    `doc_type`/`year` filtrent sur les métadonnées (voir processing.doc_type).
    `document_id` restreint aux seuls chunks d'un document importé précis
    ("discuter avec ce document").
    """
    try:
        collection = get_collection(domain)
        count = collection.count()
        if count == 0:
            logger.warning(f"Corpus '{domain}' vide — aucun résultat.")
            return []

        # On sur-échantillonne pour compenser le filtrage de visibilité ci-dessous
        # sans réduire artificiellement le nombre de résultats retournés.
        fetch_n = min(count, max(n_results * 3, n_results))
        query_embedding = embed_query(query)
        where = _build_where(doc_type, year, document_id)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_n,
            include=["documents", "metadatas", "distances"],
            **({"where": where} if where else {}),
        )

        hits = []
        for i in range(len(results["documents"][0])):
            metadata = results["metadatas"][0][i]
            if not _is_visible(metadata, user_id):
                continue
            hits.append({
                "text": results["documents"][0][i],
                "metadata": metadata,
                "score": 1 - results["distances"][0][i],  # cosine → similarité
                "domain": domain,
                "method": "vector",
            })
            if len(hits) >= n_results:
                break

        logger.debug(f"Vector search '{domain}' : {len(hits)} résultats")
        return hits

    except Exception as e:
        logger.error(f"Erreur vector_search [{domain}] : {e}")
        return []


def multi_domain_vector_search(
    query: str,
    domains: list[str],
    n_results_per_domain: int = 3,
    user_id: str | None = None,
    doc_type: str | None = None,
    year: int | str | None = None,
    document_id: str | None = None,
) -> list[dict]:
    """Recherche sémantique sur plusieurs domaines en parallèle."""
    all_results = []
    for domain in domains:
        results = vector_search(query, domain, n_results=n_results_per_domain, user_id=user_id, doc_type=doc_type, year=year, document_id=document_id)
        all_results.extend(results)
    return all_results
