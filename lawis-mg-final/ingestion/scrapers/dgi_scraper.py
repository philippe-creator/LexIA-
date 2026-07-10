"""
Scraper DGI — droit fiscal
Source : https://www.tax.gov.ma
Cible  : CGI, lois de finances, notes circulaires, chartes contribuables
"""
import os
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from ingestion.scrapers.url_safety import same_origin, safe_filename

BASE_URL = os.getenv("DGI_BASE_URL", "https://www.tax.gov.ma")
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw")) / "fiscal"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Pages de législation et réglementation du portail DGI
SECTION_URLS = [
    f"{BASE_URL}/wps/portal/tax/particuliers/legislationetreglementation",
    f"{BASE_URL}/wps/portal/tax/professionnels/legislationetreglementation",
]

DOCUMENT_CATEGORIES = [
    "code-general-des-impots",
    "loi-de-finances",
    "note-circulaire",
    "textes-legislatifs",
    "charte-du-contribuable",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_page(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.error(f"Erreur fetch {url}: {e}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def download_pdf(url: str, dest: Path) -> bool:
    if dest.exists():
        logger.debug(f"Existant : {dest.name}")
        return False
    if not same_origin(url, BASE_URL):
        logger.warning(f"URL hors domaine ignorée : {url}")
        return False
    resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.info(f"Téléchargé : {dest.name}")
    return True


def extract_pdf_links(soup: BeautifulSoup, base: str) -> list[str]:
    """Extrait tous les liens PDF d'une page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                links.append(base + href)
    return links


def scrape_dgi() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collected = []

    for section_url in SECTION_URLS:
        logger.info(f"Scraping DGI section : {section_url}")
        soup = fetch_page(section_url)
        if not soup:
            continue

        pdf_links = extract_pdf_links(soup, BASE_URL)
        for url in pdf_links:
            filename = safe_filename(url.split("/")[-1].split("?")[0])
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            dest = OUTPUT_DIR / filename

            # Déterminer la catégorie selon l'URL
            category = "divers"
            for cat in DOCUMENT_CATEGORIES:
                if cat in url.lower():
                    category = cat
                    break

            try:
                is_new = download_pdf(url, dest)
                collected.append({
                    "domain": "fiscal",
                    "source": "dgi",
                    "category": category,
                    "url": url,
                    "local_path": str(dest),
                    "filename": filename,
                    "is_new": is_new,
                })
                time.sleep(1)
            except Exception:
                logger.warning(f"Ignoré : {url}")

    logger.info(f"DGI : {len(collected)} documents traités.")
    return collected


if __name__ == "__main__":
    results = scrape_dgi()
    logger.info(f"{len([r for r in results if r['is_new']])} nouveaux documents.")
