"""
Génération de documents juridiques — modèles déterministes (pas de LLM) fondés
sur le Code du travail marocain (loi 65-99). Chaque modèle référence les
articles applicables, conformément à BNF-01 (toute affirmation doit être
fondée).

Ces documents sont des trames indicatives : elles reprennent les mentions
légales usuelles mais ne remplacent pas la relecture d'un professionnel
(conventions collectives, régimes particuliers et clauses spécifiques peuvent
devoir être ajoutés). Un avertissement en ce sens est inséré dans chaque pièce.

Le module est pur (aucune I/O) : chaque modèle produit une liste de « blocs »
neutres — un format intermédiaire rendu ensuite en DOCX ou en PDF par la
couche API. On ne change pas la trame selon le format de sortie.
"""

from datetime import date
import re

# ---------------------------------------------------------------------------
# Format intermédiaire : un document = liste de blocs.
# style ∈ {title, subtitle, heading, body, body_center, body_right, spacer, note}
# ---------------------------------------------------------------------------

def _b(style, text=""):
    return {"style": style, "text": text}


def _fmt_date(value: str) -> str:
    """Normalise une date ISO (YYYY-MM-DD) en JJ/MM/AAAA ; sinon renvoie tel quel."""
    if not value:
        return "……………………"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return value.strip()


def _money(value) -> str:
    """Formate un montant en séparant les milliers par une espace : 12 500,00."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    entier, dec = f"{v:,.2f}".split(".")
    entier = entier.replace(",", " ")
    return f"{entier},{dec}"


def _g(data: dict, key: str, fallback: str = "……………………") -> str:
    """Valeur d'un champ, avec pointillés de remplissage si vide."""
    v = data.get(key)
    if v is None or str(v).strip() == "":
        return fallback
    return str(v).strip()


_DISCLAIMER = (
    "Document généré à titre indicatif par LexIA Maroc à partir d'une trame "
    "conforme au Code du travail (loi 65-99). À faire relire et adapter par un "
    "professionnel avant tout usage : conventions collectives, clauses "
    "particulières et situations spécifiques peuvent nécessiter des ajouts."
)


# ---------------------------------------------------------------------------
# Modèle 1 — Attestation de travail (article 72 du Code du travail)
# ---------------------------------------------------------------------------

def _build_attestation_travail(d: dict) -> list:
    ice = _g(d, "company_ice", "")
    ice_part = f", ICE n° {ice}" if ice else ""
    still = str(d.get("still_employed", "oui")).strip().lower() in ("oui", "true", "1", "yes")
    if still:
        periode = f"Il/Elle est en poste depuis le {_fmt_date(_g(d, 'start_date'))} à ce jour."
    else:
        periode = (
            f"Il/Elle a exercé ses fonctions du {_fmt_date(_g(d, 'start_date'))} "
            f"au {_fmt_date(_g(d, 'end_date'))}."
        )
    return [
        _b("title", "ATTESTATION DE TRAVAIL"),
        _b("spacer"),
        _b("body",
           f"Je soussigné(e), {_g(d, 'signatory_name')}, agissant en qualité de "
           f"{_g(d, 'signatory_role', 'représentant légal')} de la société "
           f"{_g(d, 'company_name')}{ice_part}, atteste par la présente que :"),
        _b("spacer"),
        _b("body",
           f"M./Mme {_g(d, 'employee_name')}, titulaire de la carte nationale "
           f"d'identité n° {_g(d, 'employee_cin')}, a été employé(e) au sein de "
           f"notre entreprise en qualité de {_g(d, 'job_title')}."),
        _b("body", periode),
        _b("spacer"),
        _b("body",
           "La présente attestation est délivrée à l'intéressé(e) pour servir et "
           "valoir ce que de droit, conformément à l'article 72 du Code du travail."),
        _b("spacer"),
        _b("body_right", f"Fait à {_g(d, 'city')}, le {_fmt_date(_g(d, 'doc_date'))}"),
        _b("spacer"),
        _b("body_right", "Signature et cachet de l'employeur"),
    ]


