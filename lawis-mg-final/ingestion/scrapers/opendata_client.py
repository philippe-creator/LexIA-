"""
Client API Open Data — data.gov.ma (CKAN)
Permet d'interroger et télécharger des datasets juridiques via l'API CKAN.
Doc : https://www.data.gov.ma/fr/guide-api
"""
import os
import json
import requests
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

API_URL = os.getenv("OPENDATA_API_URL", "https://www.data.gov.ma/data/api/3")
OUTPUT_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Mots-clés juridiques à rechercher dans le portail Open Data
LEGAL_KEYWORDS = [
    "droit travail", "code travail", "CNSS",
    "impôts", "fiscal", "taxe",
    "sociétés", "entreprise", "commerce",
    "données personnelles", "CNDP", "protection données",
    "bulletin officiel", "dahir", "réglementation",
    "jurisprudence",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def search_datasets(query: str, rows: int = 20) -> list[dict]:
    """Recherche des datasets via l'API CKAN."""
    url = f"{API_URL}/action/package_search"
    params = {"q": query, "rows": rows}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("success"):
        return data["result"]["results"]
    return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def get_dataset(dataset_id: str) -> dict | None:
    """Récupère les métadonnées complètes d'un dataset."""
    url = f"{API_URL}/action/package_show"
    resp = requests.get(url, headers=HEADERS, params={"id": dataset_id}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["result"] if data.get("success") else None


def download_resource(resource_url: str, dest: Path) -> bool:
    """Télécharge une ressource (CSV, PDF, JSON) depuis le portail."""
    if dest.exists():
        logger.debug(f"Existant : {dest.name}")
        return False
    resp = requests.get(resource_url, headers=HEADERS, timeout=30, stream=True)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.info(f"Téléchargé : {dest.name}")
    return True


def map_to_domain(title: str, notes: str) -> str:
    """Tente de mapper un dataset à un domaine juridique."""
    text = (title + " " + notes).lower()
    if any(k in text for k in ["travail", "emploi", "salarié", "cnss", "smig"]):
        return "travail"
    if any(k in text for k in ["impôt", "taxe", "fiscal", "cgi", "tva"]):
        return "fiscal"
    if any(k in text for k in ["société", "entreprise", "commerce", "ompic", "registre"]):
        return "societes"
    if any(k in text for k in ["données", "cndp", "privacy", "personnel"]):
        return "donnees_personnelles"
    return "divers"


def collect_legal_datasets() -> list[dict]:
    """
    Interroge l'API Open Data pour tous les mots-clés juridiques
    et télécharge les ressources pertinentes.
    """
    collected = []
    seen_ids = set()

    for keyword in LEGAL_KEYWORDS:
        logger.info(f"Recherche Open Data : '{keyword}'")
        datasets = search_datasets(keyword)

        for ds in datasets:
            if ds["id"] in seen_ids:
                continue
            seen_ids.add(ds["id"])

            domain = map_to_domain(ds.get("title", ""), ds.get("notes", ""))
            dest_dir = OUTPUT_DIR / domain / "opendata"
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Sauvegarder les métadonnées
            meta_file = dest_dir / f"{ds['id']}_meta.json"
            if not meta_file.exists():
                meta_file.write_text(
                    json.dumps(ds, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

            # Télécharger les ressources (CSV, PDF, etc.)
            for resource in ds.get("resources", []):
                res_url = resource.get("url", "")
                res_format = resource.get("format", "").lower()
                if not res_url or res_format not in ["csv", "pdf", "json", "xlsx"]:
                    continue

                filename = f"{ds['id']}_{resource['id'][:8]}.{res_format}"
                dest = dest_dir / filename

                try:
                    is_new = download_resource(res_url, dest)
                    collected.append({
                        "domain": domain,
                        "source": "opendata_gov",
                        "dataset_title": ds.get("title"),
                        "resource_name": resource.get("name"),
                        "format": res_format,
                        "url": res_url,
                        "local_path": str(dest),
                        "is_new": is_new,
                    })
                except Exception as e:
                    logger.warning(f"Ignoré {res_url} : {e}")

    logger.info(f"Open Data : {len(collected)} ressources collectées.")
    return collected


if __name__ == "__main__":
    collect_legal_datasets()
