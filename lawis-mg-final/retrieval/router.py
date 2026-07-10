"""
Router — identifie le(s) domaine(s) juridique(s) pertinent(s) pour une question.
Combine la classification par mots-clés et une détection d'intention simple.
"""
from processing.classifier import classify, DOMAIN_KEYWORDS
from loguru import logger

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

    # Confiance suffisante → cibler un domaine principal
    if result.confidence >= CONFIDENCE_THRESHOLD and result.domain != "divers":
        # Ajouter la jurisprudence du même domaine en complément
        domains = [result.domain]
        if result.domain in ["travail", "societes", "fiscal"]:
            domains.append("jurisprudence")
        return domains

    # Confiance faible → interroger tous les corpus (plus lent mais exhaustif)
    logger.info("Confiance faible — interrogation multi-corpus.")
    return ["travail", "societes", "fiscal", "donnees_personnelles", "jurisprudence"]


if __name__ == "__main__":
    queries = [
        "Quels sont les droits du salarié en cas de licenciement abusif ?",
        "Comment déclarer la TVA pour une SARL ?",
        "Quelles sont les obligations d'une société anonyme en matière de données personnelles ?",
        "Qu'est-ce qu'une assemblée générale ordinaire ?",
    ]
    for q in queries:
        domains = route_query(q)
        print(f"Q: {q[:60]}...\n→ Corpus ciblé(s) : {domains}\n")
