"""
Garde-fou anti-SSRF pour les scrapers : n'autorise à suivre que des liens
pointant vers le même domaine que la source de confiance (BASE_URL), pour
éviter qu'un lien injecté sur une page compromise ne redirige le scraper
vers une ressource interne/arbitraire.
"""
import hashlib
import os
from urllib.parse import urlparse

# Marge sous la limite de 255 octets par composant de chemin (ext4/NTFS) — une
# URL encodée (ex. titre arabe en %XX) peut largement dépasser cette limite
# une fois décodée en octets UTF-8, d'où la troncature ci-dessous.
_MAX_BASENAME_BYTES = 150


def same_origin(url: str, base_url: str) -> bool:
    try:
        return urlparse(url).netloc == urlparse(base_url).netloc
    except Exception:
        return False


def safe_filename(name: str) -> str:
    """Réduit un nom dérivé d'une URL à son composant final, sans séparateurs de chemin,
    et le tronque si besoin (avec un hash pour rester unique) pour respecter la limite
    de longueur de nom de fichier du système de fichiers."""
    name = os.path.basename(name.replace("\\", "/")) or "fichier"
    if len(name.encode("utf-8")) <= _MAX_BASENAME_BYTES:
        return name
    stem, ext = os.path.splitext(name)
    short_hash = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    budget = _MAX_BASENAME_BYTES - len(ext.encode("utf-8")) - len(short_hash) - 1
    truncated = stem.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
    return f"{truncated}_{short_hash}{ext}"
