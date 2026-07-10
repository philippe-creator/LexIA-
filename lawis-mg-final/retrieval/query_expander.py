import re
from loguru import logger

LEGAL_SYNONYMS = {
    "licenciement": ["rupture du contrat","résiliation","congédiement"],
    "salarié": ["employé","travailleur","agent"],
    "tva": ["taxe sur la valeur ajoutée"],
    "impôt": ["taxe","prélèvement fiscal","IS","IR"],
    "données personnelles": ["données à caractère personnel"],
    "consentement": ["accord","autorisation"],
    "amende": ["pénalité","sanction financière"],
}

LEGAL_EXPANSIONS = {
    "CGI": "Code Général des Impôts",
    "IS": "impôt sur les sociétés",
    "IR": "impôt sur le revenu",
    "TVA": "taxe sur la valeur ajoutée",
    "CNSS": "Caisse Nationale de Sécurité Sociale",
    "CNDP": "Commission Nationale de Protection des Données",
    "BO": "Bulletin Officiel",
    "SMIG": "Salaire Minimum Interprofessionnel Garanti",
}

def expand_query(query: str, max_variants: int = 3) -> list[str]:
    variants = [query]
    for abbr, full in LEGAL_EXPANSIONS.items():
        pattern = re.compile(r'\b' + re.escape(abbr) + r'\b', re.IGNORECASE)
        if pattern.search(query):
            new = pattern.sub(full, query)
            if new != query and new not in variants:
                variants.append(new)
    for term, synonyms in LEGAL_SYNONYMS.items():
        if term.lower() in query.lower():
            for syn in synonyms[:1]:
                v = re.sub(re.escape(term), syn, query, flags=re.IGNORECASE, count=1)
                if v not in variants: variants.append(v)
        if len(variants) >= max_variants + 1: break
    stop = {"quels","quelles","comment","que","qui","les","des","une","un","la","le","de","du","au","pour","sur","dans","est","par"}
    kw = " ".join(w for w in query.lower().split() if w not in stop and len(w) > 2)
    if kw and kw not in variants and kw != query.lower(): variants.append(kw)
    logger.debug(f"Query expansion: {len(variants)} variante(s)")
    return variants[:max_variants + 1]