# ---------------------------------------------------------------------------
# Modèle 2 — Mise en demeure pour salaire impayé
# ---------------------------------------------------------------------------

def _build_mise_en_demeure_salaire(d: dict) -> list:
    montant = _money(d.get("amount_due", 0))
    delai = _g(d, "deadline_days", "8")
    return [
        _b("body_right", _g(d, "sender_name")),
        _b("body_right", _g(d, "sender_address", "")),
        _b("spacer"),
        _b("body", f"À l'attention de : {_g(d, 'recipient_name')}"),
        _b("body", _g(d, "recipient_address", "")),
        _b("spacer"),
        _b("body_right", f"{_g(d, 'city')}, le {_fmt_date(_g(d, 'doc_date'))}"),
        _b("spacer"),
        _b("subtitle",
           "Objet : Mise en demeure de payer les salaires impayés"),
        _b("body", "Lettre recommandée avec accusé de réception"),
        _b("spacer"),
        _b("body", "Madame, Monsieur,"),
        _b("body",
           f"En ma qualité de salarié(e) de votre entreprise, occupant le poste "
           f"de {_g(d, 'job_title')}, je constate que les salaires afférents à "
           f"{_g(d, 'period_concerned')} demeurent impayés à ce jour, pour un "
           f"montant total de {montant} dirhams (MAD)."),
        _b("body",
           "Or, le paiement du salaire à son échéance constitue une obligation "
           "légale de l'employeur au regard des dispositions du Code du travail "
           "(loi 65-99)."),
        _b("body",
           f"Par la présente, je vous mets en demeure de me régler l'intégralité "
           f"des sommes dues, soit {montant} MAD, dans un délai de {delai} jours "
           f"à compter de la réception du présent courrier."),
        _b("body",
           "À défaut de règlement dans ce délai, je me réserve le droit de saisir "
           "l'inspection du travail ainsi que le tribunal de première instance "
           "compétent afin de faire valoir mes droits, sans préjudice des "
           "dommages et intérêts éventuels."),
        _b("body",
           "Dans l'attente de votre règlement, je vous prie d'agréer, Madame, "
           "Monsieur, l'expression de mes salutations distinguées."),
        _b("spacer"),
        _b("body_right", _g(d, "sender_name")),
        _b("body_right", "(Signature)"),
    ]


# ---------------------------------------------------------------------------
# Modèle 3 — Contrat de travail à durée indéterminée (CDI)
# ---------------------------------------------------------------------------

# Période d'essai légale — article 14 du Code du travail.
_TRIAL_PERIODS = {
    "cadre": "trois (3) mois",
    "employe": "un mois et demi (1 mois et 15 jours)",
    "ouvrier": "quinze (15) jours",
}


