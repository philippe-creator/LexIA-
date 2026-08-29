"""
Scraper jurisprudence.ma — décisions de justice marocaines, texte intégral.

Bien plus riche que juricaf.org (résumés seulement, déjà exploité via
scripts/complete_jurisprudence.py) : ~24 800 décisions au total, chaque page
contient à la fois un résumé rédigé en français (plusieurs paragraphes) et
le texte intégral de la décision originale (arabe, dir="rtl") — les deux
sont ingérés ensemble, le résumé pour l'ancrage sémantique en français, le
texte intégral pour la valeur probante complète.

Un bouton "Exporter en PDF" existe mais génère un lien à jeton unique par
page (?pdf=ID&t=...) — inutile puisque le contenu est déjà dans le HTML.

Comme scrape_sgg() : parcourt les pages de chaque thème (les plus récentes
en premier), télécharge/ingère jusqu'à `batch_size` décisions pas encore
présentes localement (dest.exists() fait l'idempotence), résumable sans
état à persister — une exécution reprend naturellement là où la précédente
s'est arrêtée.
"""
import os
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = os.getenv("JURISPRUDENCE_MA_BASE_URL", "https://www.jurisprudence.ma")
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw")) / "jurisprudence" / "jurisprudence_ma"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LexIA-corpus/1.0)"}
_MAX_PAGES_PER_THEME = 300  # garde-fou anti-boucle infinie, pas une limite réelle en usage normal

# Thèmes du site -> domaine prioritaire correspondant (même logique que
# CHAMBRES dans cspj_scraper.py : enrichit le corpus du domaine concerné
# plutôt que de tout reléguer dans "jurisprudence"). Vérifié par sous-chaîne,
# insensible à la casse ; premier thème qui matche l'emporte.
THEME_DOMAIN_MAP = {
    "commercial": "societes", "société": "societes", "societes": "societes",
    "social": "travail", "travail": "travail",
    "fiscal": "fiscal", "impôt": "fiscal", "impot": "fiscal", "tva": "fiscal",
    "données personnelles": "donnees_personnelles",
    "pénal": "penal", "penal": "penal", "criminel": "penal",
}
THEMES = [
    "commercial", "civil", "penal", "social", "administratif", "famille",
    "assurance", "immobilier", "bancaire", "societes",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _get(url: str) -> str | None:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.text


def _decision_domain(theme_text: str) -> str:
    low = theme_text.lower()
    for keyword, domain in THEME_DOMAIN_MAP.items():
        if keyword in low:
            return domain
    return "jurisprudence"


def _parse_decision(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("div", class_="detail-table")
    if not table:
        return None

    fields = {}
    labels = table.find_all("p", class_="is-bold")
    for label in labels:
        value_p = label.find_next_sibling("p")
        if value_p:
            fields[label.get_text(strip=True)] = value_p.get_text(" ", strip=True)

    title_tag = soup.find("h2", class_="is-bold")
    title = title_tag.get_text(strip=True) if title_tag else fields.get("Réf", "Décision")

    blocs = soup.find_all("div", class_="is-bloc")
    resume, texte_integral = "", ""
    for bloc in blocs:
        h4 = bloc.find("h4")
        edito = bloc.find("div", class_="is-edito")
        if not h4 or not edito:
            continue
        paragraphs = "\n\n".join(p.get_text(" ", strip=True) for p in edito.find_all("p"))
        if "résumé" in h4.get_text(strip=True).lower():
            resume = paragraphs
        elif "intégral" in h4.get_text(strip=True).lower():
            texte_integral = paragraphs

    if not resume and not texte_integral:
        return None

    parts = [f"{title}\n"]
    parts.append(f"Juridiction : {fields.get('Juridiction', '?')} — {fields.get('Pays/Ville', '?')}")
    parts.append(f"N° de décision : {fields.get('N° de décision', '?')} — Date : {fields.get('Date de décision', '?')}")
    if resume:
        parts.append(f"\n--- Résumé en français ---\n{resume}")
    if texte_integral:
        parts.append(f"\n--- Texte intégral ---\n{texte_integral}")

    return {
        "ref": fields.get("Réf", ""),
        "title": title,
        "theme": fields.get("Thème", ""),
        "text": "\n\n".join(parts),
    }


def scrape_jurisprudence_ma(batch_size: int = 20) -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collected = []
    new_count = 0

    for theme in THEMES:
        if new_count >= batch_size:
            break
        for page in range(1, _MAX_PAGES_PER_THEME + 1):
            if new_count >= batch_size:
                break
            page_url = f"{BASE_URL}/decision-theme/{theme}/" if page == 1 else f"{BASE_URL}/decision-theme/{theme}/page/{page}/"
            html = _get(page_url)
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            links = [a["href"] for a in soup.find_all("a", href=True) if "/decision/" in a["href"]]
            # dédoublonner en gardant l'ordre d'apparition
            seen_on_page = []
            for l in links:
                if l not in seen_on_page:
                    seen_on_page.append(l)
            if not seen_on_page:
                break

            for url in seen_on_page:
                if new_count >= batch_size:
                    break
                slug = url.rstrip("/").split("/")[-1]
                dest = OUTPUT_DIR / f"{slug[:100]}.txt"
                if dest.exists():
                    continue

                html_decision = _get(url)
                time.sleep(1.5)
                if not html_decision:
                    continue
                parsed = _parse_decision(html_decision)
                if not parsed:
                    continue

                dest.write_text(parsed["text"], encoding="utf-8")
                domain = _decision_domain(parsed["theme"])
                collected.append({
                    "domain": domain,
                    "source": "jurisprudence_ma",
                    "ref": parsed["ref"],
                    "url": url,
                    "local_path": str(dest),
                    "filename": parsed["title"],
                    "is_new": True,
                })
                new_count += 1

    logger.info(f"jurisprudence.ma : {new_count} nouvelle(s) décision(s) traitée(s).")
    return collected


if __name__ == "__main__":
    results = scrape_jurisprudence_ma(batch_size=10)
    logger.info(f"{len(results)} décisions collectées.")
