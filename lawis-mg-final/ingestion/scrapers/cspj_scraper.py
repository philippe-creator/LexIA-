"""
Scraper CSPJ — jurisprudence Cour de cassation marocaine
Source : https://juriscassation.cspj.ma
Cible  : arrêts par chambre (sociale, commerciale, administrative, civile, pénale)
"""
import os
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from ingestion.scrapers.url_safety import same_origin

BASE_URL = os.getenv("CSPJ_BASE_URL", "https://juriscassation.cspj.ma")
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw")) / "jurisprudence"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Même souci de chaîne TLS incomplète côté serveur que cnss.ma — voir le
# commentaire dans ingestion/scrapers/cnss_scraper.py.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Chambres de la Cour de cassation — à mapper par domaine prioritaire
CHAMBRES = {
    "sociale": "travail",          # → enrichit le corpus droit du travail
    "commerciale": "societes",     # → enrichit le corpus droit des sociétés
    "administrative": "fiscal",    # → enrichit le corpus droit fiscal
    "penale": "penal",             # → enrichit le corpus droit pénal
    "civile": "jurisprudence",
    "statut-personnel": "jurisprudence",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_page(url: str, params: dict = None) -> BeautifulSoup | None:
    if not same_origin(url, BASE_URL):
        logger.warning(f"URL hors domaine ignorée : {url}")
        return None
    resp = requests.get(url, headers=HEADERS, params=params, timeout=20, verify=False)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def parse_decision(card_soup) -> dict | None:
    """Extrait les métadonnées d'une décision depuis son élément HTML."""
    try:
        title = card_soup.find(["h3", "h4", "strong"])
        title_text = title.get_text(strip=True) if title else "Sans titre"

        # Numéro d'arrêt, date, chambre
        meta = card_soup.get_text(" ", strip=True)
        link_tag = card_soup.find("a", href=True)
        link = BASE_URL + link_tag["href"] if link_tag and link_tag["href"].startswith("/") else (link_tag["href"] if link_tag else None)

        return {
            "title": title_text,
            "meta": meta[:200],
            "link": link,
        }
    except Exception as e:
        logger.debug(f"Erreur parse décision : {e}")
        return None


def fetch_decision_text(url: str) -> str:
    """Récupère le texte complet d'un arrêt depuis sa page dédiée."""
    soup = fetch_page(url)
    if not soup:
        return ""
    # Chercher le contenu principal de la décision
    content = soup.find("div", class_=lambda c: c and ("content" in c.lower() or "decision" in c.lower()))
    if not content:
        content = soup.find("main") or soup.find("article") or soup.body
    return content.get_text(" ", strip=True) if content else ""


def scrape_cspj(max_pages_per_chambre: int = 5) -> list[dict]:
    """
    Parcourt le portail CSPJ chambre par chambre.
    max_pages_per_chambre : limite pour le développement (augmenter en prod).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collected = []

    # Page d'accueil — identifier la structure de navigation
    home = fetch_page(BASE_URL)
    if not home:
        logger.error("Impossible d'accéder au portail CSPJ")
        return []

    logger.info("Portail CSPJ accessible. Début de la collecte par chambre.")

    for chambre, domaine in CHAMBRES.items():
        output_subdir = OUTPUT_DIR / chambre
        output_subdir.mkdir(exist_ok=True)

        for page_num in range(1, max_pages_per_chambre + 1):
            url = f"{BASE_URL}/fr/decisions"
            params = {"chambre": chambre, "page": page_num}

            logger.info(f"CSPJ chambre {chambre} — page {page_num}")
            soup = fetch_page(url, params=params)
            if not soup:
                break

            # Chercher les cartes/blocs de décisions
            cards = soup.find_all(["article", "div"], class_=lambda c: c and "decision" in c.lower())
            if not cards:
                # Fallback : chercher tous les liens vers des décisions
                cards = soup.find_all("li")

            if not cards:
                logger.info(f"Pas de résultats page {page_num} pour {chambre}, arrêt.")
                break

            for card in cards:
                decision = parse_decision(card)
                if not decision or not decision.get("link"):
                    continue

                # Sauvegarder le texte de l'arrêt dans un fichier .txt
                decision_id = decision["link"].split("/")[-1] or f"decision_{len(collected)}"
                dest = output_subdir / f"{decision_id}.txt"

                # Capturé AVANT l'écriture : sinon dest.exists() est toujours vrai
                # une fois le fichier créé juste en dessous, et is_new est toujours
                # faux — aucune décision n'est alors jamais indexée par la veille
                # (run_watch_cycle filtre sur is_new).
                was_new = not dest.exists()
                if was_new:
                    text = fetch_decision_text(decision["link"])
                    if text:
                        dest.write_text(text, encoding="utf-8")
                        logger.info(f"Arrêt sauvegardé : {dest.name}")
                        time.sleep(0.5)
                    else:
                        was_new = False

                collected.append({
                    "domain": domaine,
                    "source": "cspj",
                    "chambre": chambre,
                    "title": decision["title"],
                    "url": decision["link"],
                    "local_path": str(dest),
                    "is_new": was_new,
                })

            time.sleep(1)

    logger.info(f"CSPJ : {len(collected)} décisions collectées.")
    return collected


if __name__ == "__main__":
    scrape_cspj(max_pages_per_chambre=3)