def _build_cdi(d: dict) -> list:
    ice = _g(d, "employer_ice", "")
    ice_part = f", ICE n° {ice}," if ice else ""
    trial = _TRIAL_PERIODS.get(str(d.get("trial_category", "employe")).strip().lower(),
                               _TRIAL_PERIODS["employe"])
    hours = _g(d, "weekly_hours", "44")
    return [
        _b("title", "CONTRAT DE TRAVAIL À DURÉE INDÉTERMINÉE"),
        _b("spacer"),
        _b("body", "Entre les soussignés :"),
        _b("body",
           f"La société {_g(d, 'employer_name')}{ice_part} dont le siège social "
           f"est sis à {_g(d, 'employer_address')}, représentée par "
           f"{_g(d, 'employer_repr')}, ci-après désignée « l'Employeur »,"),
        _b("body", "D'une part,"),
        _b("body",
           f"Et M./Mme {_g(d, 'employee_name')}, titulaire de la CIN n° "
           f"{_g(d, 'employee_cin')}, demeurant à {_g(d, 'employee_address')}, "
           f"ci-après désigné(e) « le Salarié »,"),
        _b("body", "D'autre part,"),
        _b("body", "Il a été convenu et arrêté ce qui suit :"),
        _b("spacer"),
        _b("heading", "Article 1 — Engagement"),
        _b("body",
           f"Le Salarié est engagé par l'Employeur en qualité de "
           f"{_g(d, 'job_title')} à compter du {_fmt_date(_g(d, 'start_date'))}, "
           f"dans le cadre d'un contrat de travail à durée indéterminée régi par "
           f"le Code du travail (loi 65-99)."),
        _b("heading", "Article 2 — Période d'essai"),
        _b("body",
           f"Le présent contrat est conclu sous réserve d'une période d'essai de "
           f"{trial}, conformément à l'article 14 du Code du travail, durant "
           f"laquelle chacune des parties peut y mettre fin dans les conditions "
           f"légales."),
        _b("heading", "Article 3 — Fonctions"),
        _b("body",
           f"Le Salarié exercera les fonctions de {_g(d, 'job_title')} ainsi que "
           f"toutes tâches connexes relevant de sa qualification, sous l'autorité "
           f"de l'Employeur."),
        _b("heading", "Article 4 — Lieu de travail"),
        _b("body", f"Les fonctions seront exercées à {_g(d, 'workplace')}."),
        _b("heading", "Article 5 — Rémunération"),
        _b("body",
           f"En contrepartie de son travail, le Salarié percevra un salaire "
           f"mensuel brut de {_money(d.get('gross_salary', 0))} dirhams (MAD), "
           f"payable à la fin de chaque mois."),
        _b("heading", "Article 6 — Durée du travail"),
        _b("body",
           f"La durée hebdomadaire de travail est fixée à {hours} heures, "
           f"conformément à l'article 184 du Code du travail."),
        _b("heading", "Article 7 — Congés payés"),
        _b("body",
           "Le Salarié bénéficie d'un congé annuel payé dans les conditions "
           "prévues par les articles 231 et suivants du Code du travail."),
        _b("heading", "Article 8 — Protection sociale"),
        _b("body",
           "Le Salarié sera immatriculé à la Caisse Nationale de Sécurité "
           "Sociale (CNSS) et bénéficiera de la couverture médicale obligatoire "
           "(AMO)."),
        _b("heading", "Article 9 — Rupture du contrat"),
        _b("body",
           "Le présent contrat pourra être rompu par l'une ou l'autre des "
           "parties dans le respect des dispositions du Code du travail relatives "
           "au préavis (article 51) et, le cas échéant, à l'indemnité de "
           "licenciement (article 53)."),
        _b("heading", "Article 10 — Dispositions générales"),
        _b("body",
           "Pour tout ce qui n'est pas prévu au présent contrat, les parties se "
           "réfèrent aux dispositions du Code du travail et aux conventions "
           "collectives applicables."),
        _b("spacer"),
        _b("body",
           f"Fait à {_g(d, 'city')}, le {_fmt_date(_g(d, 'doc_date'))}, en deux "
           f"exemplaires originaux."),
        _b("spacer"),
        _b("body", "L'Employeur                                    Le Salarié"),
        _b("body", "                                               (lu et approuvé)"),
    ]


# ---------------------------------------------------------------------------
# Modèle 4 — Reçu pour solde de tout compte (articles 73 et 74)
# ---------------------------------------------------------------------------

