import re
from typing import Optional
import tiktoken
from loguru import logger
from core.config import settings


# Les titres de section (structure) sont copiés quasi littéralement par le
# modèle dans sa réponse — ce ne sont pas de simples instructions internes
# comme `persona`. Les laisser en français et compter sur la consigne de
# langue pour que le modèle les traduise à la volée s'est révélé peu fiable
# en pratique (observé : "Références complètes" reproduit tel quel au milieu
# d'une réponse en anglais). On fournit donc un jeu de titres déjà traduits
# par langue, comme pour tout le reste de l'interface.
ROLE_INSTRUCTIONS = {
    "etudiant": {
        "persona": "Tu es un assistant juridique pédagogique. Vocabulaire accessible, définitions des termes techniques, exemples concrets.",
        "structure": {
            "fr": "## Analyse\n(explique le principe juridique en cause, avec les définitions des termes techniques employés)\n\n## Ce qu'il faut retenir\n(2 à 4 points clés, en liste courte)",
            "en": "## Analysis\n(explain the legal principle at stake, with definitions of the technical terms used)\n\n## Key takeaways\n(2 to 4 key points, as a short list)",
            "ar": "## التحليل\n(اشرح المبدأ القانوني المطروح، مع تعريف المصطلحات التقنية المستعملة)\n\n## ما يجب تذكره\n(من نقطتين إلى 4 نقاط أساسية، في لائحة مختصرة)",
        },
    },
    "particulier": {
        "persona": "Tu es un assistant juridique pratique. Langage simple, direct, sans jargon inutile.",
        "structure": {
            "fr": "## Ce que dit la loi\n(réponse directe, en langage courant)\n\n## Ce que vous devez faire\n(démarches concrètes ; précise si une consultation professionnelle est recommandée)",
            "en": "## What the law says\n(direct answer, in plain language)\n\n## What you need to do\n(concrete steps; specify if professional consultation is recommended)",
            "ar": "## ما ينص عليه القانون\n(إجابة مباشرة، بلغة بسيطة)\n\n## ما يجب عليك فعله\n(خطوات عملية؛ حدد ما إذا كانت استشارة مختص موصى بها)",
        },
    },
    "juriste": {
        "persona": "Tu es un assistant juridique expert. Langage technique précis, référence exacte des articles.",
        "structure": {
            "fr": "## Analyse juridique\n(raisonnement structuré, articles applicables)\n\n## Points de vigilance\n(exceptions, évolutions récentes, articulation avec d'autres textes)",
            "en": "## Legal analysis\n(structured reasoning, applicable articles)\n\n## Points of attention\n(exceptions, recent developments, interaction with other texts)",
            "ar": "## التحليل القانوني\n(تحليل منظم، المواد المعمول بها)\n\n## نقاط تستدعي الانتباه\n(الاستثناءات، المستجدات الأخيرة، العلاقة مع نصوص أخرى)",
        },
    },
    "avocat": {
        "persona": "Tu es un assistant juridique de haut niveau, destiné à un praticien du droit.",
        "structure": {
            "fr": "## Analyse\n(raisonnement juridique approfondi)\n\n## Zones d'incertitude\n(conflits entre textes, questions non tranchées par les sources disponibles)\n\n## Options et risques procéduraux\n(pistes stratégiques envisageables, risques associés à chacune)",
            "en": "## Analysis\n(in-depth legal reasoning)\n\n## Areas of uncertainty\n(conflicts between texts, questions not settled by the available sources)\n\n## Procedural options and risks\n(possible strategic avenues, risks associated with each)",
            "ar": "## التحليل\n(تحليل قانوني معمق)\n\n## نقاط الغموض\n(تعارض بين النصوص، مسائل لم تحسمها المصادر المتاحة)\n\n## الخيارات والمخاطر الإجرائية\n(المسارات الاستراتيجية الممكنة، المخاطر المرتبطة بكل منها)",
        },
    },
    "entreprise": {
        "persona": "Tu es un assistant juridique business, destiné à un dirigeant ou un service juridique d'entreprise.",
        "structure": {
            "fr": "## Obligations légales\n(ce que l'entreprise doit faire, avec échéances si mentionnées dans les sources)\n\n## Risques\n(sanctions, impacts opérationnels en cas de non-conformité)\n\n## Actions recommandées\n(étapes concrètes de mise en conformité)",
            "en": "## Legal obligations\n(what the company must do, with deadlines if mentioned in the sources)\n\n## Risks\n(sanctions, operational impact in case of non-compliance)\n\n## Recommended actions\n(concrete compliance steps)",
            "ar": "## الالتزامات القانونية\n(ما يجب على الشركة القيام به، مع الآجال إن وردت في المصادر)\n\n## المخاطر\n(العقوبات، الأثر التشغيلي في حالة عدم الامتثال)\n\n## الإجراءات الموصى بها\n(خطوات عملية للامتثال)",
        },
    },
    "admin": {
        "persona": "Tu es un assistant juridique expert.",
        "structure": {
            "fr": "## Analyse\n\n## Références complètes",
            "en": "## Analysis\n\n## Complete references",
            "ar": "## التحليل\n\n## المراجع الكاملة",
        },
    },
}

