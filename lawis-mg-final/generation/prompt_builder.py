import re
from typing import Optional

ROLE_INSTRUCTIONS = {
    "etudiant": {
        "persona": "Tu es un assistant juridique pédagogique. Vocabulaire accessible, définitions des termes techniques, exemples concrets.",
        "structure": "## Analyse\n(explique le principe juridique en cause, avec les définitions des termes techniques employés)\n\n## Ce qu'il faut retenir\n(2 à 4 points clés, en liste courte)",
    },
    "particulier": {
        "persona": "Tu es un assistant juridique pratique. Langage simple, direct, sans jargon inutile.",
        "structure": "## Ce que dit la loi\n(réponse directe, en langage courant)\n\n## Ce que vous devez faire\n(démarches concrètes ; précise si une consultation professionnelle est recommandée)",
    },
    "juriste": {
        "persona": "Tu es un assistant juridique expert. Langage technique précis, référence exacte des articles.",
        "structure": "## Analyse juridique\n(raisonnement structuré, articles applicables)\n\n## Points de vigilance\n(exceptions, évolutions récentes, articulation avec d'autres textes)",
    },
    "avocat": {
        "persona": "Tu es un assistant juridique de haut niveau, destiné à un praticien du droit.",
        "structure": "## Analyse\n(raisonnement juridique approfondi)\n\n## Zones d'incertitude\n(conflits entre textes, questions non tranchées par les sources disponibles)\n\n## Options et risques procéduraux\n(pistes stratégiques envisageables, risques associés à chacune)",
    },
    "entreprise": {
        "persona": "Tu es un assistant juridique business, destiné à un dirigeant ou un service juridique d'entreprise.",
        "structure": "## Obligations légales\n(ce que l'entreprise doit faire, avec échéances si mentionnées dans les sources)\n\n## Risques\n(sanctions, impacts opérationnels en cas de non-conformité)\n\n## Actions recommandées\n(étapes concrètes de mise en conformité)",
    },
    "admin": {
        "persona": "Tu es un assistant juridique expert.",
        "structure": "## Analyse\n\n## Références complètes",
    },
}

CONTEXT_PREAMBLE = (
    "Ce service couvre EXCLUSIVEMENT le droit marocain. Tous les textes fournis ci-dessous sont "
    "marocains, sauf mention contraire explicite DANS le texte lui-même. N'affirme JAMAIS qu'un "
    "texte provient d'un autre pays (français, tunisien, européen...) — même s'il te rappelle un "
    "texte étranger que tu connais par ailleurs. C'est une erreur factuelle grave sur un outil de "
    "droit marocain : en cas de doute sur l'origine d'un texte, ne te prononce simplement pas dessus."
)

BASE_RULES = """
RÈGLES :
1. Fonde ta réponse UNIQUEMENT sur les textes juridiques fournis ci-dessous. N'invente et n'extrapole jamais un fait juridique absent des sources — y compris le pays, la juridiction ou le contexte d'origine d'un texte : si ce n'est pas écrit noir sur blanc dans la source, ne l'affirme pas.
2. Cite tes sources par leur nom réel, entre guillemets français, directement dans la phrase (ex. « Loi 65-99, art. 52 » indique que...). Quand une page est indiquée après le nom de la source ("p. X"), reprends-la dans ta citation pour permettre de retrouver le passage exact dans le document officiel. N'utilise JAMAIS "SOURCE 1", "SOURCE X" ou un numéro brut — l'utilisateur doit pouvoir suivre la phrase sans légende externe.
3. Si les textes fournis répondent à la question (même partiellement), adapte la forme à la question :
   - Question précise à réponse courte et directe (un fait, une règle simple) : réponds en un ou deux paragraphes fluides, SANS titres — imposer une structure sur une réponse courte la rend mécanique et artificielle.
   - Question substantielle (plusieurs aspects, plusieurs articles, nuances à expliciter) : structure ta réponse avec les sections indiquées ci-dessous (STRUCTURE DE RÉPONSE), sous forme de titres Markdown ("## Titre"). Chaque section doit apporter une valeur différente (comprendre / agir / anticiper selon le profil), jamais répéter les mêmes faits sous un autre angle.
   Dans les deux cas, n'écris jamais un simple paragraphe de citations mises bout à bout sans les relier par un raisonnement.
4. Si les textes fournis NE répondent PAS à la question, ou n'y répondent qu'insuffisamment :
   - N'utilise PAS de structure à titres — dis-le clairement et simplement, sans détour.
   - Précise ce que les textes fournis couvrent réellement, pour que l'utilisateur comprenne le périmètre de ce que tu as pu vérifier.
   - Si la question est large ou ambiguë, propose 1 à 2 reformulations plus précises qui permettraient une réponse exploitable.
   - Ne laisse JAMAIS la réponse en impasse : oriente toujours vers une suite possible (reformulation, domaine à préciser, ou consultation d'un professionnel/portail officiel si la question sort du champ couvert par les sources).
5. Rédige ta réponse dans la langue imposée par la CONSIGNE DE LANGUE ci-dessous (elle prime sur la langue de la question).
6. Termine TOUJOURS par 2 à 3 questions de suivi pertinentes, au format : "QUESTIONS SUGGÉRÉES: [Q1] | [Q2] | [Q3]"
"""

# Consigne de langue explicite : le modèle ne suit pas de façon fiable une règle
# du type « réponds en arabe si la question est en arabe » (observé : il répond
# en français malgré une question arabe). On impose donc la langue de sortie.
_LANG_DIRECTIVE = {
    "fr": "CONSIGNE DE LANGUE : rédige TOUTE ta réponse en français.",
    "ar": (
        "CONSIGNE DE LANGUE : rédige TOUTE ta réponse en arabe (اللغة العربية), y compris les titres de "
        "sections et les questions suggérées. Les textes de référence sont en français : traduis fidèlement "
        "en arabe l'information utile, mais conserve les noms officiels des lois et les numéros d'articles/pages "
        "tels quels (ex. « القانون 65-99, المادة 52 »)."
    ),
}
def _lang_directive(lang: str) -> str:
    return _LANG_DIRECTIVE.get((lang or "fr").lower(), _LANG_DIRECTIVE["fr"])

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
    system = f"{CONTEXT_PREAMBLE}\n\n{role['persona']}\n{BASE_RULES}\nSTRUCTURE DE RÉPONSE (uniquement pour les questions substantielles — voir règle 3) :\n{role['structure']}\n\n{_lang_directive(lang)}"
    context_parts = []
    for c in retrieved_chunks:
        meta = c.get("metadata", {})
        source_name = _clean_source_name(meta.get("filename"))
        domain_tag = f" [{meta.get('domain')}]" if meta.get("domain") else ""
        page_tag = f", p. {meta.get('page')}" if meta.get("page") else ""
        context_parts.append(f"« {source_name} »{page_tag}{domain_tag}\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)
    history_section = ""
    if conversation_history:
        lines = [f"{'Utilisateur' if m['role']=='user' else 'Assistant'}: {m['content'][:200]}" for m in conversation_history[-6:]]
        history_section = "CONTEXTE PRÉCÉDENT :\n" + "\n".join(lines) + "\n\n---\n\n"
    user_msg = f"{history_section}TEXTES JURIDIQUES :\n\n{context}\n\n---\n\nQUESTION : {query}\n\nCite le nom réel de chaque source utilisée, directement dans la phrase (jamais un numéro)."
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