def _build_solde_tout_compte(d: dict) -> list:
    blocks = [
        _b("title", "REÇU POUR SOLDE DE TOUT COMPTE"),
        _b("spacer"),
        _b("body",
           f"Je soussigné(e), {_g(d, 'employee_name')}, titulaire de la CIN n° "
           f"{_g(d, 'employee_cin')}, ayant exercé les fonctions de "
           f"{_g(d, 'job_title')} au sein de la société {_g(d, 'employer_name')} "
           f"jusqu'au {_fmt_date(_g(d, 'end_date'))},"),
        _b("body",
           f"reconnais avoir reçu de mon employeur la somme de "
           f"{_money(d.get('total_amount', 0))} dirhams (MAD), pour solde de tout "
           f"compte, au titre de l'ensemble des sommes qui m'étaient dues en "
           f"raison de l'exécution et de la cessation de mon contrat de travail "
           f"(salaires, indemnités de congés payés, de préavis et de "
           f"licenciement le cas échéant)."),
    ]
    details = _g(d, "details", "")
    if details:
        blocks.append(_b("body", "Détail des sommes versées :"))
        blocks.append(_b("body", details))
    blocks += [
        _b("body",
           "Le présent reçu est établi conformément aux articles 73 et 74 du Code "
           "du travail. Il peut être dénoncé dans un délai de soixante (60) jours "
           "à compter de sa signature."),
        _b("spacer"),
        _b("body",
           f"Fait à {_g(d, 'city')}, le {_fmt_date(_g(d, 'doc_date'))}, en double "
           f"exemplaire."),
        _b("spacer"),
        _b("body_right",
           "Signature du salarié précédée de la mention manuscrite :"),
        _b("body_right", "« Lu et approuvé, bon pour solde de tout compte »"),
    ]
    return blocks


# ---------------------------------------------------------------------------
# Registre des modèles — source unique pour l'API et le frontend.
# Chaque champ : name, label, type (text|date|number|textarea|select), required,
# options (pour select), placeholder.
# ---------------------------------------------------------------------------

def _f(name, label, type="text", required=True, options=None, placeholder=""):
    field = {"name": name, "label": label, "type": type, "required": required}
    if options:
        field["options"] = options
    if placeholder:
        field["placeholder"] = placeholder
    return field