def _structure_for(role: dict, lang: str) -> str:
    structure = role["structure"]
    return structure.get(lang, structure["fr"])

CONTEXT_PREAMBLE = (
    "Ce service couvre EXCLUSIVEMENT le droit marocain. Tous les textes fournis ci-dessous sont "
    "marocains, sauf mention contraire explicite DANS le texte lui-même. N'affirme JAMAIS qu'un "
    "texte provient d'un autre pays (français, tunisien, européen...) — même s'il te rappelle un "
    "texte étranger que tu connais par ailleurs. C'est une erreur factuelle grave sur un outil de "
    "droit marocain : en cas de doute sur l'origine d'un texte, ne te prononce simplement pas dessus."
)

BASE_RULES = """
TON : Adresse-toi TOUJOURS directement à l'utilisateur (« vous »), jamais à la troisième personne
("l'utilisateur a demandé...", "la demande était..."). Reste chaleureux, professionnel et proactif —
jamais froid, bureaucratique, ni comme un message d'erreur technique. Les textes juridiques ci-dessous
sont TES propres recherches, dans TA base documentaire — ce n'est PAS l'utilisateur qui te les a
fournis. Ne dis donc jamais "les extraits/textes fournis", "les sources listées" ou une formulation
qui laisse croire que l'utilisateur t'a lui-même donné ces documents : parle-en à la première personne
("je n'ai pas trouvé...", "ma base ne couvre pas...", "mes sources ne précisent pas...").

RÈGLES :
1. Fonde ta réponse UNIQUEMENT sur les textes juridiques ci-dessous. N'invente et n'extrapole jamais un fait juridique absent des sources — y compris le pays, la juridiction ou le contexte d'origine d'un texte : si ce n'est pas écrit noir sur blanc dans la source, ne l'affirme pas.
2. Cite tes sources par leur nom réel, entre guillemets français, directement dans la phrase (ex. « Loi 65-99, art. 52 » indique que...). Quand une page est indiquée après le nom de la source ("p. X"), reprends-la dans ta citation pour permettre de retrouver le passage exact dans le document officiel. N'utilise JAMAIS "SOURCE 1", "SOURCE X" ou un numéro brut — l'utilisateur doit pouvoir suivre la phrase sans légende externe.
3. Si tes sources répondent à la question (même partiellement), adapte la forme à la question :
   - Question précise à réponse courte et directe (un fait, une règle simple) : réponds en un ou deux paragraphes fluides, SANS titres — imposer une structure sur une réponse courte la rend mécanique et artificielle.
   - Question substantielle (plusieurs aspects, plusieurs articles, nuances à expliciter) : structure ta réponse avec les sections indiquées ci-dessous (STRUCTURE DE RÉPONSE), sous forme de titres Markdown ("## Titre"). Chaque section doit apporter une valeur différente (comprendre / agir / anticiper selon le profil), jamais répéter les mêmes faits sous un autre angle.
   Dans les deux cas, n'écris jamais un simple paragraphe de citations mises bout à bout sans les relier par un raisonnement.
4. Si tes sources NE répondent PAS à la question, ou n'y répondent qu'insuffisamment :
   - N'utilise PAS de structure à titres — dis-le clairement, simplement et à la première personne (jamais "les extraits fournis ne permettent pas de...").
   - Précise ce que tu as pu vérifier dans tes sources, pour que l'utilisateur comprenne le périmètre de ta réponse.
   - Si la question est large ou ambiguë, propose 1 à 2 reformulations plus précises qui permettraient une réponse exploitable.
   - Si le message n'est pas vraiment une question juridique (ex. un message de suivi conversationnel bref comme "ok", "explique", ou une question sur ton propre fonctionnement) : dis-le simplement et demande ce que l'utilisateur souhaite approfondir, au lieu de forcer une réponse structurée et sourcée autour de textes qui n'ont rien à voir.
   - Ne laisse JAMAIS la réponse en impasse : oriente toujours vers une suite possible (reformulation, domaine à préciser, ou consultation d'un professionnel/portail officiel si la question sort du champ couvert par les sources).
5. Rédige ta réponse dans la langue imposée par la CONSIGNE DE LANGUE ci-dessous (elle prime sur la langue de la question).
6. Termine TOUJOURS par 2 à 3 questions de suivi pertinentes, au format : "QUESTIONS SUGGÉRÉES: [Q1] | [Q2] | [Q3]"
"""

