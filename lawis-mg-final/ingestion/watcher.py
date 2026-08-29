"""
Module de veille — détection de nouveaux textes publiés
Compare l'état actuel des sources avec l'état précédemment enregistré.
Déclenche automatiquement l'ingestion si de nouveaux documents sont détectés.
"""
import json
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from loguru import logger

from ingestion.scrapers.cndp_scraper import scrape_cndp
from ingestion.scrapers.dgi_scraper import scrape_dgi
from ingestion.scrapers.cnss_scraper import scrape_cnss
from ingestion.scrapers.cspj_scraper import scrape_cspj
from ingestion.scrapers.opendata_client import collect_legal_datasets
from ingestion.scrapers.sgg_scraper import scrape_sgg
from ingestion.scrapers.jurisprudence_ma_scraper import scrape_jurisprudence_ma

STATE_FILE = Path(os.getenv("LOGS_DIR", "./logs")) / "watch_state.json"
# scrape_cspj() documente sa valeur par défaut (5) comme une limite de
# développement — jamais relevée pour un usage réel. Variable d'env pour
# pouvoir l'ajuster sans redéploiement.
CSPJ_MAX_PAGES = int(os.getenv("CSPJ_MAX_PAGES", "25"))
# scrape_sgg() ne télécharge que ce lot de numéros manquants par cycle
# automatique (24h) — suffisant pour la fraîcheur (nouvelles publications,
# toujours en tête de liste). Le rattrapage de l'archive complète (~4891
# numéros depuis 1912) est confié à un job séparé, plus fréquent, voir
# SGG_BACKFILL_* dans ingestion/scheduler.py — pas ce cycle-ci.
SGG_MAX_ISSUES = int(os.getenv("SGG_MAX_ISSUES", "20"))
# jurisprudence.ma : ~24 800 décisions disponibles (texte intégral, bien plus
# riche que juricaf.org) — même logique que SGG_MAX_ISSUES, un lot par cycle
# automatique, le reste s'accumule progressivement cycle après cycle.
JURISPRUDENCE_MA_MAX = int(os.getenv("JURISPRUDENCE_MA_MAX", "20"))


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


def _process_source(name: str, fn, prev_fingerprint: str | None) -> dict:
    """Scrape puis indexe une source — exécuté en parallèle (un thread par
    source) par run_watch_cycle(). Ne lève jamais : les erreurs sont
    retournées dans le résultat plutôt que propagées, pour ne pas interrompre
    les autres sources en cours."""
    logger.info(f"Vérification source : {name}")
    try:
        docs = fn()
    except Exception as e:
        logger.error(f"Erreur source {name} : {e}")
        return {"name": name, "error": str(e)}

    fingerprint = compute_fingerprint(docs)
    is_changed = fingerprint != prev_fingerprint
    new_docs = [d for d in docs if d.get("is_new")] if is_changed else []

    if new_docs:
        logger.info(f"{name} : {len(new_docs)} nouveau(x) document(s) détecté(s)")
        try:
            _trigger_indexation(new_docs)
        except Exception as e:
            logger.error(f"Erreur indexation source {name} : {e}")
        try:
            _notify_new_documents(name, new_docs)
        except Exception as e:
            logger.warning(f"Notification watch {name} ignorée : {e}")

    return {"name": name, "error": None, "fingerprint": fingerprint, "doc_count": len(docs), "changed": is_changed, "new_docs": new_docs}


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
        {"name": "cspj", "fn": lambda: scrape_cspj(max_pages_per_chambre=CSPJ_MAX_PAGES)},
        {"name": "opendata", "fn": collect_legal_datasets},
        {"name": "sgg", "fn": lambda: scrape_sgg(batch_size=SGG_MAX_ISSUES)},
        {"name": "jurisprudence_ma", "fn": lambda: scrape_jurisprudence_ma(batch_size=JURISPRUDENCE_MA_MAX)},
    ]

    # Sources traitées en parallèle, chacune dans son propre thread : sûr
    # car chaque domaine a sa propre collection Chroma (fichier persistant
    # séparé, voir get_collection() dans processing/indexer.py) et chaque
    # ingestion ouvre sa propre session SQLAlchemy (voir ingest_text()) —
    # la seule ressource partagée est le fichier SQLite de l'app, qui tolère
    # déjà les écritures concurrentes avec un repli sans casse (voir
    # save_snapshot() / ingest_text()). Accélère surtout les cycles où
    # plusieurs sources ont un vrai travail d'embedding à faire (ex. SGG et
    # jurisprudence.ma en même temps) plutôt que de les enchaîner en série.
    new_state = {}
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {
            executor.submit(_process_source, s["name"], s["fn"], state.get(s["name"], {}).get("fingerprint")): s["name"]
            for s in sources
        }
        for future in as_completed(futures):
            result = future.result()
            name = result["name"]
            if result["error"]:
                report["errors"].append({"source": name, "error": result["error"]})
                continue
            new_state[name] = {
                "fingerprint": result["fingerprint"],
                "last_check": datetime.now().isoformat(),
                "doc_count": result["doc_count"],
                "changed": result["changed"],
            }
            report["sources_checked"].append({"source": name, "doc_count": result["doc_count"], "changed": result["changed"]})
            if result["new_docs"]:
                report["new_documents"].extend(result["new_docs"])

    save_state(new_state)
    _save_report(report)
    logger.info(f"=== Cycle terminé — {len(report['new_documents'])} nouveau(x) document(s) ===")
    return report


