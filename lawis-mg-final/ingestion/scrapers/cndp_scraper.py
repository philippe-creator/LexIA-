"""
Scraper CNDP — protection des données personnelles
Source : https://www.cndp.ma
Cible  : loi 09-08, décret 2-09-165, délibérations CNDP
"""
import os
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
from ingestion.scrapers.url_safety import same_origin, safe_filename

BASE_URL = os.getenv("CNDP_BASE_URL", "https://www.cndp.ma")
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw")) / "donnees_personnelles"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

KNOWN_URLS = [
    f"{BASE_URL}/fr/reglementation/",
    f"{BASE_URL}/fr/deliberations/",
    f"{BASE_URL}/fr/avis/",
    f"{BASE_URL}/fr/textes-juridiques/",
    f"{BASE_URL}/reglementation/",
    f"{BASE_URL}/deliberations/",
]


def fetch_page(url: str) -> BeautifulSoup | None:
    """Télécharge une page et retourne un objet BeautifulSoup. Retourne None si échec."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except Exception as e:
        logger.warning(f"Page inaccessible {url} : {e}")
        return None


def download_pdf(url: str, dest_path: Path) -> bool:
    """Télécharge un PDF vers dest_path. Retourne True si succès."""
    if dest_path.exists():
        logger.debug(f"Déjà téléchargé : {dest_path.name}")
        return False
    if not same_origin(url, BASE_URL):
        logger.warning(f"URL hors domaine ignorée : {url}")
        return False
    try:
        response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        response.raise_for_status()
        dest_path.write_bytes(response.content)
        logger.info(f"Téléchargé : {dest_path.name}")
        return True
    except Exception as e:
        logger.error(f"Erreur téléchargement PDF {url} : {e}")
        raise


def scrape_cndp() -> list[dict]:
    """
    Parcourt le site CNDP et télécharge tous les PDFs disponibles.
    Retourne une liste de métadonnées pour chaque document.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collected = []

    for page_url in KNOWN_URLS:
        logger.info(f"Scraping page CNDP : {page_url}")
        try:
            soup = fetch_page(page_url)
        except Exception as e:
            logger.warning(f"URL ignorée : {page_url} — {e}")
            continue
        if not soup:
            continue

        # Chercher tous les liens PDF
        links = soup.find_all("a", href=True)
        pdf_links = [
            a["href"] for a in links
            if a["href"].lower().endswith(".pdf")
        ]

        for href in pdf_links:
            # Construire l'URL absolue si relative
            if href.startswith("/"):
                full_url = BASE_URL + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = BASE_URL + "/" + href

            # Nom de fichier à partir de l'URL
            filename = safe_filename(href.split("/")[-1])
            dest = OUTPUT_DIR / filename

            try:
                is_new = download_pdf(full_url, dest)
                collected.append({
                    "domain": "donnees_personnelles",
                    "source": "cndp",
                    "url": full_url,
                    "local_path": str(dest),
                    "filename": filename,
                    "is_new": is_new,
                })
                time.sleep(1)  # politesse vis-à-vis du serveur
            except Exception:
                logger.warning(f"Ignoré après tentatives : {full_url}")

    logger.info(f"CNDP : {len(collected)} documents traités.")
    return collected


if __name__ == "__main__":
    results = scrape_cndp()
    new_docs = [r for r in results if r["is_new"]]
    logger.info(f"{len(new_docs)} nouveaux documents téléchargés.")
