"""
Router — identifie le(s) domaine(s) juridique(s) pertinent(s) pour une question.
Combine la classification par mots-clés et une détection d'intention simple.
"""
from loguru import logger
from processing.classifier import classify
from core.domains import PRIORITY_DOMAINS, COMPANION_DOMAINS

CONFIDENCE_THRESHOLD = 0.3   # en dessous : interroger tous les corpus


def route_query(query: str) -> list[str]:
    """
    Détermine le(s) corpus à interroger pour une question donnée.
    Retourne une liste de domaines ordonnée par pertinence décroissante.
    """
    result = classify(query)
    logger.info(
        f"Routage : domaine={result.domain} | confiance={result.confidence:.0%} | "
        f"scores={result.scores}"
    )

    # Confiance suffisante → cibler un domaine principal + ses domaines complémentaires
    if result.confidence >= CONFIDENCE_THRESHOLD and result.domain != "divers":
        domains = [result.domain]
        domains += [d for d in COMPANION_DOMAINS.get(result.domain, []) if d not in domains]
        return domains

    # Confiance faible → interroger tous les corpus prioritaires (plus lent mais exhaustif)
    logger.info("Confiance faible — interrogation multi-corpus.")
    return PRIORITY_DOMAINS + ["jurisprudence"]


if __name__ == "__main__":
    queries = [
        "Quels sont les droits du salarié en cas de licenciement abusif ?",
        "Comment déclarer la TVA pour une SARL ?",
        "Quelles sont les obligations d'une société anonyme en matière de données personnelles ?",
        "Qu'est-ce qu'une assemblée générale ordinaire ?",
        "Quel est le délai de préavis légal en cas de démission d'une secrétaire ?",
    ]
    for q in queries:
        domains = route_query(q)
        print(f"Q: {q[:60]}...\n→ Corpus ciblé(s) : {domains}\n")