def backfill_sgg_cycle(batch_size: int) -> dict:
    """
    Job séparé du cycle de veille normal (24h) : rattrape l'archive complète
    du Bulletin Officiel, `batch_size` numéros à la fois, à un rythme plus
    soutenu (voir SGG_BACKFILL_INTERVAL_HOURS dans ingestion/scheduler.py).

    Ne fait rien de spécial pour "reprendre" — scrape_sgg() saute déjà tout
    ce qui existe sur disque (dest.exists()), donc chaque appel reprend
    naturellement là où le précédent s'est arrêté, résumable après une
    interruption sans état à gérer ici.
    """
    logger.info(f"=== Rattrapage SGG — lot de {batch_size} numéro(s) ===")
    docs = scrape_sgg(batch_size=batch_size)
    new_docs = [d for d in docs if d.get("is_new")]
    if new_docs:
        _trigger_indexation(new_docs)
        try:
            _notify_new_documents("sgg_backfill", new_docs)
        except Exception as e:
            logger.warning(f"Notification rattrapage SGG ignorée : {e}")
    else:
        logger.info("Rattrapage SGG : archive à jour, rien à traiter.")
    logger.info(f"=== Rattrapage SGG terminé — {len(new_docs)} numéro(s) traité(s) ===")
    return {"new_documents": new_docs}


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
        # .xlsx est un binaire (archive ZIP) — path.read_text() dessus produit du
        # charabia (octets bruts décodés en UTF-8) au lieu d'un texte exploitable.
        # Tant qu'il n'y a pas d'extracteur dédié (ex. openpyxl), on l'ignore
        # plutôt que de polluer le corpus RAG et /compare avec du binaire.
        if path.suffix.lower() == ".xlsx":
            logger.info(f"Ignoré (xlsx, pas de texte exploitable) : {path.name}")
            continue
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


def _notify_new_documents(source_name: str, new_docs: list[dict]):
    from sqlalchemy.orm import Session
    from core.database import SessionLocal, User
    from services.notifications.notifier import create_notification
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == "admin", User.is_active == True).all()
        titles = [d.get("title") or d.get("filename") or "document" for d in new_docs[:3]]
        sample = ", ".join(titles)
        suffix = f" et {len(new_docs) - len(titles)} autre(s)" if len(new_docs) > len(titles) else ""
        for admin in admins:
            create_notification(
                db,
                user_id=admin.id,
                type="watch_new_document",
                title=f"Nouveaux documents — {source_name.upper()}",
                message=f"{len(new_docs)} nouveau(x) document(s) détecté(s) sur {source_name} : {sample}{suffix}.",
                data={"source": source_name, "count": len(new_docs), "documents": [d.get("url") for d in new_docs[:5] if d.get("url")]},
            )
    finally:
        db.close()



if __name__ == "__main__":
    run_watch_cycle()
