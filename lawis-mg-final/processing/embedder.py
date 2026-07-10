"""
Embedder — génération des vecteurs sémantiques.
Modèle recommandé : intfloat/multilingual-e5-large
(support français + arabe, performant sur textes juridiques)
"""
import os
import threading
from loguru import logger
from sentence_transformers import SentenceTransformer

# Modèle multilingue adapté au français et à l'arabe
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "intfloat/multilingual-e5-large"
)

# Préfixes recommandés par le modèle E5 pour améliorer la qualité
QUERY_PREFIX = "query: "
DOC_PREFIX = "passage: "

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def get_model() -> SentenceTransformer:
    """
    Charge le modèle une seule fois (mis en cache).
    Verrou explicite car retrieve() lance plusieurs variantes de requête en
    parallèle (ThreadPoolExecutor) — sans lui, deux threads peuvent déclencher
    un chargement concurrent du modèle et se retrouver avec des poids non
    matérialisés ("meta tensor").
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info(f"Chargement du modèle d'embedding : {EMBEDDING_MODEL}")
                _model = SentenceTransformer(EMBEDDING_MODEL)
                logger.info("Modèle chargé.")
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Génère les embeddings pour une liste de documents (passages).
    Utilise le préfixe 'passage:' recommandé par E5.
    """
    model = get_model()
    prefixed = [DOC_PREFIX + t for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """
    Génère l'embedding pour une requête utilisateur.
    Utilise le préfixe 'query:' recommandé par E5.
    """
    model = get_model()
    embedding = model.encode(QUERY_PREFIX + query, normalize_embeddings=True)
    return embedding.tolist()


if __name__ == "__main__":
    sample_docs = [
        "Le salarié a droit à un congé annuel payé.",
        "La TVA est fixée à 20% pour les services.",
    ]
    vecs = embed_documents(sample_docs)
    print(f"Vecteurs générés : {len(vecs)} × {len(vecs[0])} dimensions")

    q_vec = embed_query("Quels sont les droits du salarié en cas de licenciement ?")
    print(f"Vecteur requête : {len(q_vec)} dimensions")
