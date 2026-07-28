"""
Complète le corpus « jurisprudence » (vide) avec des arrêts de la Cour de
cassation marocaine récupérés sur juricaf.org.

À lancer quand juricaf est joignable (le site bannit temporairement les IP qui
scrapent trop vite ; réessayer plus tard ou depuis un autre réseau) :

    python -m scripts.complete_jurisprudence

Le script : (1) récupère ~150 arrêts via des recherches thématiques, en douceur ;
(2) les ingère dans le domaine « jurisprudence » ; (3) invalide le cache BM25.
Après exécution, redémarrer le backend pour recharger l'index vectoriel :
    docker compose restart api        (ou relancer uvicorn)
"""
import time
import re
import requests
from loguru import logger
from bs4 import BeautifulSoup

from ingestion.pipeline import ingest_text
from retrieval.keyword_search import invalidate_bm25_cache

TERMES = [
    "licenciement", "salaire", "preavis", "conge", "contrat travail", "indemnite",
    "societe", "commerce", "faillite", "bail commercial", "cheque", "gerant",
    "impot", "tva", "fiscal", "divorce", "succession", "responsabilite", "prescription",
]
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; LexIA-corpus/1.0)"})


def _get(url: str, timeout: int = 30):
    """Une seule tentative (les retries en rafale aggravent le bannissement)."""
    try:
        r = _SESSION.get(url, timeout=timeout)
        if r.status_code == 200 and len(r.text) > 1000:
            return r.text
    except requests.RequestException:
        pass
    return None


def collect_slugs() -> list[str]:
    slugs, seen = [], set()
    for terme in TERMES:
        html = _get(f"https://juricaf.org/recherche/{terme.replace(' ', '+')}/facet_pays:Maroc")
        if html:
            for slug in re.findall(r"/arret/(MAROC-COURDECASSATION-[0-9]+-[0-9]+)", html):
                if slug not in seen:
                    seen.add(slug)
                    slugs.append(slug)
        time.sleep(3)
    return slugs


def fetch_decision(slug: str) -> dict | None:
    html = _get(f"https://juricaf.org/arret/{slug}")
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    h = soup.find(["h1", "h2"])
    title = (h.get_text(" ", strip=True).strip(" |") if h else "")
    node = soup.find("div", {"id": "texte"}) or soup.find("div", class_="texte")
    text = re.sub(r"\n{3,}", "\n\n", node.get_text("\n", strip=True)).strip() if node else ""
    if len(text) < 200:
        return None
    m = re.match(r"MAROC-COURDECASSATION-(\d{4})(\d{2})(\d{2})-(\d+)", slug)
    date = f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else ""
    num = m.group(4) if m else ""
    cm = re.search(r"Chambre\s+([^,]+)", title)
    chambre = "Chambre " + cm.group(1).strip() if cm else ""
    return {"title": title, "date": date, "num": num, "chambre": chambre, "text": text}


def main():
    logger.info("Collecte des références d'arrêts sur juricaf…")
    slugs = collect_slugs()
    logger.info(f"{len(slugs)} arrêts référencés.")
    if not slugs:
        logger.error("Aucun arrêt récupéré — juricaf est probablement en train de bannir l'IP. "
                     "Réessayez plus tard ou depuis un autre réseau.")
        return

    total_chunks, kept = 0, 0
    for i, slug in enumerate(slugs, 1):
        dec = fetch_decision(slug)
        time.sleep(2.5)
        if not dec:
            continue
        header = f"Cour de cassation du Maroc — {dec['chambre'] or 'arrêt'} — {dec['date']} (n° {dec['num']})\n\n"
        res = ingest_text(
            header + dec["text"], domain="jurisprudence",
            filename=dec["title"] or f"Arrêt {dec['num']} du {dec['date']}",
            source="juricaf",
            extra_metadata={"date": dec["date"], "num": dec["num"], "chambre": dec["chambre"]},
        )
        total_chunks += res["chunks_indexed"]
        kept += 1
        if kept % 20 == 0:
            logger.info(f"  {kept} arrêts ingérés ({total_chunks} chunks)…")

    invalidate_bm25_cache()
    logger.info(f"Terminé : {kept} arrêts, {total_chunks} chunks dans « jurisprudence ». "
                f"Redémarrez le backend (docker compose restart api) pour recharger l'index.")


if __name__ == "__main__":
    main()
