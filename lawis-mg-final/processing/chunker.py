"""
Chunker — découpage des textes juridiques en chunks pertinents.
Stratégie : découpage par article/alinéa d'abord,
            fallback sur découpage par taille avec chevauchement.
"""
import re
from dataclasses import dataclass, field
from loguru import logger

# Patterns de structure juridique marocaine
ARTICLE_PATTERNS = [
    r"^article\s+\d+[\s\-–—]",        # Article 9 —
    r"^art\.\s*\d+[\s\-–—]",           # Art. 9 —
    r"^\d+\s*[-–—]\s+",               # 9 — texte
    r"^chapitre\s+[IVXivx\d]+",       # Chapitre I, II...
    r"^section\s+[IVXivx\d]+",        # Section 1
    r"^titre\s+[IVXivx\d]+",          # Titre I
]

CHUNK_SIZE = 800        # taille cible en caractères
CHUNK_OVERLAP = 150     # chevauchement entre chunks consécutifs

# Une ligne de sommaire ("ARTICLE 247 BIS .......... 464") matche le motif
# d'en-tête d'article ci-dessus (commence par "article N") et se retrouvait
# indexée comme si c'était le texte réel de l'article — sans aucun contenu
# juridique. Un texte de loi ne contient jamais de suite de points de
# guidage typographiques ; une table des matières, systématiquement.
_TOC_LEADER = re.compile(r"\.{4,}\s*\d+")


def _looks_like_toc(text: str) -> bool:
    # Le découpage par en-tête d'article isole souvent CHAQUE ligne de
    # sommaire dans son propre chunk (une seule occurrence du motif) — un
    # simple comptage ">= 2" les rate. On mesure plutôt la part du texte
    # occupée par le "guidage de points" : dans une vraie ligne de sommaire
    # ("ARTICLE 247 BIS .......... 464"), les points dominent le texte ;
    # dans un article réel, une éventuelle ellipse ("[...]") est marginale.
    matches = _TOC_LEADER.findall(text)
    if not matches:
        return False
    if len(matches) >= 2:
        return True
    return sum(len(m) for m in matches) / max(len(text), 1) > 0.15


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    def __len__(self):
        return len(self.text)


def split_by_articles(text: str) -> list[str]:
    """
    Découpe un texte juridique en sections par article.
    Retourne une liste de chaînes (une par article/section).
    """
    combined_pattern = "|".join(ARTICLE_PATTERNS)
    # re.IGNORECASE est indispensable ici : les textes juridiques marocains
    # écrivent presque toujours "Article N" (majuscule), alors que les motifs
    # ci-dessus sont en minuscules — sans ce flag, le split ne matche jamais
    # et le découpage retombe silencieusement sur le fallback par taille.
    parts = re.split(f"({combined_pattern})", text, flags=re.MULTILINE | re.IGNORECASE)

    if len(parts) <= 1:
        return []  # Pas de structure d'articles détectée

    sections = []
    i = 0
    while i < len(parts):
        if re.match(combined_pattern, parts[i], re.IGNORECASE | re.MULTILINE):
            # L'article header + son contenu
            header = parts[i]
            body = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((header + body).strip())
            i += 2
        else:
            if parts[i].strip():
                sections.append(parts[i].strip())
            i += 1

    return [s for s in sections if len(s.strip()) > 30 and not _looks_like_toc(s)]


def split_by_size(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Découpage par taille avec chevauchement (fallback).
    Respecte les fins de phrase pour éviter les coupures en plein milieu.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += " " + sentence
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # Chevauchement : garder les derniers `overlap` caractères
            current_chunk = current_chunk[-overlap:] + " " + sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def chunk_document(text: str, metadata: dict = None) -> list[Chunk]:
    """
    Point d'entrée principal.
    Tente d'abord le découpage par articles, puis par taille.
    """
    metadata = metadata or {}
    if not text.strip():
        return []

    # Tenter le découpage structurel par articles
    article_sections = split_by_articles(text)

    if len(article_sections) >= 3:
        logger.debug(f"Découpage par articles : {len(article_sections)} sections")
        chunks = []
        for i, section in enumerate(article_sections):
            # Si une section est trop grande, la re-découper
            if len(section) > CHUNK_SIZE * 2:
                sub_chunks = split_by_size(section)
                for j, sub in enumerate(sub_chunks):
                    chunks.append(Chunk(
                        text=sub,
                        metadata={**metadata, "chunk_idx": f"{i}_{j}", "method": "article+size"},
                    ))
            else:
                chunks.append(Chunk(
                    text=section,
                    metadata={**metadata, "chunk_idx": str(i), "method": "article"},
                ))
        return chunks

    # Fallback : découpage par taille
    logger.debug("Pas de structure article détectée — découpage par taille")
    size_chunks = [c for c in split_by_size(text) if not _looks_like_toc(c)]
    return [
        Chunk(text=c, metadata={**metadata, "chunk_idx": str(i), "method": "size"})
        for i, c in enumerate(size_chunks)
    ]


def assign_pages(chunks: list[Chunk], full_text: str, page_offsets: list[int] | None) -> None:
    """Annote chaque chunk avec le numéro de page (1-indexé) où il commence,
    par recherche de sa position dans le texte source complet. Approximatif
    près des frontières de page (le chevauchement entre chunks peut décaler
    la correspondance de quelques caractères) mais suffisant pour retrouver
    la bonne page dans le PDF — traçabilité (BNF-02 du cahier des charges).
    Ne fait rien si `page_offsets` est absent (texte non issu d'un PDF)."""
    if not page_offsets:
        return
    cursor = 0
    for c in chunks:
        needle = c.text.strip()[:60]
        if not needle:
            continue
        pos = full_text.find(needle, max(0, cursor - 200))
        if pos == -1:
            pos = full_text.find(needle)
        if pos == -1:
            continue
        cursor = pos
        page_num = 1
        for i, offset in enumerate(page_offsets):
            if offset <= pos:
                page_num = i + 1
            else:
                break
        c.metadata["page"] = page_num


if __name__ == "__main__":
    sample = """
    Article 1 — Le présent code régit les relations entre employeurs et salariés.
    Il s'applique à toutes les entreprises exerçant leur activité au Maroc.

    Article 2 — Les dispositions du présent code sont d'ordre public.
    Toute convention contraire est nulle de plein droit.

    Article 3 — Les litiges relatifs à l'application du présent code relèvent
    de la juridiction compétente.
    """
    chunks = chunk_document(sample, metadata={"domain": "travail", "source": "test"})
    for c in chunks:
        print(f"[{c.metadata}] {c.text[:80]}...")
