"""
Pipeline d'ingestion — point d'entrée unique pour transformer un document
source en corpus interrogeable : extraction → indexation (chunking +
embedding + Chroma + invalidation BM25) → snapshot de version (BF-17).

Remplace la logique auparavant dispersée entre ingestion/watcher.py et
processing/indexer.py — un seul endroit à modifier si une étape change,
et un seul endroit où la règle de confidentialité des uploads privés
(voir ci-dessous) est appliquée.
"""
from pathlib import Path
from loguru import logger
from core.domains import validate_domain
from processing.indexer import index_document as _index_chunks

# Les documents uploadés par un utilisateur sont privés (visibles uniquement
# par leur propriétaire dans la recherche — voir retrieval/vector_search.py
# et retrieval/keyword_search.py). Un snapshot de version est partagé entre
# tous les utilisateurs via /compare — créer un snapshot pour un upload privé
# exposerait son contenu intégral à n'importe quel autre utilisateur.
_NO_SNAPSHOT_SOURCES = {"user_upload"}


def ingest_text(text: str, domain: str, filename: str, source: str = None, extra_metadata: dict = None) -> dict:
    """
    Ingère un texte déjà extrait dans le corpus d'un domaine.
    Retourne {"chunks_indexed": int, "snapshot_saved": bool}.
    """
    validate_domain(domain)
    if not text or not text.strip():
        logger.warning(f"Texte vide, ingestion ignorée : {filename}")
        return {"chunks_indexed": 0, "snapshot_saved": False}

    metadata = {"filename": filename, "source": source or "unknown", **(extra_metadata or {})}
    n_chunks = _index_chunks(text=text, domain=domain, metadata=metadata)

    snapshot_saved = False
    if source not in _NO_SNAPSHOT_SOURCES:
        try:
            from core.database import SessionLocal
            from api.repositories.snapshot_repo import save_snapshot
            db = SessionLocal()
            try:
                snap = save_snapshot(db, domain=domain, filename=filename, source=source, full_text=text)
                snapshot_saved = snap is not None
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Snapshot non enregistré pour '{filename}' : {e}")

    return {"chunks_indexed": n_chunks, "snapshot_saved": snapshot_saved}


def ingest_pdf(pdf_path: Path, domain: str, source: str = None, extra_metadata: dict = None) -> dict:
    """Extrait le texte d'un PDF (natif ou OCR) puis l'ingère."""
    from ingestion.ocr.pdf_extractor import extract_text
    pdf_path = Path(pdf_path)
    result = extract_text(pdf_path)
    return ingest_text(
        result["text"], domain=domain, filename=pdf_path.name, source=source,
        extra_metadata={**(extra_metadata or {}), "extraction_method": result.get("method")},
    )
