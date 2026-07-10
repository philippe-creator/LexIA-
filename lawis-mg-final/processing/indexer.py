"""
Indexer — indexation des chunks dans les bases vectorielles par domaine.
Une base Chroma distincte par domaine juridique.
"""
import os
from pathlib import Path
from loguru import logger
import chromadb
from chromadb.config import Settings

from processing.chunker import chunk_document, Chunk
from processing.embedder import embed_documents
from core.domains import DOMAINS, validate_domain

VECTOR_STORE_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/vector_stores"))


def get_collection(domain: str) -> chromadb.Collection:
    """Retourne (ou crée) la collection Chroma pour un domaine donné."""
    validate_domain(domain)
    client = chromadb.PersistentClient(
        path=str(VECTOR_STORE_DIR / domain),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=domain,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def index_document(text: str, domain: str, metadata: dict = None) -> int:
    """
    Découpe un texte en chunks et les indexe dans le corpus du domaine.
    Retourne le nombre de chunks indexés.
    """
    metadata = metadata or {}
    if not text.strip():
        logger.warning("Texte vide, indexation ignorée.")
        return 0

    # Chunking
    chunks: list[Chunk] = chunk_document(text, metadata=metadata)
    if not chunks:
        logger.warning("Aucun chunk généré.")
        return 0

    # Embeddings
    texts = [c.text for c in chunks]
    embeddings = embed_documents(texts)

    # Indexation dans Chroma
    collection = get_collection(domain)

    # Générer des IDs uniques basés sur le contenu
    import hashlib
    ids = [
        hashlib.sha256((metadata.get("filename", "") + c.text[:100]).encode()).hexdigest()[:32]
        for c in chunks
    ]

    metadatas = [
        {**c.metadata, "domain": domain, **{k: str(v) for k, v in metadata.items()}}
        for c in chunks
    ]

    # Upsert (évite les doublons si le document est re-indexé)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    logger.info(f"Indexé : {len(chunks)} chunks dans le corpus '{domain}'")
    from retrieval.keyword_search import invalidate_bm25_cache
    invalidate_bm25_cache(domain)

    # Snapshot du texte intégral (hors chunks) pour la comparaison de versions (BF-17).
    try:
        from core.database import SessionLocal
        from api.repositories.snapshot_repo import save_snapshot
        db = SessionLocal()
        try:
            save_snapshot(db, domain=domain, filename=metadata.get("filename", "document"), source=metadata.get("source"), full_text=text)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Snapshot non enregistré pour '{metadata.get('filename')}' : {e}")

    return len(chunks)


def index_batch_from_dir(processed_dir: Path, domain: str) -> int:
    """Indexe tous les fichiers .txt d'un répertoire traité."""
    processed_dir = Path(processed_dir)
    total = 0
    for txt_file in processed_dir.rglob("*.txt"):
        text = txt_file.read_text(encoding="utf-8", errors="ignore")
        n = index_document(
            text=text,
            domain=domain,
            metadata={"filename": txt_file.name, "source": "batch"},
        )
        total += n
    logger.info(f"Batch {domain} : {total} chunks indexés au total.")
    return total


def get_corpus_stats() -> dict:
    """Retourne le nombre de documents par corpus."""
    stats = {}
    for domain in DOMAINS:
        try:
            col = get_collection(domain)
            stats[domain] = col.count()
        except Exception:
            stats[domain] = 0
    return stats


if __name__ == "__main__":
    from processing.indexer import get_corpus_stats
    stats = get_corpus_stats()
    print("État des corpus :")
    for domain, count in stats.items():
        print(f"  {domain}: {count} chunks")
