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

Multilingue (fr/en/ar) : le contenu de chaque modèle est un jeu de trois
gabarits parallèles écrits directement dans chaque langue — pas une traduction
automatique après génération. C'est ce qui préserve la garantie d'exactitude
factuelle (BNF-01) qui a motivé le choix originel de ne pas utiliser de LLM
pour ces documents : dates, noms et montants sont insérés tels quels, jamais
reformulés par un modèle. Le français reste la référence ; l'anglais et
l'arabe sont de vraies traductions juridiques, puisque ce sont des documents
que l'utilisateur peut signer ou soumettre.
"""

from datetime import date
import re

_LANGS = ("fr", "en", "ar")


def _lang(lang: str) -> str:
    return lang if lang in _LANGS else "fr"


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


_DISCLAIMER = {
    "fr": (
        "Document généré à titre indicatif par LexIA Maroc à partir d'une trame "
        "conforme au Code du travail (loi 65-99). À faire relire et adapter par un "
        "professionnel avant tout usage : conventions collectives, clauses "
        "particulières et situations spécifiques peuvent nécessiter des ajouts."
    ),
    "en": (
        "This document is generated for guidance purposes by LexIA Maroc based on "
        "a template compliant with the Labor Code (Law 65-99). It should be "
        "reviewed and adapted by a professional before use: collective agreements, "
        "specific clauses and particular situations may require additions."
    ),
    "ar": (
        "هذه الوثيقة مُولَّدة على سبيل الاستئناس من طرف LexIA Maroc اعتماداً على "
        "نموذج مطابق لمدونة الشغل (القانون 65.99). يجب مراجعتها وتكييفها من طرف "
        "مختص قبل أي استعمال: قد تستلزم اتفاقيات الشغل الجماعية والبنود الخاصة "
        "والحالات الخاصة إضافات معينة."
    ),
}

# Réponse "toujours en poste ?" acceptée comme vraie, toutes langues confondues
# (la valeur envoyée par le frontend dépend de la langue de l'option choisie).
_TRUTHY = ("oui", "true", "1", "yes", "نعم")


# ---------------------------------------------------------------------------
# Modèle 1 — Attestation de travail (article 72 du Code du travail)
# ---------------------------------------------------------------------------

def _build_attestation_travail(d: dict, lang: str = "fr") -> list:
    lang = _lang(lang)
    still = str(d.get("still_employed", "oui")).strip().lower() in _TRUTHY
    start = _fmt_date(_g(d, "start_date"))
    end = _fmt_date(_g(d, "end_date"))
    signatory_role = _g(d, "signatory_role", {"fr": "représentant légal", "en": "legal representative", "ar": "الممثل القانوني"}[lang])
    ice = _g(d, "company_ice", "")

    if lang == "en":
        ice_part = f", ICE No. {ice}" if ice else ""
        periode = f"He/She has held this position since {start} to date." if still else f"He/She held this position from {start} to {end}."
        return [
            _b("title", "EMPLOYMENT CERTIFICATE"),
            _b("spacer"),
            _b("body", f"I, the undersigned, {_g(d, 'signatory_name')}, acting in the capacity of {signatory_role} of the company {_g(d, 'company_name')}{ice_part}, hereby certify that:"),
            _b("spacer"),
            _b("body", f"Mr./Ms. {_g(d, 'employee_name')}, holder of national identity card No. {_g(d, 'employee_cin')}, has been employed within our company as {_g(d, 'job_title')}."),
            _b("body", periode),
            _b("spacer"),
            _b("body", "This certificate is issued to the person concerned for all legal purposes, in accordance with Article 72 of the Labor Code."),
            _b("spacer"),
            _b("body_right", f"Issued in {_g(d, 'city')}, on {_fmt_date(_g(d, 'doc_date'))}"),
            _b("spacer"),
            _b("body_right", "Employer's signature and stamp"),
        ]
    if lang == "ar":
        ice_part = f"، ICE رقم {ice}" if ice else ""
        periode = f"وهو/هي يشغل(تشغل) هذا المنصب منذ {start} إلى تاريخه." if still else f"وقد شغل(ت) هذا المنصب من {start} إلى {end}."
        return [
            _b("title", "شهادة عمل"),
            _b("spacer"),
            _b("body", f"أنا الموقع(ة) أدناه، {_g(d, 'signatory_name')}، بصفتي {signatory_role} بشركة {_g(d, 'company_name')}{ice_part}، أشهد بموجب هذه الوثيقة بما يلي:"),
            _b("spacer"),
            _b("body", f"أن السيد(ة) {_g(d, 'employee_name')}، حامل(ة) البطاقة الوطنية للتعريف رقم {_g(d, 'employee_cin')}، قد عمل(ت) لدى شركتنا بصفة {_g(d, 'job_title')}."),
            _b("body", periode),
            _b("spacer"),
            _b("body", "تُسلَّم هذه الشهادة للمعني(ة) بالأمر لتُستعمل عند الاقتضاء، طبقاً للمادة 72 من مدونة الشغل."),
            _b("spacer"),
            _b("body_right", f"حرر ب{_g(d, 'city')}، بتاريخ {_fmt_date(_g(d, 'doc_date'))}"),
            _b("spacer"),
            _b("body_right", "توقيع وخاتم المشغل"),
        ]
    # fr (défaut)
    ice_part = f", ICE n° {ice}" if ice else ""
    periode = f"Il/Elle est en poste depuis le {start} à ce jour." if still else f"Il/Elle a exercé ses fonctions du {start} au {end}."
    return [
        _b("title", "ATTESTATION DE TRAVAIL"),
        _b("spacer"),
        _b("body", f"Je soussigné(e), {_g(d, 'signatory_name')}, agissant en qualité de {signatory_role} de la société {_g(d, 'company_name')}{ice_part}, atteste par la présente que :"),
        _b("spacer"),
        _b("body", f"M./Mme {_g(d, 'employee_name')}, titulaire de la carte nationale d'identité n° {_g(d, 'employee_cin')}, a été employé(e) au sein de notre entreprise en qualité de {_g(d, 'job_title')}."),
        _b("body", periode),
        _b("spacer"),
        _b("body", "La présente attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit, conformément à l'article 72 du Code du travail."),
        _b("spacer"),
        _b("body_right", f"Fait à {_g(d, 'city')}, le {_fmt_date(_g(d, 'doc_date'))}"),
        _b("spacer"),
        _b("body_right", "Signature et cachet de l'employeur"),
    ]


# ---------------------------------------------------------------------------
# Modèle 2 — Mise en demeure pour salaire impayé
# ---------------------------------------------------------------------------

def _build_mise_en_demeure_salaire(d: dict, lang: str = "fr") -> list:
    lang = _lang(lang)
    montant = _money(d.get("amount_due", 0))
    delai = _g(d, "deadline_days", "8")
    doc_date = _fmt_date(_g(d, "doc_date"))

    if lang == "en":
        return [
            _b("body_right", _g(d, "sender_name")),
            _b("body_right", _g(d, "sender_address", "")),
            _b("spacer"),
            _b("body", f"To the attention of: {_g(d, 'recipient_name')}"),
            _b("body", _g(d, "recipient_address", "")),
            _b("spacer"),
            _b("body_right", f"{_g(d, 'city')}, {doc_date}"),
            _b("spacer"),
            _b("subtitle", "Subject: Formal notice to pay outstanding wages"),
            _b("body", "Registered letter with acknowledgment of receipt"),
            _b("spacer"),
            _b("body", "Dear Sir/Madam,"),
            _b("body", f"As an employee of your company, holding the position of {_g(d, 'job_title')}, I note that the wages relating to {_g(d, 'period_concerned')} remain unpaid to date, for a total amount of {montant} dirhams (MAD)."),
            _b("body", "However, the timely payment of wages constitutes a legal obligation of the employer under the provisions of the Labor Code (Law 65-99)."),
            _b("body", f"By this letter, I formally give you notice to pay the full amount owed, namely {montant} MAD, within {delai} days of receipt of this letter."),
            _b("body", "Failing payment within this period, I reserve the right to refer the matter to the labor inspectorate and to the competent court of first instance to assert my rights, without prejudice to any damages."),
            _b("body", "Awaiting your payment, please accept, Sir/Madam, the expression of my distinguished regards."),
            _b("spacer"),
            _b("body_right", _g(d, "sender_name")),
            _b("body_right", "(Signature)"),
        ]
    if lang == "ar":
        return [
            _b("body_right", _g(d, "sender_name")),
            _b("body_right", _g(d, "sender_address", "")),
            _b("spacer"),
            _b("body", f"إلى: {_g(d, 'recipient_name')}"),
            _b("body", _g(d, "recipient_address", "")),
            _b("spacer"),
            _b("body_right", f"{_g(d, 'city')}، بتاريخ {doc_date}"),
            _b("spacer"),
            _b("subtitle", "الموضوع: إنذار بأداء الأجور غير المؤداة"),
            _b("body", "رسالة مضمونة الوصول مع الإشعار بالتوصل"),
            _b("spacer"),
            _b("body", "السيدة/السيد المحترم(ة)،"),
            _b("body", f"بصفتي أجيراً(ة) لدى شركتكم، أشغل منصب {_g(d, 'job_title')}، ألاحظ أن الأجور المتعلقة ب{_g(d, 'period_concerned')} لا تزال غير مؤداة إلى حد الآن، وذلك بمبلغ إجمالي قدره {montant} درهم (MAD)."),
            _b("body", "وحيث إن أداء الأجر في أجله يشكل التزاماً قانونياً على عاتق المشغل بمقتضى أحكام مدونة الشغل (القانون 65.99)،"),
            _b("body", f"فإنني بموجب هذه الرسالة أنذركم بأداء كامل المبالغ المستحقة، أي {montant} درهم، داخل أجل {delai} يوماً من تاريخ التوصل بهذه الرسالة."),
            _b("body", "وفي حالة عدم الأداء داخل هذا الأجل، أحتفظ بحقي في اللجوء إلى مفتشية الشغل وكذا المحكمة الابتدائية المختصة للمطالبة بحقوقي، مع عدم الإخلال بالتعويضات المحتملة."),
            _b("body", "وفي انتظار أدائكم، تقبلوا مني، السيدة/السيد، فائق عبارات الاحترام والتقدير."),
            _b("spacer"),
            _b("body_right", _g(d, "sender_name")),
            _b("body_right", "(التوقيع)"),
        ]
    # fr
    return [
        _b("body_right", _g(d, "sender_name")),
        _b("body_right", _g(d, "sender_address", "")),
        _b("spacer"),
        _b("body", f"À l'attention de : {_g(d, 'recipient_name')}"),
        _b("body", _g(d, "recipient_address", "")),
        _b("spacer"),
        _b("body_right", f"{_g(d, 'city')}, le {doc_date}"),
        _b("spacer"),
        _b("subtitle", "Objet : Mise en demeure de payer les salaires impayés"),
        _b("body", "Lettre recommandée avec accusé de réception"),
        _b("spacer"),
        _b("body", "Madame, Monsieur,"),
        _b("body", f"En ma qualité de salarié(e) de votre entreprise, occupant le poste de {_g(d, 'job_title')}, je constate que les salaires afférents à {_g(d, 'period_concerned')} demeurent impayés à ce jour, pour un montant total de {montant} dirhams (MAD)."),
        _b("body", "Or, le paiement du salaire à son échéance constitue une obligation légale de l'employeur au regard des dispositions du Code du travail (loi 65-99)."),
        _b("body", f"Par la présente, je vous mets en demeure de me régler l'intégralité des sommes dues, soit {montant} MAD, dans un délai de {delai} jours à compter de la réception du présent courrier."),
        _b("body", "À défaut de règlement dans ce délai, je me réserve le droit de saisir l'inspection du travail ainsi que le tribunal de première instance compétent afin de faire valoir mes droits, sans préjudice des dommages et intérêts éventuels."),
        _b("body", "Dans l'attente de votre règlement, je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées."),
        _b("spacer"),
        _b("body_right", _g(d, "sender_name")),
        _b("body_right", "(Signature)"),
    ]


# ---------------------------------------------------------------------------
# Modèle 3 — Contrat de travail à durée indéterminée (CDI)
# ---------------------------------------------------------------------------

# Période d'essai légale — article 14 du Code du travail.
_TRIAL_PERIODS = {
    "fr": {"cadre": "trois (3) mois", "employe": "un mois et demi (1 mois et 15 jours)", "ouvrier": "quinze (15) jours"},
    "en": {"cadre": "three (3) months", "employe": "one and a half months (1 month and 15 days)", "ouvrier": "fifteen (15) days"},
    "ar": {"cadre": "ثلاثة (3) أشهر", "employe": "شهر ونصف (شهر و15 يوماً)", "ouvrier": "خمسة عشر (15) يوماً"},
}


def _build_cdi(d: dict, lang: str = "fr") -> list:
    lang = _lang(lang)
    ice = _g(d, "employer_ice", "")
    category = str(d.get("trial_category", "employe")).strip().lower()
    trial = _TRIAL_PERIODS[lang].get(category, _TRIAL_PERIODS[lang]["employe"])
    hours = _g(d, "weekly_hours", "44")
    money = _money(d.get("gross_salary", 0))
    doc_date = _fmt_date(_g(d, "doc_date"))
    start = _fmt_date(_g(d, "start_date"))

    if lang == "en":
        ice_part = f", ICE No. {ice}," if ice else ""
        return [
            _b("title", "PERMANENT EMPLOYMENT CONTRACT (CDI)"),
            _b("spacer"),
            _b("body", "Between the undersigned:"),
            _b("body", f"The company {_g(d, 'employer_name')}{ice_part} whose registered office is located at {_g(d, 'employer_address')}, represented by {_g(d, 'employer_repr')}, hereinafter referred to as \"the Employer\","),
            _b("body", "On the one hand,"),
            _b("body", f"And Mr./Ms. {_g(d, 'employee_name')}, holder of national ID card No. {_g(d, 'employee_cin')}, residing at {_g(d, 'employee_address')}, hereinafter referred to as \"the Employee\","),
            _b("body", "On the other hand,"),
            _b("body", "It has been agreed and decided as follows:"),
            _b("spacer"),
            _b("heading", "Article 1 — Hiring"),
            _b("body", f"The Employee is hired by the Employer as {_g(d, 'job_title')} effective {start}, under a permanent employment contract (CDI) governed by the Labor Code (Law 65-99)."),
            _b("heading", "Article 2 — Probationary period"),
            _b("body", f"This contract is concluded subject to a probationary period of {trial}, in accordance with Article 14 of the Labor Code, during which either party may terminate it under the legal conditions."),
            _b("heading", "Article 3 — Duties"),
            _b("body", f"The Employee shall perform the duties of {_g(d, 'job_title')} as well as any related tasks falling within their qualification, under the Employer's authority."),
            _b("heading", "Article 4 — Place of work"),
            _b("body", f"The duties shall be performed at {_g(d, 'workplace')}."),
            _b("heading", "Article 5 — Remuneration"),
            _b("body", f"In consideration of their work, the Employee shall receive a gross monthly salary of {money} dirhams (MAD), payable at the end of each month."),
            _b("heading", "Article 6 — Working hours"),
            _b("body", f"The weekly working time is set at {hours} hours, in accordance with Article 184 of the Labor Code."),
            _b("heading", "Article 7 — Paid leave"),
            _b("body", "The Employee is entitled to annual paid leave under the conditions provided for in Articles 231 et seq. of the Labor Code."),
            _b("heading", "Article 8 — Social protection"),
            _b("body", "The Employee shall be registered with the National Social Security Fund (CNSS) and shall benefit from compulsory health coverage (AMO)."),
            _b("heading", "Article 9 — Termination of contract"),
            _b("body", "This contract may be terminated by either party in accordance with the provisions of the Labor Code relating to notice (Article 51) and, where applicable, severance pay (Article 53)."),
            _b("heading", "Article 10 — General provisions"),
            _b("body", "For any matter not covered by this contract, the parties shall refer to the provisions of the Labor Code and applicable collective agreements."),
            _b("spacer"),
            _b("body", f"Made in {_g(d, 'city')}, on {doc_date}, in two original copies."),
            _b("spacer"),
            _b("body", "The Employer                                    The Employee"),
            _b("body", "                                               (read and approved)"),
        ]
    if lang == "ar":
        ice_part = f"، ICE رقم {ice}،" if ice else ""
        return [
            _b("title", "عقد عمل غير محدد المدة"),
            _b("spacer"),
            _b("body", "بين الموقعين أدناه:"),
            _b("body", f"شركة {_g(d, 'employer_name')}{ice_part} الكائن مقرها الاجتماعي ب{_g(d, 'employer_address')}، ممثلة من طرف {_g(d, 'employer_repr')}، ويشار إليها فيما يلي بـ«المشغل»،"),
            _b("body", "من جهة،"),
            _b("body", f"والسيد(ة) {_g(d, 'employee_name')}، حامل(ة) البطاقة الوطنية للتعريف رقم {_g(d, 'employee_cin')}، الساكن(ة) ب{_g(d, 'employee_address')}، ويشار إليه(ا) فيما يلي بـ«الأجير»،"),
            _b("body", "من جهة أخرى،"),
            _b("body", "اتفق الطرفان وتقرر ما يلي:"),
            _b("spacer"),
            _b("heading", "المادة 1 — التشغيل"),
            _b("body", f"يلتحق الأجير بالعمل لدى المشغل بصفة {_g(d, 'job_title')} ابتداءً من {start}، في إطار عقد عمل غير محدد المدة تحكمه مدونة الشغل (القانون 65.99)."),
            _b("heading", "المادة 2 — فترة الاختبار"),
            _b("body", f"يُبرم هذا العقد رهين فترة اختبار مدتها {trial}، طبقاً للمادة 14 من مدونة الشغل، يجوز خلالها لكل طرف إنهاء العقد وفق الشروط القانونية."),
            _b("heading", "المادة 3 — المهام"),
            _b("body", f"يمارس الأجير مهام {_g(d, 'job_title')} وكذا كل المهام المرتبطة بمؤهلاته، تحت سلطة المشغل."),
            _b("heading", "المادة 4 — مكان العمل"),
            _b("body", f"تُمارَس المهام ب{_g(d, 'workplace')}."),
            _b("heading", "المادة 5 — الأجرة"),
            _b("body", f"مقابل عمله، يتقاضى الأجير أجراً شهرياً إجمالياً قدره {money} درهم (MAD)، يُؤدى في نهاية كل شهر."),
            _b("heading", "المادة 6 — مدة الشغل"),
            _b("body", f"تُحدد المدة الأسبوعية للشغل في {hours} ساعة، طبقاً للمادة 184 من مدونة الشغل."),
            _b("heading", "المادة 7 — العطلة السنوية المؤدى عنها"),
            _b("body", "يستفيد الأجير من عطلة سنوية مؤدى عنها وفق الشروط المنصوص عليها في المادة 231 وما يليها من مدونة الشغل."),
            _b("heading", "المادة 8 — التغطية الاجتماعية"),
            _b("body", "يُسجَّل الأجير في الصندوق الوطني للضمان الاجتماعي (CNSS) ويستفيد من التغطية الصحية الإجبارية (AMO)."),
            _b("heading", "المادة 9 — إنهاء العقد"),
            _b("body", "يجوز إنهاء هذا العقد من طرف أي من الطرفين وفق مقتضيات مدونة الشغل المتعلقة بمهلة الإخطار (المادة 51) وكذا، عند الاقتضاء، تعويض الفصل (المادة 53)."),
            _b("heading", "المادة 10 — مقتضيات عامة"),
            _b("body", "بخصوص كل ما لم يُنص عليه في هذا العقد، يرجع الطرفان إلى مقتضيات مدونة الشغل واتفاقيات الشغل الجماعية المعمول بها."),
            _b("spacer"),
            _b("body", f"حرر ب{_g(d, 'city')}، بتاريخ {doc_date}، من نسختين أصليتين."),
            _b("spacer"),
            _b("body", "المشغل                                          الأجير"),
            _b("body", "                                               (قرئ ووافق عليه)"),
        ]
    # fr
    ice_part = f", ICE n° {ice}," if ice else ""
    return [
        _b("title", "CONTRAT DE TRAVAIL À DURÉE INDÉTERMINÉE"),
        _b("spacer"),
        _b("body", "Entre les soussignés :"),
        _b("body", f"La société {_g(d, 'employer_name')}{ice_part} dont le siège social est sis à {_g(d, 'employer_address')}, représentée par {_g(d, 'employer_repr')}, ci-après désignée « l'Employeur »,"),
        _b("body", "D'une part,"),
        _b("body", f"Et M./Mme {_g(d, 'employee_name')}, titulaire de la CIN n° {_g(d, 'employee_cin')}, demeurant à {_g(d, 'employee_address')}, ci-après désigné(e) « le Salarié »,"),
        _b("body", "D'autre part,"),
        _b("body", "Il a été convenu et arrêté ce qui suit :"),
        _b("spacer"),
        _b("heading", "Article 1 — Engagement"),
        _b("body", f"Le Salarié est engagé par l'Employeur en qualité de {_g(d, 'job_title')} à compter du {start}, dans le cadre d'un contrat de travail à durée indéterminée régi par le Code du travail (loi 65-99)."),
        _b("heading", "Article 2 — Période d'essai"),
        _b("body", f"Le présent contrat est conclu sous réserve d'une période d'essai de {trial}, conformément à l'article 14 du Code du travail, durant laquelle chacune des parties peut y mettre fin dans les conditions légales."),
        _b("heading", "Article 3 — Fonctions"),
        _b("body", f"Le Salarié exercera les fonctions de {_g(d, 'job_title')} ainsi que toutes tâches connexes relevant de sa qualification, sous l'autorité de l'Employeur."),
        _b("heading", "Article 4 — Lieu de travail"),
        _b("body", f"Les fonctions seront exercées à {_g(d, 'workplace')}."),
        _b("heading", "Article 5 — Rémunération"),
        _b("body", f"En contrepartie de son travail, le Salarié percevra un salaire mensuel brut de {money} dirhams (MAD), payable à la fin de chaque mois."),
        _b("heading", "Article 6 — Durée du travail"),
        _b("body", f"La durée hebdomadaire de travail est fixée à {hours} heures, conformément à l'article 184 du Code du travail."),
        _b("heading", "Article 7 — Congés payés"),
        _b("body", "Le Salarié bénéficie d'un congé annuel payé dans les conditions prévues par les articles 231 et suivants du Code du travail."),
        _b("heading", "Article 8 — Protection sociale"),
        _b("body", "Le Salarié sera immatriculé à la Caisse Nationale de Sécurité Sociale (CNSS) et bénéficiera de la couverture médicale obligatoire (AMO)."),
        _b("heading", "Article 9 — Rupture du contrat"),
        _b("body", "Le présent contrat pourra être rompu par l'une ou l'autre des parties dans le respect des dispositions du Code du travail relatives au préavis (article 51) et, le cas échéant, à l'indemnité de licenciement (article 53)."),
        _b("heading", "Article 10 — Dispositions générales"),
        _b("body", "Pour tout ce qui n'est pas prévu au présent contrat, les parties se réfèrent aux dispositions du Code du travail et aux conventions collectives applicables."),
        _b("spacer"),
        _b("body", f"Fait à {_g(d, 'city')}, le {doc_date}, en deux exemplaires originaux."),
        _b("spacer"),
        _b("body", "L'Employeur                                    Le Salarié"),
        _b("body", "                                               (lu et approuvé)"),
    ]


# ---------------------------------------------------------------------------
# Modèle 4 — Reçu pour solde de tout compte (articles 73 et 74)
# ---------------------------------------------------------------------------

def _build_solde_tout_compte(d: dict, lang: str = "fr") -> list:
    lang = _lang(lang)
    amount = _money(d.get("total_amount", 0))
    doc_date = _fmt_date(_g(d, "doc_date"))
    end = _fmt_date(_g(d, "end_date"))
    details = _g(d, "details", "")

    if lang == "en":
        blocks = [
            _b("title", "FINAL SETTLEMENT RECEIPT"),
            _b("spacer"),
            _b("body", f"I, the undersigned, {_g(d, 'employee_name')}, holder of national ID card No. {_g(d, 'employee_cin')}, having held the position of {_g(d, 'job_title')} within the company {_g(d, 'employer_name')} until {end},"),
            _b("body", f"acknowledge having received from my employer the sum of {amount} dirhams (MAD), as full and final settlement, for all amounts owed to me arising from the performance and termination of my employment contract (wages, paid leave allowance, notice allowance and severance pay where applicable)."),
        ]
        if details:
            blocks.append(_b("body", "Breakdown of amounts paid:"))
            blocks.append(_b("body", details))
        blocks += [
            _b("body", "This receipt is issued in accordance with Articles 73 and 74 of the Labor Code. It may be challenged within sixty (60) days of its signature."),
            _b("spacer"),
            _b("body", f"Made in {_g(d, 'city')}, on {doc_date}, in duplicate."),
            _b("spacer"),
            _b("body_right", "Employee's signature preceded by the handwritten note:"),
            _b("body_right", "\"Read and approved, good for final settlement\""),
        ]
        return blocks
    if lang == "ar":
        blocks = [
            _b("title", "وصل التصفية النهائية للحساب"),
            _b("spacer"),
            _b("body", f"أنا الموقع(ة) أدناه، {_g(d, 'employee_name')}، حامل(ة) البطاقة الوطنية للتعريف رقم {_g(d, 'employee_cin')}، وقد شغلت منصب {_g(d, 'job_title')} لدى شركة {_g(d, 'employer_name')} إلى غاية {end}،"),
            _b("body", f"أقر بأنني تسلمت من مشغلي مبلغاً قدره {amount} درهم (MAD)، وذلك على سبيل التصفية النهائية للحساب، عن جميع المبالغ المستحقة لي بمناسبة تنفيذ وإنهاء عقد عملي (الأجور، تعويض العطلة السنوية، تعويض الإخطار وتعويض الفصل عند الاقتضاء)."),
        ]
        if details:
            blocks.append(_b("body", "تفصيل المبالغ المؤداة:"))
            blocks.append(_b("body", details))
        blocks += [
            _b("body", "يُحرَّر هذا الوصل طبقاً للمادتين 73 و74 من مدونة الشغل. ويمكن الطعن فيه داخل أجل ستين (60) يوماً من تاريخ التوقيع عليه."),
            _b("spacer"),
            _b("body", f"حرر ب{_g(d, 'city')}، بتاريخ {doc_date}، من نسختين."),
            _b("spacer"),
            _b("body_right", "توقيع الأجير مسبوق بالعبارة المكتوبة بخط اليد:"),
            _b("body_right", "«قرئ ووافق عليه، جيد للتصفية النهائية للحساب»"),
        ]
        return blocks
    # fr
    blocks = [
        _b("title", "REÇU POUR SOLDE DE TOUT COMPTE"),
        _b("spacer"),
        _b("body", f"Je soussigné(e), {_g(d, 'employee_name')}, titulaire de la CIN n° {_g(d, 'employee_cin')}, ayant exercé les fonctions de {_g(d, 'job_title')} au sein de la société {_g(d, 'employer_name')} jusqu'au {end},"),
        _b("body", f"reconnais avoir reçu de mon employeur la somme de {amount} dirhams (MAD), pour solde de tout compte, au titre de l'ensemble des sommes qui m'étaient dues en raison de l'exécution et de la cessation de mon contrat de travail (salaires, indemnités de congés payés, de préavis et de licenciement le cas échéant)."),
    ]
    if details:
        blocks.append(_b("body", "Détail des sommes versées :"))
        blocks.append(_b("body", details))
    blocks += [
        _b("body", "Le présent reçu est établi conformément aux articles 73 et 74 du Code du travail. Il peut être dénoncé dans un délai de soixante (60) jours à compter de sa signature."),
        _b("spacer"),
        _b("body", f"Fait à {_g(d, 'city')}, le {doc_date}, en double exemplaire."),
        _b("spacer"),
        _b("body_right", "Signature du salarié précédée de la mention manuscrite :"),
        _b("body_right", "« Lu et approuvé, bon pour solde de tout compte »"),
    ]
    return blocks


# ---------------------------------------------------------------------------
# Registre des modèles — source unique pour l'API et le frontend.
# Structure langue-neutre : nom de champ, type, obligatoire, valeurs d'options
# (internes, stables). Tout le texte affiché (libellés, description, catégorie,
# référence légale, libellés d'options) vit dans _I18N, résolu à la demande.
# ---------------------------------------------------------------------------

def _f(name, type="text", required=True, options=None):
    field = {"name": name, "type": type, "required": required}
    if options:
        field["options"] = options
    return field


DOCUMENT_TYPES = {
    "attestation_travail": {
        "key": "attestation_travail",
        "fields": [
            _f("signatory_name"),
            _f("signatory_role", required=False),
            _f("company_name"),
            _f("company_ice", required=False),
            _f("employee_name"),
            _f("employee_cin"),
            _f("job_title"),
            _f("start_date", type="date"),
            _f("still_employed", type="select", options=["oui", "non"]),
            _f("end_date", type="date", required=False),
            _f("city"),
            _f("doc_date", type="date"),
        ],
        "build": _build_attestation_travail,
    },
    "mise_en_demeure_salaire": {
        "key": "mise_en_demeure_salaire",
        "fields": [
            _f("sender_name"),
            _f("sender_address", required=False),
            _f("recipient_name"),
            _f("recipient_address", required=False),
            _f("job_title"),
            _f("amount_due", type="number"),
            _f("period_concerned"),
            _f("deadline_days", type="number", required=False),
            _f("city"),
            _f("doc_date", type="date"),
        ],
        "build": _build_mise_en_demeure_salaire,
    },
    "cdi": {
        "key": "cdi",
        "fields": [
            _f("employer_name"),
            _f("employer_ice", required=False),
            _f("employer_repr"),
            _f("employer_address"),
            _f("employee_name"),
            _f("employee_cin"),
            _f("employee_address"),
            _f("job_title"),
            _f("start_date", type="date"),
            _f("gross_salary", type="number"),
            _f("weekly_hours", type="number", required=False),
            _f("trial_category", type="select", options=["cadre", "employe", "ouvrier"]),
            _f("workplace"),
            _f("city"),
            _f("doc_date", type="date"),
        ],
        "build": _build_cdi,
    },
    "solde_tout_compte": {
        "key": "solde_tout_compte",
        "fields": [
            _f("employee_name"),
            _f("employee_cin"),
            _f("job_title"),
            _f("employer_name"),
            _f("end_date", type="date"),
            _f("total_amount", type="number"),
            _f("details", type="textarea", required=False),
            _f("city"),
            _f("doc_date", type="date"),
        ],
        "build": _build_solde_tout_compte,
    },
}


# Métadonnées affichées (titre, description, catégorie, référence légale) par
# type de document et par langue.
_META = {
    "attestation_travail": {
        "fr": {"label": "Attestation de travail", "description": "Certificat attestant l'emploi d'un salarié (poste, période).", "category": "Emploi", "legal_reference": "Article 72 du Code du travail (loi 65-99)"},
        "en": {"label": "Employment Certificate", "description": "Certificate attesting to an employee's employment (position, period).", "category": "Employment", "legal_reference": "Article 72 of the Labor Code (Law 65-99)"},
        "ar": {"label": "شهادة عمل", "description": "شهادة تثبت تشغيل أجير (المنصب، الفترة).", "category": "التوظيف", "legal_reference": "المادة 72 من مدونة الشغل (القانون 65.99)"},
    },
    "mise_en_demeure_salaire": {
        "fr": {"label": "Mise en demeure — salaire impayé", "description": "Lettre de mise en demeure adressée à l'employeur pour salaires impayés.", "category": "Contentieux", "legal_reference": "Obligation de paiement du salaire — Code du travail (loi 65-99)"},
        "en": {"label": "Formal Notice — Unpaid Wages", "description": "Formal notice letter sent to the employer for unpaid wages.", "category": "Disputes", "legal_reference": "Obligation to pay wages — Labor Code (Law 65-99)"},
        "ar": {"label": "إنذار — أجر غير مؤدى", "description": "رسالة إنذار موجهة إلى المشغل بخصوص أجور غير مؤداة.", "category": "النزاعات", "legal_reference": "الالتزام بأداء الأجر — مدونة الشغل (القانون 65.99)"},
    },
    "cdi": {
        "fr": {"label": "Contrat de travail (CDI)", "description": "Contrat de travail à durée indéterminée conforme au Code du travail.", "category": "Emploi", "legal_reference": "Articles 14, 51, 53, 184, 231 du Code du travail (loi 65-99)"},
        "en": {"label": "Employment Contract (Permanent — CDI)", "description": "Permanent employment contract compliant with the Labor Code.", "category": "Employment", "legal_reference": "Articles 14, 51, 53, 184, 231 of the Labor Code (Law 65-99)"},
        "ar": {"label": "عقد عمل (غير محدد المدة)", "description": "عقد عمل غير محدد المدة مطابق لمدونة الشغل.", "category": "التوظيف", "legal_reference": "المواد 14 و51 و53 و184 و231 من مدونة الشغل (القانون 65.99)"},
    },
    "solde_tout_compte": {
        "fr": {"label": "Reçu pour solde de tout compte", "description": "Reçu signé par le salarié attestant le règlement de toutes les sommes dues.", "category": "Emploi", "legal_reference": "Articles 73 et 74 du Code du travail (loi 65-99)"},
        "en": {"label": "Final Settlement Receipt", "description": "Receipt signed by the employee acknowledging payment of all amounts owed.", "category": "Employment", "legal_reference": "Articles 73 and 74 of the Labor Code (Law 65-99)"},
        "ar": {"label": "وصل التصفية النهائية للحساب", "description": "وصل موقع من طرف الأجير يثبت أداء جميع المبالغ المستحقة له.", "category": "التوظيف", "legal_reference": "المادتان 73 و74 من مدونة الشغل (القانون 65.99)"},
    },
}

# Libellés et placeholders de champs par type de document / nom de champ / langue.
_FIELD_I18N = {
    "attestation_travail": {
        "signatory_name": {"fr": {"label": "Nom du signataire"}, "en": {"label": "Signatory's name"}, "ar": {"label": "اسم الموقع"}},
        "signatory_role": {"fr": {"label": "Qualité du signataire", "placeholder": "ex. Directeur des Ressources Humaines"}, "en": {"label": "Signatory's title", "placeholder": "e.g. HR Director"}, "ar": {"label": "صفة الموقع", "placeholder": "مثال: مدير الموارد البشرية"}},
        "company_name": {"fr": {"label": "Raison sociale de l'entreprise"}, "en": {"label": "Company name"}, "ar": {"label": "التسمية الاجتماعية للشركة"}},
        "company_ice": {"fr": {"label": "ICE de l'entreprise"}, "en": {"label": "Company ICE number"}, "ar": {"label": "السجل الموحد للمقاولة (ICE)"}},
        "employee_name": {"fr": {"label": "Nom du salarié"}, "en": {"label": "Employee's name"}, "ar": {"label": "اسم الأجير"}},
        "employee_cin": {"fr": {"label": "CIN du salarié"}, "en": {"label": "Employee's national ID (CIN)"}, "ar": {"label": "البطاقة الوطنية للأجير"}},
        "job_title": {"fr": {"label": "Poste occupé"}, "en": {"label": "Position held"}, "ar": {"label": "المنصب المشغول"}},
        "start_date": {"fr": {"label": "Date d'entrée"}, "en": {"label": "Start date"}, "ar": {"label": "تاريخ الالتحاق"}},
        "still_employed": {"fr": {"label": "Toujours en poste ?"}, "en": {"label": "Currently employed?"}, "ar": {"label": "لا يزال يشغل المنصب؟"}},
        "end_date": {"fr": {"label": "Date de sortie (si départ)"}, "en": {"label": "End date (if departed)"}, "ar": {"label": "تاريخ المغادرة (إن وجد)"}},
        "city": {"fr": {"label": "Ville"}, "en": {"label": "City"}, "ar": {"label": "المدينة"}},
        "doc_date": {"fr": {"label": "Date du document"}, "en": {"label": "Document date"}, "ar": {"label": "تاريخ الوثيقة"}},
    },
    "mise_en_demeure_salaire": {
        "sender_name": {"fr": {"label": "Votre nom (salarié)"}, "en": {"label": "Your name (employee)"}, "ar": {"label": "اسمك (الأجير)"}},
        "sender_address": {"fr": {"label": "Votre adresse"}, "en": {"label": "Your address"}, "ar": {"label": "عنوانك"}},
        "recipient_name": {"fr": {"label": "Nom / raison sociale de l'employeur"}, "en": {"label": "Employer's name / company name"}, "ar": {"label": "اسم / التسمية الاجتماعية للمشغل"}},
        "recipient_address": {"fr": {"label": "Adresse de l'employeur"}, "en": {"label": "Employer's address"}, "ar": {"label": "عنوان المشغل"}},
        "job_title": {"fr": {"label": "Votre poste"}, "en": {"label": "Your position"}, "ar": {"label": "منصبك"}},
        "amount_due": {"fr": {"label": "Montant dû (MAD)"}, "en": {"label": "Amount owed (MAD)"}, "ar": {"label": "المبلغ المستحق (درهم)"}},
        "period_concerned": {"fr": {"label": "Période concernée", "placeholder": "ex. les mois de janvier et février 2026"}, "en": {"label": "Period concerned", "placeholder": "e.g. January and February 2026"}, "ar": {"label": "الفترة المعنية", "placeholder": "مثال: شهري يناير وفبراير 2026"}},
        "deadline_days": {"fr": {"label": "Délai de règlement (jours)", "placeholder": "8"}, "en": {"label": "Payment deadline (days)", "placeholder": "8"}, "ar": {"label": "أجل الأداء (بالأيام)", "placeholder": "8"}},
        "city": {"fr": {"label": "Ville"}, "en": {"label": "City"}, "ar": {"label": "المدينة"}},
        "doc_date": {"fr": {"label": "Date"}, "en": {"label": "Date"}, "ar": {"label": "التاريخ"}},
    },
    "cdi": {
        "employer_name": {"fr": {"label": "Raison sociale de l'employeur"}, "en": {"label": "Employer's company name"}, "ar": {"label": "التسمية الاجتماعية للمشغل"}},
        "employer_ice": {"fr": {"label": "ICE de l'employeur"}, "en": {"label": "Employer's ICE number"}, "ar": {"label": "السجل الموحد للمشغل (ICE)"}},
        "employer_repr": {"fr": {"label": "Représenté par"}, "en": {"label": "Represented by"}, "ar": {"label": "ممثل من طرف"}},
        "employer_address": {"fr": {"label": "Siège social de l'employeur"}, "en": {"label": "Employer's registered office"}, "ar": {"label": "المقر الاجتماعي للمشغل"}},
        "employee_name": {"fr": {"label": "Nom du salarié"}, "en": {"label": "Employee's name"}, "ar": {"label": "اسم الأجير"}},
        "employee_cin": {"fr": {"label": "CIN du salarié"}, "en": {"label": "Employee's national ID (CIN)"}, "ar": {"label": "البطاقة الوطنية للأجير"}},
        "employee_address": {"fr": {"label": "Adresse du salarié"}, "en": {"label": "Employee's address"}, "ar": {"label": "عنوان الأجير"}},
        "job_title": {"fr": {"label": "Poste"}, "en": {"label": "Position"}, "ar": {"label": "المنصب"}},
        "start_date": {"fr": {"label": "Date de début"}, "en": {"label": "Start date"}, "ar": {"label": "تاريخ الالتحاق"}},
        "gross_salary": {"fr": {"label": "Salaire mensuel brut (MAD)"}, "en": {"label": "Gross monthly salary (MAD)"}, "ar": {"label": "الأجر الشهري الإجمالي (درهم)"}},
        "weekly_hours": {"fr": {"label": "Heures / semaine", "placeholder": "44"}, "en": {"label": "Hours / week", "placeholder": "44"}, "ar": {"label": "الساعات / الأسبوع", "placeholder": "44"}},
        "trial_category": {"fr": {"label": "Catégorie (période d'essai)"}, "en": {"label": "Category (probationary period)"}, "ar": {"label": "الفئة (فترة الاختبار)"}},
        "workplace": {"fr": {"label": "Lieu de travail"}, "en": {"label": "Place of work"}, "ar": {"label": "مكان العمل"}},
        "city": {"fr": {"label": "Ville de signature"}, "en": {"label": "City of signature"}, "ar": {"label": "مدينة التوقيع"}},
        "doc_date": {"fr": {"label": "Date de signature"}, "en": {"label": "Signature date"}, "ar": {"label": "تاريخ التوقيع"}},
    },
    "solde_tout_compte": {
        "employee_name": {"fr": {"label": "Nom du salarié"}, "en": {"label": "Employee's name"}, "ar": {"label": "اسم الأجير"}},
        "employee_cin": {"fr": {"label": "CIN du salarié"}, "en": {"label": "Employee's national ID (CIN)"}, "ar": {"label": "البطاقة الوطنية للأجير"}},
        "job_title": {"fr": {"label": "Poste occupé"}, "en": {"label": "Position held"}, "ar": {"label": "المنصب المشغول"}},
        "employer_name": {"fr": {"label": "Raison sociale de l'employeur"}, "en": {"label": "Employer's company name"}, "ar": {"label": "التسمية الاجتماعية للمشغل"}},
        "end_date": {"fr": {"label": "Date de fin du contrat"}, "en": {"label": "Contract end date"}, "ar": {"label": "تاريخ نهاية العقد"}},
        "total_amount": {"fr": {"label": "Montant total versé (MAD)"}, "en": {"label": "Total amount paid (MAD)"}, "ar": {"label": "المبلغ الإجمالي المؤدى (درهم)"}},
        "details": {"fr": {"label": "Détail des sommes (facultatif)"}, "en": {"label": "Breakdown of amounts (optional)"}, "ar": {"label": "تفصيل المبالغ (اختياري)"}},
        "city": {"fr": {"label": "Ville"}, "en": {"label": "City"}, "ar": {"label": "المدينة"}},
        "doc_date": {"fr": {"label": "Date"}, "en": {"label": "Date"}, "ar": {"label": "التاريخ"}},
    },
}

# Libellés des options de champs "select" (la valeur interne reste stable ;
# seul le libellé affiché change selon la langue).
_OPTION_I18N = {
    "attestation_travail": {
        "still_employed": {
            "oui": {"fr": "Oui", "en": "Yes", "ar": "نعم"},
            "non": {"fr": "Non", "en": "No", "ar": "لا"},
        },
    },
    "cdi": {
        "trial_category": {
            "cadre": {"fr": "Cadre", "en": "Executive", "ar": "إطار"},
            "employe": {"fr": "Employé", "en": "Employee", "ar": "مستخدم"},
            "ouvrier": {"fr": "Ouvrier", "en": "Worker", "ar": "عامل"},
        },
    },
}

_UNKNOWN_DOC_TYPE = {
    "fr": "Type de document inconnu : ",
    "en": "Unknown document type: ",
    "ar": "نوع وثيقة غير معروف: ",
}
_MISSING_FIELDS = {
    "fr": "Champs obligatoires manquants : ",
    "en": "Missing required fields: ",
    "ar": "حقول إلزامية ناقصة: ",
}


def list_document_types(lang: str = "fr") -> list:
    """Métadonnées des modèles (sans la fonction build) pour le frontend, localisées."""
    lang = _lang(lang)
    out = []
    for key, doc in DOCUMENT_TYPES.items():
        meta = _META[key][lang]
        field_i18n = _FIELD_I18N[key]
        option_i18n = _OPTION_I18N.get(key, {})
        fields = []
        for f in doc["fields"]:
            fi = field_i18n[f["name"]][lang]
            field = {"name": f["name"], "label": fi["label"], "type": f["type"], "required": f["required"]}
            if fi.get("placeholder"):
                field["placeholder"] = fi["placeholder"]
            if f.get("options"):
                opt_labels = option_i18n.get(f["name"], {})
                field["options"] = [
                    {"value": o, "label": opt_labels.get(o, {}).get(lang, o)}
                    for o in f["options"]
                ]
            fields.append(field)
        out.append({
            "key": key,
            "label": meta["label"],
            "description": meta["description"],
            "category": meta["category"],
            "legal_reference": meta["legal_reference"],
            "fields": fields,
        })
    return out


def build_document(doc_type: str, data: dict, lang: str = "fr") -> dict:
    """
    Construit un document à partir d'un modèle et des données saisies.
    Valide les champs obligatoires. Renvoie titre, blocs, référence légale.
    Lève ValueError si le type est inconnu ou si un champ requis manque.
    """
    lang = _lang(lang)
    doc = DOCUMENT_TYPES.get(doc_type)
    if not doc:
        raise ValueError(_UNKNOWN_DOC_TYPE[lang] + doc_type)

    data = data or {}
    field_i18n = _FIELD_I18N[doc_type]
    missing = [
        field_i18n[f["name"]][lang]["label"] for f in doc["fields"]
        if f.get("required") and str(data.get(f["name"], "")).strip() == ""
    ]
    if missing:
        raise ValueError(_MISSING_FIELDS[lang] + ", ".join(missing))

    blocks = doc["build"](data, lang)
    blocks = blocks + [_b("spacer"), _b("note", _DISCLAIMER[lang])]
    meta = _META[doc_type][lang]
    return {
        "doc_type": doc_type,
        "label": meta["label"],
        "title": next((b["text"] for b in blocks if b["style"] == "title"), meta["label"]),
        "legal_reference": meta["legal_reference"],
        "filename": f"{doc_type}_{date.today().isoformat()}",
        "lang": lang,
        "blocks": blocks,
    }
