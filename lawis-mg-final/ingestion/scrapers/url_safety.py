"""
Garde-fou anti-SSRF pour les scrapers : n'autorise à suivre que des liens
pointant vers le même domaine que la source de confiance (BASE_URL), pour
éviter qu'un lien injecté sur une page compromise ne redirige le scraper
vers une ressource interne/arbitraire.
"""
import os
from urllib.parse import urlparse


def same_origin(url: str, base_url: str) -> bool:
    try:
        return urlparse(url).netloc == urlparse(base_url).netloc
    except Exception:
        return False


def safe_filename(name: str) -> str:
    """Réduit un nom dérivé d'une URL à son composant final, sans séparateurs de chemin."""
    name = os.path.basename(name.replace("\\", "/"))
    return name or "fichier"
