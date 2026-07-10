"""
Classifier — attribue un texte à un domaine juridique.
Approche légère : comptage de mots-clés (source unique : core.domains) avec
correspondance à limite de mot, + score de confiance.
"""
import re
from dataclasses import dataclass
from functools import lru_cache
from core.domains import DOMAIN_KEYWORDS


@dataclass
class ClassificationResult:
    domain: str
    confidence: float       # 0.0 à 1.0
    scores: dict            # score brut par domaine


@lru_cache(maxsize=1)
def _compiled_patterns() -> dict[str, list[re.Pattern]]:
    """
    Compile une regex à limite de mot (\\b) par mot-clé, une seule fois.
    Sans cette limite de mot, un mot-clé court comme "IS" ou "IR" matche par
    simple sous-chaîne à l'intérieur de mots français courants (ex. "préavis"
    contient "is", "secrétaire" contient "ir") et provoque un mauvais routage.
    """
    return {
        domain: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in keywords]
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }


def classify(text: str) -> ClassificationResult:
    """
    Classe un texte dans un domaine juridique.
    Retourne le domaine avec le score le plus élevé.
    """
    scores = {domain: sum(1 for p in patterns if p.search(text)) for domain, patterns in _compiled_patterns().items()}

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
        "Quel est le délai de préavis légal en cas de démission d'une secrétaire ?",  # ex-piège IS/IR
    ]
    for t in tests:
        r = classify(t)
        print(f"Domaine : {r.domain} | Confiance : {r.confidence:.0%} | Texte : {t[:60]}...")
