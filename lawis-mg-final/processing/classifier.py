"""
Classifier — attribue un texte à un domaine juridique.
Approche légère : règles par mots-clés + score de confiance.
Peut être remplacé par un classifieur ML si besoin.
"""
import re
from dataclasses import dataclass

DOMAIN_KEYWORDS = {
    "travail": [
        "code du travail", "contrat de travail", "salarié", "employeur",
        "licenciement", "démission", "congé", "salaire", "SMIG", "SMAG",
        "syndicat", "grève", "CNSS", "sécurité sociale", "cotisation",
        "convention collective", "inspection du travail", "période d'essai",
        "indemnité de licenciement", "heures supplémentaires", "loi 65-99",
    ],
    "fiscal": [
        "code général des impôts", "CGI", "impôt sur les sociétés", "IS",
        "impôt sur le revenu", "IR", "TVA", "taxe sur la valeur ajoutée",
        "loi de finances", "direction générale des impôts", "DGI",
        "déclaration fiscale", "cotisation minimale", "note circulaire",
        "contribuable", "assiette fiscale", "exonération", "déduction",
        "redressement fiscal", "contrôle fiscal",
    ],
    "societes": [
        "société anonyme", "SA", "SARL", "société à responsabilité limitée",
        "SNC", "société en nom collectif", "capital social", "associé",
        "actionnaire", "assemblée générale", "conseil d'administration",
        "gérant", "commissaire aux comptes", "OMPIC", "registre de commerce",
        "loi 17-95", "loi 5-96", "fusion", "dissolution", "liquidation",
        "statuts", "objet social",
    ],
    "donnees_personnelles": [
        "données personnelles", "protection des données", "loi 09-08",
        "CNDP", "Commission Nationale", "traitement de données",
        "responsable du traitement", "consentement", "droit d'accès",
        "droit de rectification", "transfert de données", "vie privée",
        "données sensibles", "finalité du traitement", "déclaration CNDP",
    ],
}


@dataclass
class ClassificationResult:
    domain: str
    confidence: float       # 0.0 à 1.0
    scores: dict            # score brut par domaine


def classify(text: str) -> ClassificationResult:
    """
    Classe un texte dans un domaine juridique.
    Retourne le domaine avec le score le plus élevé.
    """
    text_lower = text.lower()
    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[domain] = count

    total = sum(scores.values())
    if total == 0:
        return ClassificationResult(domain="divers", confidence=0.0, scores=scores)

    best_domain = max(scores, key=scores.get)
    confidence = scores[best_domain] / total

    return ClassificationResult(
        domain=best_domain,
        confidence=round(confidence, 3),
        scores=scores,
    )


def classify_batch(texts: list[str]) -> list[ClassificationResult]:
    return [classify(t) for t in texts]


if __name__ == "__main__":
    tests = [
        "Le salarié a droit à une indemnité de licenciement après 5 ans d'ancienneté selon le code du travail.",
        "La TVA est fixée à 20% pour les prestations de services selon le CGI.",
        "La société anonyme doit disposer d'un capital minimum de 300 000 dirhams.",
        "Le responsable du traitement doit déclarer les traitements de données personnelles à la CNDP.",
    ]
    for t in tests:
        r = classify(t)
        print(f"Domaine : {r.domain} | Confiance : {r.confidence:.0%} | Texte : {t[:60]}...")
