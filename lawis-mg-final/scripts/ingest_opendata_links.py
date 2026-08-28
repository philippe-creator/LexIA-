"""
Certains fichiers xlsx téléchargés par le scraper Open Data (opendata_client.py)
ne sont pas des données brutes mais des annuaires de liens vers de vrais textes
PDF (ex. lois organiques sur les collectivités territoriales). Ces xlsx ne sont
jamais ingérés tels quels (contenu = liens, pas du texte juridique) — ce script
en extrait les liens PDF, télécharge les documents réels et les ingère proprement.

Usage :
    python -m scripts.ingest_opendata_links
"""
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import openpyxl
import requests
from loguru import logger

from ingestion.pipeline import ingest_pdf
from ingestion.scrapers.url_safety import safe_filename
from core.domains import DOMAINS

RAW_DIR = Path("data/raw")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LexIA-corpus/1.0)"}


def find_pdf_links(xlsx_path: Path) -> list[tuple[str, str]]:
    """Retourne les (titre, url) des liens PDF trouvés dans le classeur —
    le titre est repris de la première cellule non vide de la même ligne."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=False)
    found = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            title = next((str(c.value).strip() for c in row if isinstance(c.value, str) and c.value.strip()), "")
            for cell in row:
                url = cell.hyperlink.target if cell.hyperlink else None
                if url and ".pdf" in url.lower():
                    found.append((title, url))
    return found


def download(url: str, dest: Path) -> bool:
    if dest.exists():
        return False
    resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return True


def main():
    xlsx_files = [p for p in RAW_DIR.rglob("*.xlsx") if not p.name.startswith("~$")]
    logger.info(f"{len(xlsx_files)} fichier(s) xlsx à examiner.")

    all_links: dict[str, str] = {}  # url -> titre (dédoublonné entre fichiers)
    for p in xlsx_files:
        for title, url in find_pdf_links(p):
            all_links.setdefault(url, title or Path(urlparse(url).path).name)

    logger.info(f"{len(all_links)} lien(s) PDF unique(s) trouvé(s).")
    if not all_links:
        return

    ingested, skipped, errors = 0, 0, 0
    for url, title in all_links.items():
        domain = "divers"  # collectivités territoriales ne correspond à aucun domaine dédié existant
        dest_dir = RAW_DIR / domain / "opendata_pdfs"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / safe_filename(url)

        try:
            is_new = download(url, dest)
        except Exception as e:
            logger.warning(f"Téléchargement échoué {url} : {e}")
            errors += 1
            continue

        if not is_new:
            skipped += 1
            continue

        try:
            result = ingest_pdf(dest, domain=domain, source="opendata_gov_pdf", filename=title, extra_metadata={"url": url})
            logger.info(f"Ingéré : {title} ({result['chunks_indexed']} chunks)")
            ingested += 1
        except Exception as e:
            logger.warning(f"Ingestion échouée {title} : {e}")
            errors += 1

    logger.info(f"Terminé : {ingested} document(s) ingéré(s), {skipped} déjà présent(s), {errors} échec(s).")


if __name__ == "__main__":
    main()
