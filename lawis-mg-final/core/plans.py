"""
Offres d'abonnement — source unique de vérité (comme core/domains.py).

Modèle « freemium simple » : une offre gratuite limitée en volume, une offre Pro
qui débloque le volume illimité et les fonctionnalités à forte valeur (audit de
contrat, génération de documents, export).

Le paiement n'est PAS encore branché : l'activation Pro passe aujourd'hui par un
point d'entrée « simulé » (voir api/routes/billing.py). Toute la mécanique —
offres, quotas, compteur d'usage, verrouillage des fonctionnalités — est en place
et prête à être reliée à Stripe ou CMI (Maroc) sans rien changer d'autre.
"""

# Clés de fonctionnalités verrouillables. Une offre déclare celles qu'elle ouvre.
FEATURE_CHAT = "chat"
FEATURE_CALCULATORS = "calculators"
FEATURE_REFERENCE = "reference"
FEATURE_COMPARE = "compare"
FEATURE_CONTRACT_AUDIT = "contract_audit"
FEATURE_LEGAL_DOCUMENTS = "legal_documents"
FEATURE_EXPORT = "export"

FEATURE_LABELS = {
    FEATURE_CHAT: "Assistant juridique",
    FEATURE_CALCULATORS: "Calculateurs juridiques",
    FEATURE_REFERENCE: "Recherche par référence",
    FEATURE_COMPARE: "Comparaison de versions",
    FEATURE_CONTRACT_AUDIT: "Audit de contrat",
    FEATURE_LEGAL_DOCUMENTS: "Génération de documents",
    FEATURE_EXPORT: "Export des conversations",
}

_FREE_FEATURES = {FEATURE_CHAT, FEATURE_CALCULATORS, FEATURE_REFERENCE, FEATURE_COMPARE}
_PRO_FEATURES = _FREE_FEATURES | {FEATURE_CONTRACT_AUDIT, FEATURE_LEGAL_DOCUMENTS, FEATURE_EXPORT}

# monthly_questions = None → illimité.
PLANS = {
    "free": {
        "key": "free",
        "label": "Gratuit",
        "price_mad": 0,
        "monthly_questions": 20,
        "features": _FREE_FEATURES,
        "tagline": "Pour découvrir le droit marocain au quotidien.",
        "highlights": [
            "20 questions par mois",
            "Réponses sourcées, citation des articles et pages",
            "Calculateurs (indemnités, préavis, salaire net)",
            "Recherche par référence et comparaison de versions",
        ],
    },
    "pro": {
        "key": "pro",
        "label": "Pro",
        "price_mad": 99,
        "monthly_questions": None,
        "features": _PRO_FEATURES,
        "tagline": "Pour les professionnels du droit et les entreprises.",
        "highlights": [
            "Questions illimitées",
            "Audit de contrat (rapport de conformité)",
            "Génération de documents juridiques (DOCX + PDF)",
            "Export des conversations (JSON + Word)",
            "Tout ce qui est inclus dans l'offre Gratuit",
        ],
    },
}

DEFAULT_PLAN = "free"


def get_plan(plan_key: str) -> dict:
    """Renvoie l'offre correspondante, ou l'offre gratuite si la clé est inconnue."""
    return PLANS.get(plan_key or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def plan_has_feature(plan_key: str, feature: str) -> bool:
    return feature in get_plan(plan_key)["features"]


def monthly_quota(plan_key: str) -> int | None:
    """Nombre de questions/mois de l'offre (None = illimité)."""
    return get_plan(plan_key)["monthly_questions"]


def list_plans_public() -> list:
    """Offres sérialisables (sets → listes) pour l'API / la page tarifs."""
    return [
        {**{k: v for k, v in p.items() if k != "features"},
         "features": sorted(p["features"])}
        for p in PLANS.values()
    ]
