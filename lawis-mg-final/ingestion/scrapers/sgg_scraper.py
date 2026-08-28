"""
Scraper SGG — Bulletin Officiel du Royaume du Maroc
Source : https://www.sgg.gov.ma (Secrétariat Général du Gouvernement)

La page de liste (BulletinOfficiel.aspx) charge son tableau en AJAX via un
module DNN (DataTables) — le HTML brut ne contient aucun lien PDF exploitable.
Mais le point d'API JSON sous-jacent, lui, est directement appelable et
renvoie l'intégralité de l'archive (numéro, date, URL du PDF) en un seul
appel — pas besoin de pagination ni de navigateur headless. Trouvé en
inspectant le script d'initialisation DataTables de la page (siteRoot +
"DesktopModules/MVC/TableListBO/BO/AjaxMethod"), qui exige un jeton
anti-CSRF (__RequestVerificationToken) présent dans la page HTML de départ.

Chaque numéro du Bulletin Officiel est une publication généraliste (il
mélange souvent plusieurs lois de domaines différents dans un même numéro) —
contrairement aux autres scrapers, il n'y a pas de domaine juridique unique
à lui assigner. Rattaché à "divers" par défaut.
"""
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.scrapers.url_safety import same_origin, safe_filename

BASE_URL = os.getenv("SGG_BASE_URL_ROOT", "https://www.sgg.gov.ma")
LIST_PAGE_URL = f"{BASE_URL}/BulletinOfficiel.aspx"
AJAX_URL = f"{BASE_URL}/DesktopModules/MVC/TableListBO/BO/AjaxMethod"
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw")) / "divers" / "bulletin_officiel"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

_TOKEN_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')
_DOTNET_DATE_RE = re.compile(r"/Date\((-?\d+)\)/")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _fetch_issue_list(session: requests.Session) -> list[dict]:
    """Une session (cookies + jeton CSRF) est requise avant l'appel AJAX —
    le jeton est lié à la session ouverte par la première requête GET."""
    resp = session.get(LIST_PAGE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    m = _TOKEN_RE.search(resp.text)
    if not m:
        logger.error("Jeton anti-CSRF introuvable sur la page SGG — structure de page changée ?")
        return []
    token = m.group(1)
    ajax_headers = {
        **HEADERS,
        "ModuleId": "2873",
        "TabId": "775",
        "RequestVerificationToken": token,
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = session.post(AJAX_URL, headers=ajax_headers, data={}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_dotnet_date(raw: str) -> str | None:
    m = _DOTNET_DATE_RE.search(raw or "")
    if not m:
        return None
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date().isoformat()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _download_pdf(session: requests.Session, url: str, dest: Path) -> bool:
    if dest.exists():
        return False
    if not same_origin(url, BASE_URL):
        logger.warning(f"URL hors domaine ignorée : {url}")
        return False
    resp = session.get(url, headers=HEADERS, timeout=30, stream=True)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.info(f"Téléchargé : {dest.name}")
    return True


def scrape_sgg(batch_size: int = 20) -> list[dict]:
    """
    Parcourt l'intégralité de l'archive du Bulletin Officiel (~4891 numéros
    depuis 1912 — un seul appel API, rapide) et télécharge les `batch_size`
    premiers numéros pas encore présents localement (`dest.exists()` fait
    l'idempotence, comme les autres scrapers du projet).

    Un même mécanisme sert deux besoins à la fois, sans état à persister :
    - fraîcheur : un numéro tout juste publié est toujours en tête de liste
      → toujours traité en premier, immédiatement ;
    - rattrapage historique : une fois les numéros récents déjà tous sur
      disque, le parcours continue automatiquement plus loin dans la liste
      et rattrape les plus anciens jamais téléchargés, `batch_size` par
      `batch_size` — résumable à tout moment (rien de perdu si interrompu,
      la prochaine exécution resaute tout ce qui existe déjà sur disque).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    issues = _fetch_issue_list(session)
    if not issues:
        logger.error("Impossible de récupérer la liste des numéros du Bulletin Officiel.")
        return []
    logger.info(f"SGG : {len(issues)} numéro(s) disponible(s) dans l'archive, lot de {batch_size} nouveau(x) numéro(s) visé.")

    collected = []
    new_count = 0
    for issue in issues:
        if new_count >= batch_size:
            break
        bo_url = issue.get("BoUrl", "")
        if not bo_url:
            continue
        full_url = bo_url if bo_url.startswith("http") else f"{BASE_URL}{bo_url}"
        filename = safe_filename(full_url)
        dest = OUTPUT_DIR / filename

        if dest.exists():
            continue  # déjà téléchargé lors d'un cycle précédent — gratuit, pas d'appel réseau

        try:
            is_new = _download_pdf(session, full_url, dest)
        except Exception as e:
            logger.warning(f"Ignoré {full_url} : {e}")
            continue

        collected.append({
            "domain": "divers",
            "source": "sgg_bulletin_officiel",
            "bo_num": issue.get("BoNum"),
            "bo_date": _parse_dotnet_date(issue.get("BoDate", "")),
            "url": full_url,
            "local_path": str(dest),
            "filename": filename,
            "is_new": is_new,
        })
        if is_new:
            new_count += 1
            time.sleep(1)

    if new_count == 0 and len(collected) == 0:
        logger.info("SGG : archive à jour, aucun numéro manquant trouvé.")
    else:
        logger.info(f"SGG : {len(collected)} numéro(s) traité(s), {new_count} nouveau(x).")
    return collected


if __name__ == "__main__":
    results = scrape_sgg(batch_size=10)
    logger.info(f"{len([r for r in results if r['is_new']])} nouveaux documents.")