# Consigne de langue explicite : le modèle ne suit pas de façon fiable une règle
# du type « réponds en arabe si la question est en arabe » (observé : il répond
# en français malgré une question arabe). On impose donc la langue de sortie.
_LANG_DIRECTIVE = {
    "fr": "CONSIGNE DE LANGUE : rédige TOUTE ta réponse en français.",
    "en": (
        "CONSIGNE DE LANGUE : rédige TOUTE ta réponse en anglais, y compris les titres de sections et les "
        "questions suggérées. Les textes de référence sont en français : traduis fidèlement en anglais "
        "l'information utile, mais conserve les noms officiels des lois et les numéros d'articles/pages "
        "tels quels (ex. « Law 65-99, Article 52 »)."
    ),
    "ar": (
        "CONSIGNE DE LANGUE : rédige TOUTE ta réponse en arabe (اللغة العربية), y compris les titres de "
        "sections et les questions suggérées. Les textes de référence sont en français : traduis fidèlement "
        "en arabe l'information utile, mais conserve les noms officiels des lois et les numéros d'articles/pages "
        "tels quels (ex. « القانون 65-99, المادة 52 »)."
    ),
}
def _lang_directive(lang: str) -> str:
    return _LANG_DIRECTIVE.get((lang or "fr").lower(), _LANG_DIRECTIVE["fr"])

_ENCODING = None

def _get_encoding():
    global _ENCODING
    if _ENCODING is None:
        try:
            _ENCODING = tiktoken.get_encoding("cl100k_base")
        except Exception:
            logger.warning("tiktoken cl100k_base introuvable, fallback sur UTF-8 length/4.")
            _ENCODING = None
    return _ENCODING

