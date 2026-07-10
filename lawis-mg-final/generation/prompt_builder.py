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
RÈGLES STRICTES :
1. Réponds UNIQUEMENT sur la base des textes juridiques fournis.
2. Cite TOUJOURS la source exacte [SOURCE X] dans ta réponse.
3. Si les textes ne permettent pas de répondre, dis-le explicitement.
4. Ne génère AUCUNE information absente des sources.
5. Réponds en français sauf si la question est en arabe.
6. Fin de réponse : propose 2-3 questions de suivi au format "QUESTIONS SUGGÉRÉES: [Q1] | [Q2] | [Q3]"
"""

def build_prompt(query: str, retrieved_chunks: list[dict], user_role: str = "particulier", conversation_history: list[dict] = None) -> tuple[str, str]:
    system = ROLE_INSTRUCTIONS.get(user_role, ROLE_INSTRUCTIONS["particulier"]) + BASE_RULES
    context_parts = []
    for i, c in enumerate(retrieved_chunks):
        meta = c.get("metadata", {})
        label = " | ".join(filter(None, [meta.get("filename"), f"via {meta.get('source','').upper()}" if meta.get("source") else None, f"[{meta.get('domain','')}]" if meta.get("domain") else None]))
        context_parts.append(f"[SOURCE {i+1}] {label}\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)
    history_section = ""
    if conversation_history:
        lines = [f"{'Utilisateur' if m['role']=='user' else 'Assistant'}: {m['content'][:200]}" for m in conversation_history[-6:]]
        history_section = "CONTEXTE PRÉCÉDENT :\n" + "\n".join(lines) + "\n\n---\n\n"
    user_msg = f"{history_section}TEXTES JURIDIQUES :\n\n{context}\n\n---\n\nQUESTION : {query}\n\nCite [SOURCE X] pour chaque information utilisée."
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
