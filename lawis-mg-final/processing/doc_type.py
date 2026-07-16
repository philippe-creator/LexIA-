"""
Classification du type de document et extraction de l'année de publication,
à partir du nom de fichier — alimente les filtres avancés de recherche
(type de document, période).

Approche par motifs, cohérente avec retrieval/reference_search.py::classify_ref
qui applique une taxonomie similaire (loi/dahir/décret) sur une référence
saisie par l'utilisateur plutôt que sur un nom de fichier.
"""
import re

DOC_TYPES = ["loi", "dahir", "decret", "arrete", "circulaire", "jurisprudence", "autre"]

_PATTERNS = [
    ("dahir", r"dahir"),
    ("decret", r"d[ée]cret"),
    ("arrete", r"arr[êe]t[ée]"),
    ("circulaire", r"circulaire"),
    ("loi", r"\bloi\b|recueil"),
]

_YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


def classify_doc_type(filename: str, domain: str = None) -> str:
    """Classe un document par son nom de fichier. Le domaine 'jurisprudence'
    prime sur les motifs textuels (un arrêt de la Cour de cassation reste de
    la jurisprudence même si son nom de fichier contient "arrêté")."""
    if domain == "jurisprudence":
        return "jurisprudence"
    name = (filename or "").lower()
    for doc_type, pattern in _PATTERNS:
        if re.search(pattern, name):
            return doc_type
    return "autre"


def extract_year(filename: str) -> int | None:
    """Extrait une année plausible (19xx/20xx) du nom de fichier, si présente.
    Approximatif : ce n'est pas nécessairement la date de promulgation du
    texte, seulement une année mentionnée dans le nom du fichier source
    (souvent la date de mise à jour du recueil). Retourne None si absente —
    ne jamais inventer une année non trouvée."""
    if not filename:
        return None
    match = _YEAR_PATTERN.search(filename)
    return int(match.group()) if match else None