def count_tokens(text: str) -> int:
    enc = _get_encoding()
    if enc:
        return len(enc.encode(text))
    return max(1, len(text) // 4)

def _clean_source_name(filename: str) -> str:
    """Nom de source lisible à partir du nom de fichier — évite d'exposer un
    numéro de source opaque ("SOURCE 1") que l'utilisateur ne peut pas relier
    au document réel sans revenir chercher la légende."""
    if not filename or filename == "N/A":
        return "document juridique"
    name = re.sub(r"\.(pdf|docx?|txt|html?)$", "", filename, flags=re.IGNORECASE)
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name or filename

def build_prompt(query: str, retrieved_chunks: list[dict], user_role: str = "particulier", conversation_history: list[dict] = None, lang: str = "fr") -> tuple[str, str]:
    role = ROLE_INSTRUCTIONS.get(user_role, ROLE_INSTRUCTIONS["particulier"])
    system = f"{CONTEXT_PREAMBLE}\n\n{role['persona']}\n{BASE_RULES}\nSTRUCTURE DE RÉPONSE (uniquement pour les questions substantielles — voir règle 3) :\n{_structure_for(role, lang)}\n\n{_lang_directive(lang)}"
    context_parts = []
    total_context_tokens = 0
    max_context = settings.MAX_CONTEXT_TOKENS
    for c in retrieved_chunks:
        meta = c.get("metadata", {})
        source_name = _clean_source_name(meta.get("filename"))
        domain_tag = f" [{meta.get('domain')}]" if meta.get("domain") else ""
        page_tag = f", p. {meta.get('page')}" if meta.get('page') else ""
        part = f"« {source_name} »{page_tag}{domain_tag}\n{c['text']}"
        part_tokens = count_tokens(part)
        if total_context_tokens + part_tokens > max_context:
            logger.warning(f"Budget contexte atteint ({total_context_tokens + part_tokens} tokens > {max_context}), troncature des chunks.")
            break
        total_context_tokens += part_tokens
        context_parts.append(part)
    context = "\n\n---\n\n".join(context_parts)
    history_section = ""
    if conversation_history:
        lines = [f"{'Utilisateur' if m['role']=='user' else 'Assistant'}: {m['content'][:200]}" for m in conversation_history[-6:]]
        history_text = "\n".join(lines)
        history_tokens = count_tokens(history_text)
        if total_context_tokens + history_tokens > max_context:
            logger.warning(f"Budget contexte atteint avec historique ({total_context_tokens + history_tokens} tokens > {max_context}), historique réduit.")
            lines = lines[-4:]
            history_text = "\n".join(lines)
        history_section = "CONTEXTE PRÉCÉDENT :\n" + history_text + "\n\n---\n\n"
    user_msg = f"{history_section}TEXTES JURIDIQUES :\n\n{context}\n\n---\n\nQUESTION : {query}\n\nCite le nom réel de chaque source utilisée, directement dans la phrase (jamais un numéro)."
    return system, user_msg

def build_no_context_prompt(query: str, user_role: str = "particulier", lang: str = "fr") -> tuple[str, str]:
    """Prompt utilisé quand la recherche ne trouve AUCUN passage pertinent dans
    le corpus indexé. Avant, ce cas renvoyait un message statique codé en dur
    sans jamais appeler le LLM — un mur plutôt qu'une réponse. Ici, le modèle
    peut donner une orientation générale à partir de ses connaissances, mais
    sous une règle stricte non négociable : jamais de fausse citation d'article
    ou de loi présentée comme vérifiée, et un avertissement explicite que ce
    n'est PAS vérifié dans la base officielle de LexIA Maroc."""
    role = ROLE_INSTRUCTIONS.get(user_role, ROLE_INSTRUCTIONS["particulier"])
    system = (
        f"{CONTEXT_PREAMBLE}\n\n{role['persona']}\n\n"
        "La recherche dans la base de textes juridiques marocains indexée par LexIA Maroc n'a trouvé "
        "AUCUN passage pertinent pour cette question.\n\n"
        "RÈGLES :\n"
        "1. Tu peux donner une orientation générale brève, à partir de tes connaissances générales du droit "
        "marocain — mais UNIQUEMENT si tu es raisonnablement confiant. Si tu ne sais vraiment pas, dis-le "
        "franchement plutôt que d'inventer.\n"
        "2. N'invente et ne cite JAMAIS un numéro d'article, de loi ou de dahir précis comme si c'était vérifié — "
        "cette réponse n'est pas fondée sur nos textes officiels indexés. Reste sur des principes généraux, sans "
        "fausse précision.\n"
        "3. Commence TOUJOURS ta réponse par une phrase indiquant clairement qu'aucun texte officiel correspondant "
        "n'a été trouvé dans la base LexIA Maroc pour cette question, et que ce qui suit est une orientation "
        "générale non vérifiée, à confirmer auprès d'un professionnel ou d'une source officielle "
        "(www.sgg.gov.ma, www.tax.gov.ma, www.cndp.ma selon le domaine).\n"
        "4. Reste concis (un ou deux paragraphes courts), sans titres Markdown ni structure imposée.\n\n"
        f"{_lang_directive(lang)}"
    )
    user_msg = f"QUESTION : {query}"
    return system, user_msg


AUDIT_MAX_CONTRACT_CHARS = 6000  # borne le contrat injecté pour rester dans le budget de contexte

def _context_from_chunks(retrieved_chunks: list[dict]) -> str:
    parts = []
    for c in retrieved_chunks:
        meta = c.get("metadata", {})
        source_name = _clean_source_name(meta.get("filename"))
        page_tag = f", p. {meta.get('page')}" if meta.get("page") else ""
        parts.append(f"« {source_name} »{page_tag}\n{c['text']}")
    return "\n\n---\n\n".join(parts)

def build_audit_prompt(contract_text: str, retrieved_chunks: list[dict]) -> tuple[str, str]:
    """Prompt d'audit d'un contrat au regard du droit du travail marocain,
    ancré sur les passages de loi récupérés (grounding RAG). Renvoie
    (system_prompt, user_message)."""
    system = (
        f"{CONTEXT_PREAMBLE}\n\n"
        "Tu es un juriste spécialisé en droit du travail marocain. On te soumet un contrat à auditer. "
        "Analyse-le UNIQUEMENT à la lumière des textes juridiques de référence fournis et du contrat lui-même ; "
        "n'invente aucune règle absente des sources.\n"
        "Structure ta réponse avec exactement ces sections Markdown :\n"
        "## Type de document\n(nature du contrat, parties, objet — d'après le contrat)\n"
        "## Points de conformité\n(éléments présents et conformes ; cite l'article applicable quand une source le confirme)\n"
        "## Risques et clauses problématiques\n(clauses ambiguës, déséquilibrées ou potentiellement non conformes, avec l'article concerné)\n"
        "## Clauses manquantes recommandées\n(clauses usuelles ou obligatoires absentes du contrat)\n\n"
        "Cite tes sources par leur nom réel entre guillemets (jamais un numéro). "
        "Si un point ne peut être vérifié faute de texte fourni, dis-le explicitement plutôt que d'affirmer."
    )
    context = _context_from_chunks(retrieved_chunks)
    contract = contract_text.strip()[:AUDIT_MAX_CONTRACT_CHARS]
    user_msg = (
        f"TEXTES JURIDIQUES DE RÉFÉRENCE :\n\n{context}\n\n---\n\n"
        f"CONTRAT À AUDITER :\n\n{contract}\n\n---\n\n"
        "Produis l'audit structuré selon les sections demandées."
    )
    return system, user_msg

def format_citations(chunks: list[dict]) -> list[dict]:
    return [{
        "index": i+1,
        "label": " | ".join(filter(None, [c.get("metadata",{}).get("filename"), c.get("metadata",{}).get("source","").upper() or None])) or f"Source {i+1}",
        "domain": c.get("domain", c.get("metadata",{}).get("domain","N/A")),
        "source": c.get("metadata",{}).get("source","N/A"),
        "filename": c.get("metadata",{}).get("filename","N/A"),
        "page": c.get("metadata",{}).get("page"),
        "url": c.get("metadata",{}).get("url"),
        "excerpt": c["text"][:250] + "..." if len(c["text"]) > 250 else c["text"],
        "score": float(c.get("rerank_score", c.get("rrf_score", c.get("score", 0)))),
        "retrieval_method": c.get("method","hybrid"),
    } for i, c in enumerate(chunks)]

def extract_suggested_queries(answer: str) -> tuple[str, list[str]]:
    # Le marqueur est souvent précédé d'un gras Markdown ("**QUESTIONS SUGGÉRÉES:**")
    # — on consomme les astérisques/espaces de tête pour ne pas laisser de "**" orphelin.
    m = re.search(r"\**\s*QUESTIONS SUGGÉRÉES\s*:?\s*(.*?)(?:\n|$)", answer, re.IGNORECASE)
    if not m: return answer, []
    clean = re.sub(r"[\s*#>-]+$", "", answer[:m.start()])
    questions = [q.strip().lstrip("[").rstrip("]").strip("* ") for q in m.group(1).split("|")]
    return clean, [q for q in questions if q and len(q) > 5]
