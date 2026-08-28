"""
Scraper CNSS — droit du travail
Source : https://www.cnss.ma/fr/content/textes-lois
Cible  : dahirs, décrets, arrêtés relatifs au travail et à la sécurité sociale
"""
import os
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from ingestion.scrapers.url_safety import same_origin, safe_filename

BASE_URL = os.getenv("CNSS_BASE_URL", "https://www.cnss.ma")
TEXTES_URL = f"{BASE_URL}/fr/content/textes-lois"
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw")) / "travail"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# cnss.ma sert une chaîne de certificats TLS incomplète côté serveur (CA
# intermédiaire manquante) — confirmé en direct (SSLCertVerificationError :
# "unable to get local issuer certificate"), pas un souci de notre côté. La
# désactivation ne s'applique qu'à ce domaine officiel ciblé en dur (voir
# BASE_URL/same_origin ci-dessus), jamais à une URL arbitraire.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_page(url: str) -> BeautifulSoup | None:
    resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def download_pdf(url: str, dest: Path) -> bool:
    if dest.exists():
        return False
    if not same_origin(url, BASE_URL):
        logger.warning(f"URL hors domaine ignorée : {url}")
        return False
    resp = requests.get(url, headers=HEADERS, timeout=30, stream=True, verify=False)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.info(f"Téléchargé : {dest.name}")
    return True


def scrape_cnss() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collected = []

    # La page CNSS liste les textes par catégorie (dahirs, décrets, arrêtés...)
    soup = fetch_page(TEXTES_URL)
    if not soup:
        logger.error("Impossible d'accéder à la page CNSS textes-lois")
        return []

    # Récupérer tous les liens (PDF et pages de sous-catégories)
    links = soup.find_all("a", href=True)

    sub_pages = []
    pdf_links = []

    for a in links:
        href = a["href"]
        full = href if href.startswith("http") else BASE_URL + href
        if not same_origin(full, BASE_URL):
            continue
        if href.lower().endswith(".pdf"):
            pdf_links.append(full)
        elif "/textes-lois/" in href or "/dahir" in href or "/decret" in href:
            sub_pages.append(full)

    # Explorer les sous-pages si nécessaire
    for sub_url in list(set(sub_pages))[:20]:  # limite de sécurité
        logger.info(f"Sous-page CNSS : {sub_url}")
        sub_soup = fetch_page(sub_url)
        if sub_soup:
            for a in sub_soup.find_all("a", href=True):
                if a["href"].lower().endswith(".pdf"):
                    full = a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
                    if same_origin(full, BASE_URL):
                        pdf_links.append(full)
        time.sleep(1)

    # Télécharger tous les PDFs
    for url in set(pdf_links):
        filename = safe_filename(url.split("/")[-1].split("?")[0])
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        dest = OUTPUT_DIR / filename
        try:
            is_new = download_pdf(url, dest)
            collected.append({
                "domain": "travail",
                "source": "cnss",
                "url": url,
                "local_path": str(dest),
                "filename": filename,
                "is_new": is_new,
            })
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Ignoré {url} : {e}")

    logger.info(f"CNSS : {len(collected)} documents traités.")
    return collected


if __name__ == "__main__":
    scrape_cnss()