DOCUMENT_TYPES = {
    "attestation_travail": {
        "key": "attestation_travail",
        "label": "Attestation de travail",
        "description": "Certificat attestant l'emploi d'un salarié (poste, période).",
        "category": "Emploi",
        "legal_reference": "Article 72 du Code du travail (loi 65-99)",
        "fields": [
            _f("signatory_name", "Nom du signataire"),
            _f("signatory_role", "Qualité du signataire", required=False,
               placeholder="ex. Directeur des Ressources Humaines"),
            _f("company_name", "Raison sociale de l'entreprise"),
            _f("company_ice", "ICE de l'entreprise", required=False),
            _f("employee_name", "Nom du salarié"),
            _f("employee_cin", "CIN du salarié"),
            _f("job_title", "Poste occupé"),
            _f("start_date", "Date d'entrée", type="date"),
            _f("still_employed", "Toujours en poste ?", type="select",
               options=["oui", "non"]),
            _f("end_date", "Date de sortie (si départ)", type="date", required=False),
            _f("city", "Ville"),
            _f("doc_date", "Date du document", type="date"),
        ],
        "build": _build_attestation_travail,
    },
    "mise_en_demeure_salaire": {
        "key": "mise_en_demeure_salaire",
        "label": "Mise en demeure — salaire impayé",
        "description": "Lettre de mise en demeure adressée à l'employeur pour salaires impayés.",
        "category": "Contentieux",
        "legal_reference": "Obligation de paiement du salaire — Code du travail (loi 65-99)",
        "fields": [
            _f("sender_name", "Votre nom (salarié)"),
            _f("sender_address", "Votre adresse", required=False),
            _f("recipient_name", "Nom / raison sociale de l'employeur"),
            _f("recipient_address", "Adresse de l'employeur", required=False),
            _f("job_title", "Votre poste"),
            _f("amount_due", "Montant dû (MAD)", type="number"),
            _f("period_concerned", "Période concernée",
               placeholder="ex. les mois de janvier et février 2026"),
            _f("deadline_days", "Délai de règlement (jours)", type="number",
               required=False, placeholder="8"),
            _f("city", "Ville"),
            _f("doc_date", "Date", type="date"),
        ],
        "build": _build_mise_en_demeure_salaire,
    },
    "cdi": {
        "key": "cdi",
        "label": "Contrat de travail (CDI)",
        "description": "Contrat de travail à durée indéterminée conforme au Code du travail.",
        "category": "Emploi",
        "legal_reference": "Articles 14, 51, 53, 184, 231 du Code du travail (loi 65-99)",
        "fields": [
            _f("employer_name", "Raison sociale de l'employeur"),
            _f("employer_ice", "ICE de l'employeur", required=False),
            _f("employer_repr", "Représenté par"),
            _f("employer_address", "Siège social de l'employeur"),
            _f("employee_name", "Nom du salarié"),
            _f("employee_cin", "CIN du salarié"),
            _f("employee_address", "Adresse du salarié"),
            _f("job_title", "Poste"),
            _f("start_date", "Date de début", type="date"),
            _f("gross_salary", "Salaire mensuel brut (MAD)", type="number"),
            _f("weekly_hours", "Heures / semaine", type="number", required=False,
               placeholder="44"),
            _f("trial_category", "Catégorie (période d'essai)", type="select",
               options=["cadre", "employe", "ouvrier"]),
            _f("workplace", "Lieu de travail"),
            _f("city", "Ville de signature"),
            _f("doc_date", "Date de signature", type="date"),
        ],
        "build": _build_cdi,
    },
    "solde_tout_compte": {
        "key": "solde_tout_compte",
        "label": "Reçu pour solde de tout compte",
        "description": "Reçu signé par le salarié attestant le règlement de toutes les sommes dues.",
        "category": "Emploi",
        "legal_reference": "Articles 73 et 74 du Code du travail (loi 65-99)",
        "fields": [
            _f("employee_name", "Nom du salarié"),
            _f("employee_cin", "CIN du salarié"),
            _f("job_title", "Poste occupé"),
            _f("employer_name", "Raison sociale de l'employeur"),
            _f("end_date", "Date de fin du contrat", type="date"),
            _f("total_amount", "Montant total versé (MAD)", type="number"),
            _f("details", "Détail des sommes (facultatif)", type="textarea",
               required=False),
            _f("city", "Ville"),
            _f("doc_date", "Date", type="date"),
        ],
        "build": _build_solde_tout_compte,
    },
}


def list_document_types() -> list:
    """Métadonnées des modèles (sans la fonction build) pour le frontend."""
    return [
        {k: v for k, v in doc.items() if k != "build"}
        for doc in DOCUMENT_TYPES.values()
    ]


def build_document(doc_type: str, data: dict) -> dict:
    """
    Construit un document à partir d'un modèle et des données saisies.
    Valide les champs obligatoires. Renvoie titre, blocs, référence légale.
    Lève ValueError si le type est inconnu ou si un champ requis manque.
    """
    doc = DOCUMENT_TYPES.get(doc_type)
    if not doc:
        raise ValueError(f"Type de document inconnu : {doc_type}")

    data = data or {}
    missing = [
        f["label"] for f in doc["fields"]
        if f.get("required") and str(data.get(f["name"], "")).strip() == ""
    ]
    if missing:
        raise ValueError("Champs obligatoires manquants : " + ", ".join(missing))

    blocks = doc["build"](data)
    blocks = blocks + [_b("spacer"), _b("note", _DISCLAIMER)]
    return {
        "doc_type": doc_type,
        "label": doc["label"],
        "title": next((b["text"] for b in blocks if b["style"] == "title"), doc["label"]),
        "legal_reference": doc["legal_reference"],
        "filename": f"{doc_type}_{date.today().isoformat()}",
        "blocks": blocks,
    }
