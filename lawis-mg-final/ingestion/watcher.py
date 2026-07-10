"""
Module de veille — détection de nouveaux textes publiés
Compare l'état actuel des sources avec l'état précédemment enregistré.
Déclenche automatiquement l'ingestion si de nouveaux documents sont détectés.
"""
import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from loguru import logger

from ingestion.scrapers.cndp_scraper import scrape_cndp
from ingestion.scrapers.dgi_scraper import scrape_dgi
from ingestion.scrapers.cnss_scraper import scrape_cnss
from ingestion.scrapers.cspj_scraper import scrape_cspj
from ingestion.scrapers.opendata_client import collect_legal_datasets

STATE_FILE = Path(os.getenv("LOGS_DIR", "./logs")) / "watch_state.json"


def load_state() -> dict:
    """Charge l'état précédent depuis le fichier de persistance."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict):
    """Sauvegarde le nouvel état."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_fingerprint(documents: list[dict]) -> str:
    """Génère un hash unique représentant l'ensemble d'une liste de documents."""
    urls = sorted([d.get("url", d.get("local_path", "")) for d in documents])
    return hashlib.md5("|".join(urls).encode()).hexdigest()


def run_watch_cycle() -> dict:
    """
    Lance un cycle complet de veille sur toutes les sources.
    Retourne un rapport des changements détectés.
    """
    logger.info("=== Démarrage cycle de veille ===")
    state = load_state()
    report = {
        "timestamp": datetime.now().isoformat(),
        "sources_checked": [],
        "new_documents": [],
        "errors": [],
    }

    # Définition des sources à surveiller
    sources = [
        {"name": "cndp", "fn": scrape_cndp},
        {"name": "dgi", "fn": scrape_dgi},
        {"name": "cnss", "fn": scrape_cnss},
        {"name": "cspj", "fn": lambda: scrape_cspj(max_pages_per_chambre=2)},
        {"name": "opendata", "fn": collect_legal_datasets},
    ]

    new_state = {}

    for source in sources:
        name = source["name"]
        logger.info(f"Vérification source : {name}")
        try:
            docs = source["fn"]()
            fingerprint = compute_fingerprint(docs)

            # Comparer avec l'état précédent
            prev_fingerprint = state.get(name, {}).get("fingerprint")
            is_changed = fingerprint != prev_fingerprint

            new_state[name] = {
                "fingerprint": fingerprint,
                "last_check": datetime.now().isoformat(),
                "doc_count": len(docs),
                "changed": is_changed,
            }

            report["sources_checked"].append({
                "source": name,
                "doc_count": len(docs),
                "changed": is_changed,
            })

            if is_changed:
                new_docs = [d for d in docs if d.get("is_new")]
                report["new_documents"].extend(new_docs)
                logger.info(f"{name} : {len(new_docs)} nouveau(x) document(s) détecté(s)")

                # Déclencher l'indexation si nouveaux documents
                if new_docs:
                    _trigger_indexation(new_docs)

        except Exception as e:
            logger.error(f"Erreur source {name} : {e}")
            report["errors"].append({"source": name, "error": str(e)})

    save_state(new_state)
    _save_report(report)
    logger.info(f"=== Cycle terminé — {len(report['new_documents'])} nouveau(x) document(s) ===")
    return report


def _trigger_indexation(new_docs: list[dict]):
    """Déclenche le pipeline d'ingestion pour les nouveaux documents détectés."""
    from ingestion.pipeline import ingest_pdf, ingest_text
    from pathlib import Path

    for doc in new_docs:
        path = Path(doc.get("local_path", ""))
        if not path.exists():
            continue
        domain = doc.get("domain", "divers")
        source = doc.get("source")
        try:
            if path.suffix.lower() == ".pdf":
                result = ingest_pdf(path, domain=domain, source=source, extra_metadata={"url": doc.get("url")})
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
                result = ingest_text(text, domain=domain, filename=path.name, source=source, extra_metadata={"url": doc.get("url")})
            if result["chunks_indexed"]:
                logger.info(f"Indexé : {path.name} ({result['chunks_indexed']} chunks)")
        except Exception as e:
            logger.error(f"Erreur indexation {path.name} : {e}")


def _save_report(report: dict):
    """Sauvegarde le rapport de veille dans les logs."""
    log_dir = Path(os.getenv("LOGS_DIR", "./logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = log_dir / f"watch_report_{ts}.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Rapport sauvegardé : {report_file.name}")


if __name__ == "__main__":
    run_watch_cycle()
