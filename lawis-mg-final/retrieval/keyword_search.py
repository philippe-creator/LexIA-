"""
Keyword Search — recherche lexicale BM25 (sparse).
Crucial pour les références exactes (article 9, loi 09-08, etc.)

L'index BM25 est construit sur les mêmes chunks que la base vectorielle
Chroma (source de vérité unique), pas sur un répertoire séparé.
"""
import re
from rank_bm25 import BM25Okapi
from loguru import logger
from processing.indexer import get_collection
from core.domains import DOMAINS


def tokenize(text: str) -> list[str]:
    """Tokenisation simple : minuscules + split sur les espaces/ponctuation."""
    return re.findall(r"\b\w+\b", text.lower())


class BM25Index:
    """Index BM25 construit depuis les chunks d'un domaine."""

    def __init__(self, domain: str):
        self.domain = domain
        self.documents: list[dict] = []
        self.index: BM25Okapi | None = None

    def build(self, documents: list[dict]):
        """Construit l'index depuis une liste de dicts {text, metadata}."""
        self.documents = documents
        corpus = [tokenize(d["text"]) for d in documents]
        self.index = BM25Okapi(corpus) if corpus else None
        logger.info(f"BM25 [{self.domain}] : {len(documents)} chunks indexés")

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Recherche BM25 et retourne les top-N résultats."""
        if not self.index or not self.documents:
            logger.warning(f"Index BM25 [{self.domain}] vide.")
            return []

        tokens = tokenize(query)
        scores = self.index.get_scores(tokens)

        scored = sorted(
            zip(scores, self.documents),
            key=lambda x: x[0],
            reverse=True,
        )[:n_results]

        results = []
        for score, doc in scored:
            if score > 0:
                results.append({
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": float(score),
                    "domain": self.domain,
                    "method": "bm25",
                })

        logger.debug(f"BM25 [{self.domain}] : {len(results)} résultats pour '{query[:50]}'")
        return results


# Cache des index BM25 en mémoire (évite de reconstruire à chaque requête).
# Invalidé explicitement par processing.indexer après chaque nouvelle indexation.
_bm25_cache: dict[str, BM25Index] = {}


def get_bm25_index(domain: str) -> BM25Index:
    """
    Retourne l'index BM25 pour un domaine.
    Construit depuis les chunks de la collection Chroma du domaine si absent du cache.
    Les documents uploadés par un utilisateur (privés) sont exclus de l'index
    partagé pour préserver la même isolation de visibilité que la recherche dense.
    """
    if domain not in DOMAINS:
        raise ValueError(f"Domaine invalide : {domain}")

    if domain in _bm25_cache:
        return _bm25_cache[domain]

    index = BM25Index(domain)
    try:
        collection = get_collection(domain)
        if collection.count() > 0:
            raw = collection.get(include=["documents", "metadatas"])
            documents = [
                {"text": text, "metadata": meta}
                for text, meta in zip(raw["documents"], raw["metadatas"])
                if meta.get("source") != "user_upload"
            ]
            if documents:
                index.build(documents)
    except Exception as e:
        logger.error(f"Erreur construction BM25 [{domain}] : {e}")

    _bm25_cache[domain] = index
    return index


def invalidate_bm25_cache(domain: str = None):
    """Invalide le cache BM25 (appelé après une nouvelle indexation dans Chroma)."""
    if domain:
        _bm25_cache.pop(domain, None)
    else:
        _bm25_cache.clear()


def keyword_search(query: str, domain: str, n_results: int = 5) -> list[dict]:
    """Point d'entrée : recherche BM25 dans un domaine."""
    index = get_bm25_index(domain)
    return index.search(query, n_results=n_results)
