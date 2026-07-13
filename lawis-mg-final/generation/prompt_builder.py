import re
from typing import Optional

ROLE_INSTRUCTIONS = {
    "etudiant": "Tu es un assistant juridique pédagogique. Vocabulaire accessible, définitions des termes techniques, exemples concrets, structure didactique.",
    "particulier": "Tu es un assistant juridique pratique. Langage simple, réponse directe, démarches concrètes. Signale si une consultation pro est recommandée.",
    "juriste": "Tu es un assistant juridique expert. Langage technique précis, référence exacte des articles, jurisprudence, exceptions et évolutions récentes.",
    "avocat": "Tu es un assistant juridique de haut niveau. Analyse approfondie, conflits entre textes, zones d'incertitude, options stratégiques, risques procéduraux.",
    "entreprise": "Tu es un assistant juridique business. Obligations légales, risques, impacts opérationnels, sanctions, échéances, mise en conformité.",
    "admin": "Tu es un assistant juridique expert. Réponse complète et technique avec toutes les références disponibles.",
}

BASE_RULES = """
RÈGLES :
1. Fonde ta réponse UNIQUEMENT sur les textes juridiques fournis ci-dessous. N'invente et n'extrapole jamais un fait juridique absent des sources.
2. Cite tes sources par leur nom réel, entre guillemets français, directement dans la phrase (ex. « Loi 65-99, art. 52 » indique que...). N'utilise JAMAIS "SOURCE 1", "SOURCE X" ou un numéro brut — l'utilisateur doit pouvoir suivre la phrase sans légende externe.
3. Si les textes fournis ne répondent pas à la question, ou n'y répondent que partiellement :
   - Dis-le clairement, sans détour.
   - Précise ce que les textes fournis couvrent réellement, pour que l'utilisateur comprenne le périmètre de ce que tu as pu vérifier.
   - Si la question est large ou ambiguë, propose 1 à 2 reformulations plus précises qui permettraient une réponse exploitable.
   - Ne laisse JAMAIS la réponse en impasse : oriente toujours vers une suite possible (reformulation, domaine à préciser, ou consultation d'un professionnel/portail officiel si la question sort du champ couvert par les sources).
4. Réponds en français sauf si la question est posée en arabe.
5. Termine TOUJOURS par 2 à 3 questions de suivi pertinentes, au format : "QUESTIONS SUGGÉRÉES: [Q1] | [Q2] | [Q3]"
"""

def _clean_source_name(filename: str) -> str:
    """Nom de source lisible à partir du nom de fichier — évite d'exposer un
    numéro de source opaque ("SOURCE 1") que l'utilisateur ne peut pas relier
    au document réel sans revenir chercher la légende."""
    if not filename or filename == "N/A":
        return "document juridique"
    name = re.sub(r"\.(pdf|docx?|txt|html?)$", "", filename, flags=re.IGNORECASE)
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name or filename

def build_prompt(query: str, retrieved_chunks: list[dict], user_role: str = "particulier", conversation_history: list[dict] = None) -> tuple[str, str]:
    system = ROLE_INSTRUCTIONS.get(user_role, ROLE_INSTRUCTIONS["particulier"]) + BASE_RULES
    context_parts = []
    for c in retrieved_chunks:
        meta = c.get("metadata", {})
        source_name = _clean_source_name(meta.get("filename"))
        domain_tag = f" [{meta.get('domain')}]" if meta.get("domain") else ""
        context_parts.append(f"« {source_name} »{domain_tag}\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)
    history_section = ""
    if conversation_history:
        lines = [f"{'Utilisateur' if m['role']=='user' else 'Assistant'}: {m['content'][:200]}" for m in conversation_history[-6:]]
        history_section = "CONTEXTE PRÉCÉDENT :\n" + "\n".join(lines) + "\n\n---\n\n"
    user_msg = f"{history_section}TEXTES JURIDIQUES :\n\n{context}\n\n---\n\nQUESTION : {query}\n\nCite le nom réel de chaque source utilisée, directement dans la phrase (jamais un numéro)."
    return system, user_msg

def format_citations(chunks: list[dict]) -> list[dict]:
    return [{
        "index": i+1,
        "label": " | ".join(filter(None, [c.get("metadata",{}).get("filename"), c.get("metadata",{}).get("source","").upper() or None])) or f"Source {i+1}",
        "domain": c.get("domain", c.get("metadata",{}).get("domain","N/A")),
        "source": c.get("metadata",{}).get("source","N/A"),
        "filename": c.get("metadata",{}).get("filename","N/A"),
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
