"""
Reconstruit les corpus depuis les fichiers sources de data/raw/ via le pipeline
d'ingestion unifié. Vide d'abord chaque collection Chroma concernée pour éviter
les doublons (les chunks issus de l'ancien chunker cassé cohabiteraient sinon
avec les nouveaux, leurs IDs de hash différant). Peuple aussi la table
document_snapshots (comparaison de versions, BF-17).

Usage : python -m scripts.backfill_corpus [domaine ...]
        (sans argument : tous les domaines ayant des fichiers dans data/raw)
"""
import sys
from pathlib import Path
from urllib.parse import unquote
from loguru import logger
import chromadb
from chromadb.config import Settings as ChromaSettings

from core.config import settings
from core.domains import DOMAINS
from ingestion.pipeline import ingest_pdf, ingest_text
from retrieval.keyword_search import invalidate_bm25_cache

RAW_DIR = Path(settings.RAW_DATA_DIR)
VECTOR_STORE_DIR = Path(settings.CHROMA_PERSIST_DIR)


def clear_collection(domain: str):
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR / domain), settings=ChromaSettings(anonymized_telemetry=False))
    try:
        client.delete_collection(name=domain)
        logger.info(f"Collection '{domain}' vidée.")
    except Exception as e:
        logger.info(f"Collection '{domain}' déjà vide ou absente ({e}).")


def backfill_domain(domain: str) -> dict:
    domain_dir = RAW_DIR / domain
    if not domain_dir.exists():
        logger.warning(f"Pas de répertoire source pour '{domain}'.")
        return {"domain": domain, "files": 0, "chunks": 0, "snapshots": 0}

    files = [f for f in domain_dir.rglob("*") if f.is_file() and f.suffix.lower() in {".pdf", ".txt", ".html"}]
    if not files:
        logger.warning(f"Aucun fichier exploitable dans data/raw/{domain}.")
        return {"domain": domain, "files": 0, "chunks": 0, "snapshots": 0}

    clear_collection(domain)
    invalidate_bm25_cache(domain)

    total_chunks, total_snapshots = 0, 0
    for f in files:
        # Les noms de fichiers téléchargés sont URL-encodés (%C3%A9...) — on
        # restitue un nom lisible pour l'affichage dans les citations et /compare.
        display_name = unquote(f.name)
        logger.info(f"[{domain}] Ingestion : {display_name}")
        try:
            if f.suffix.lower() == ".pdf":
                res = ingest_pdf(f, domain=domain, source="backfill", extra_metadata={"filename": display_name})
            else:
                text = f.read_text(encoding="utf-8", errors="ignore")
                res = ingest_text(text, domain=domain, filename=display_name, source="backfill")
            total_chunks += res["chunks_indexed"]
            total_snapshots += 1 if res["snapshot_saved"] else 0
        except Exception as e:
            logger.error(f"[{domain}] Échec sur {display_name} : {e}")

    return {"domain": domain, "files": len(files), "chunks": total_chunks, "snapshots": total_snapshots}


def main(domains: list[str]):
    if not domains:
        domains = [d for d in DOMAINS if (RAW_DIR / d).exists() and any((RAW_DIR / d).rglob("*"))]
    logger.info(f"Reconstruction des domaines : {domains}")
    results = [backfill_domain(d) for d in domains]
    logger.info("=== Résumé ===")
    for r in results:
        logger.info(f"  {r['domain']}: {r['files']} fichier(s) → {r['chunks']} chunks, {r['snapshots']} snapshot(s)")


if __name__ == "__main__":
    main(sys.argv[1:])
