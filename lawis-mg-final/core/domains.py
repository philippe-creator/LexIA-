"""
Registre unique des domaines juridiques couverts par la plateforme (BF-11 :
ajouter un domaine ne doit exiger de toucher qu'à ce fichier — BNF-04).

Toute couche (ingestion, processing, retrieval, api) doit importer la liste
des domaines et leurs métadonnées depuis ce module, jamais depuis un autre
module métier — c'est la racine neutre dont dépendent toutes les couches.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainInfo:
    slug: str
    label: str
    # Mots-clés utilisés par le classifieur pour router une question vers ce
    # domaine (correspondance par limite de mot — voir processing/classifier.py).
    keywords: tuple[str, ...] = field(default_factory=tuple)
    # Domaine juridique prioritaire du démonstrateur (cahier des charges §1.3).
    priority: bool = False


_REGISTRY: tuple[DomainInfo, ...] = (
    DomainInfo(
        slug="travail", label="Droit du travail", priority=True,
        keywords=(
            "code du travail", "contrat de travail", "salarié", "employeur",
            "licenciement", "démission", "congé", "salaire", "SMIG", "SMAG",
            "syndicat", "grève", "CNSS", "sécurité sociale", "cotisation",
            "convention collective", "inspection du travail", "période d'essai",
            "indemnité de licenciement", "heures supplémentaires", "loi 65-99",
        ),
    ),
    DomainInfo(
        slug="fiscal", label="Droit fiscal", priority=True,
        keywords=(
            "code général des impôts", "CGI", "impôt sur les sociétés",
            "impôt sur le revenu", "TVA", "taxe sur la valeur ajoutée",
            "loi de finances", "direction générale des impôts", "DGI",
            "déclaration fiscale", "cotisation minimale", "note circulaire",
            "contribuable", "assiette fiscale", "exonération", "déduction",
            "redressement fiscal", "contrôle fiscal",
        ),
    ),
    DomainInfo(
        slug="societes", label="Droit des sociétés", priority=True,
        keywords=(
            "société anonyme", "SARL", "société à responsabilité limitée",
            "SNC", "société en nom collectif", "capital social", "associé",
            "actionnaire", "assemblée générale", "conseil d'administration",
            "gérant", "commissaire aux comptes", "OMPIC", "registre de commerce",
            "loi 17-95", "loi 5-96", "fusion", "dissolution", "liquidation",
            "statuts", "objet social",
        ),
    ),
    DomainInfo(
        slug="donnees_personnelles", label="Protection des données personnelles", priority=True,
        keywords=(
            "données personnelles", "protection des données", "loi 09-08",
            "CNDP", "Commission Nationale", "traitement de données",
            "responsable du traitement", "consentement", "droit d'accès",
            "droit de rectification", "transfert de données", "vie privée",
            "données sensibles", "finalité du traitement", "déclaration CNDP",
        ),
    ),
    DomainInfo(slug="jurisprudence", label="Jurisprudence"),
    DomainInfo(slug="divers", label="Divers"),
)

DOMAINS: list[str] = [d.slug for d in _REGISTRY]
DOMAIN_LABELS: dict[str, str] = {d.slug: d.label for d in _REGISTRY}
DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {d.slug: d.keywords for d in _REGISTRY if d.keywords}
PRIORITY_DOMAINS: list[str] = [d.slug for d in _REGISTRY if d.priority]
# Domaines interrogés en complément d'un domaine principal à forte confiance
# (ex : une question "travail" bénéficie aussi de la jurisprudence sociale).
COMPANION_DOMAINS: dict[str, list[str]] = {d: ["jurisprudence"] for d in PRIORITY_DOMAINS}


def is_valid_domain(domain: str) -> bool:
    return domain in DOMAINS


def validate_domain(domain: str) -> str:
    if not is_valid_domain(domain):
        raise ValueError(f"Domaine invalide : {domain}")
    return domain
