"""
Indexer — indexation des chunks dans les bases vectorielles par domaine.
Une base Chroma distincte par domaine juridique.
"""
import os
from pathlib import Path
from loguru import logger
import chromadb
from chromadb.config import Settings

from processing.chunker import chunk_document, assign_pages, Chunk
from processing.embedder import embed_documents
from processing.doc_type import classify_doc_type, extract_year
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


def index_document(text: str, domain: str, metadata: dict = None, page_offsets: list[int] = None) -> int:
    """
    Découpe un texte en chunks et les indexe dans le corpus du domaine.
    `page_offsets` (optionnel, fourni pour les PDF) permet d'annoter chaque
    chunk avec son numéro de page d'origine — voir chunker.assign_pages.
    Retourne le nombre de chunks indexés.
    """
    metadata = metadata or {}
    if not text.strip():
        logger.warning("Texte vide, indexation ignorée.")
        return 0

    # Filtres avancés (type de document, année) — dérivés du nom de fichier,
    # appliqués uniformément à tous les chunks du document. Un appelant peut
    # fournir explicitement doc_type/year dans metadata pour outrepasser la
    # déduction automatique.
    metadata.setdefault("doc_type", classify_doc_type(metadata.get("filename"), domain))
    year = metadata.get("year") or extract_year(metadata.get("filename"))
    if year:
        metadata.setdefault("year", year)

    # Chunking
    chunks: list[Chunk] = chunk_document(text, metadata=metadata)
    if not chunks:
        logger.warning("Aucun chunk généré.")
        return 0
    assign_pages(chunks, text, page_offsets)

    # Embeddings
    texts = [c.text for c in chunks]
    embeddings = embed_documents(texts)

    # Indexation dans Chroma
    collection = get_collection(domain)

    # Générer des IDs uniques et stables. On combine le nom de fichier, l'index
    # du chunk et le texte INTÉGRAL (pas seulement les 100 premiers caractères) :
    # dans un texte juridique découpé par article, plusieurs articles partagent
    # souvent le même début ("Article X — Les dispositions…"), ce qui provoquait
    # des collisions d'IDs (upsert rejeté). L'index garantit l'unicité même entre
    # deux chunks byte-identiques ; le contenu complet garde l'idempotence lors
    # d'une ré-indexation du même document.
    #
    # Cas particulier des documents importés par un utilisateur (source=
    # "user_upload") : SANS `document_id` dans le hash, deux utilisateurs qui
    # importent le même fichier (même nom, même contenu — un texte officiel
    # téléchargé par les deux) calculent des IDs identiques. Le second upsert
    # écrase alors silencieusement les métadonnées (document_id, user_id) du
    # premier dans Chroma : son document reste "indexé" en base SQL mais
    # devient introuvable en pratique — contradiction avec la promesse de la
    # politique de confidentialité ("vos documents restent strictement
    # privés"). `document_id` est un UUID unique par import : l'inclure dans
    # le hash isole chaque upload sans toucher à l'idempotence du corpus
    # partagé (qui ne porte jamais de document_id).
    import hashlib
    doc_id = metadata.get("document_id", "")
    ids = [
        hashlib.sha256(
            f"{metadata.get('filename', '')}::{doc_id}::{c.metadata.get('chunk_idx', i)}::{c.text}".encode()
        ).hexdigest()[:32]
        for i, c in enumerate(chunks)
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
    """Retourne le nombre de chunks (passages indexés) par corpus."""
    stats = {}
    for domain in DOMAINS:
        try:
            col = get_collection(domain)
            stats[domain] = col.count()
        except Exception:
            stats[domain] = 0
    return stats


def get_corpus_document_counts() -> dict:
    """Retourne le nombre de documents DISTINCTS par corpus (déduplication par
    nom de fichier) — contrairement à get_corpus_stats(), qui compte les
    chunks. Un même document produit des dizaines de chunks ; le nombre de
    documents reflète mieux l'étendue réelle du corpus qu'un total de chunks,
    dont la valeur dépend surtout du découpage choisi."""
    counts = {}
    for domain in DOMAINS:
        try:
            col = get_collection(domain)
            res = col.get(include=["metadatas"])
            filenames = {m.get("filename", "?") for m in res["metadatas"]}
            counts[domain] = len(filenames)
        except Exception:
            counts[domain] = 0
    return counts


if __name__ == "__main__":
    from processing.indexer import get_corpus_stats
    stats = get_corpus_stats()
    print("État des corpus :")
    for domain, count in stats.items():
        print(f"  {domain}: {count} chunks")
