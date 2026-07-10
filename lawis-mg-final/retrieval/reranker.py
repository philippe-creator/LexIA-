import math
import threading
from loguru import logger
from core.config import settings

_reranker = None
_reranker_loaded = False
_reranker_lock = threading.Lock()

def get_reranker():
    """
    Charge le cross-encoder une seule fois (mis en cache).
    Verrou explicite pour la même raison que processing.embedder.get_model —
    évite un chargement concurrent depuis les threads de retrieve().
    """
    global _reranker, _reranker_loaded
    if not _reranker_loaded:
        with _reranker_lock:
            if not _reranker_loaded:
                try:
                    from sentence_transformers import CrossEncoder
                    _reranker = CrossEncoder(settings.RERANKER_MODEL)
                    logger.info(f"Cross-encoder chargé : {settings.RERANKER_MODEL}")
                except Exception as e:
                    logger.warning(f"Cross-encoder indisponible : {e}")
                    _reranker = None
                _reranker_loaded = True
    return _reranker

def rerank(query: str, candidates: list[dict], top_k: int = None) -> list[dict]:
    if not candidates: return []
    top_k = top_k or settings.TOP_K_RERANK
    reranker = get_reranker()
    if not reranker:
        return sorted(candidates, key=lambda x: x.get("rrf_score", x.get("score", 0)), reverse=True)[:top_k]
    try:
        pairs = [(query, c["text"][:512]) for c in candidates]
        scores = reranker.predict(pairs)
        # Le cross-encoder renvoie des logits bruts (pas bornés [0,1]) — on les
        # normalise via sigmoid pour un score de pertinence affichable en %.
        for i, c in enumerate(candidates): c["rerank_score"] = 1 / (1 + math.exp(-float(scores[i])))
        return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
    except Exception as e:
        logger.error(f"Erreur reranking : {e}")
        return sorted(candidates, key=lambda x: x.get("rrf_score", 0), reverse=True)[:top_k]

def compute_confidence(reranked: list[dict]) -> tuple[float, str]:
    if not reranked: return 0.0, "insuffisant"
    top = reranked[0]
    if "rerank_score" in top:
        # Déjà normalisé en [0,1] par le sigmoid appliqué dans rerank() — ne pas re-appliquer.
        norm = top["rerank_score"]
    else:
        # Fallback sans cross-encoder : score RRF brut, non borné — sigmoid pour ramener en [0,1].
        norm = 1 / (1 + math.exp(-top.get("rrf_score", 0)))
    label = "élevé" if norm >= 0.8 else "moyen" if norm >= 0.6 else "faible" if norm >= 0.4 else "insuffisant"
    return round(norm, 3), label
