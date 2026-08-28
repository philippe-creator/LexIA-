"""
Rendu des documents juridiques (blocs neutres → fichier binaire).

Deux sorties depuis la même trame : DOCX (modifiable, brouillon relu par le
juriste) et PDF (version finale prête à imprimer/signer). La logique de contenu
vit dans generation/legal_documents.py ; ce module ne fait que la mise en forme.
"""

import io


def render_docx(document: dict) -> bytes:
    """Rend un document (dict issu de build_document) en fichier DOCX."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    for block in document["blocks"]:
        style, text = block["style"], block["text"]
        if style == "spacer":
            doc.add_paragraph("")
            continue
        p = doc.add_paragraph()
        run = p.add_run(text)
        if style == "title":
            run.bold = True
            run.font.size = Pt(15)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif style == "subtitle":
            run.bold = True
            run.font.size = Pt(12)
        elif style == "heading":
            run.bold = True
            run.font.size = Pt(11)
        elif style == "body_center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif style == "body_right":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif style == "note":
            run.italic = True
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
        else:  # body
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def render_pdf(document: dict) -> bytes:
    """Rend un document (dict issu de build_document) en fichier PDF.

    Utilise les polices core de fpdf2 (Helvetica), encodées en latin-1 : elles
    couvrent les accents français. Le texte est donc encodé/décodé en latin-1
    en remplaçant les rares caractères hors jeu (ex. apostrophe typographique).
    """
    from fpdf import FPDF

    def latin1(s: str) -> str:
        return (s.replace("’", "'").replace("‘", "'")
                 .replace("“", '"').replace("”", '"')
                 .replace("–", "-").replace("—", "-")
                 .replace("…", "...")
                 .encode("latin-1", "replace").decode("latin-1"))

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=20, right=20)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    for block in document["blocks"]:
        style, text = block["style"], latin1(block["text"])
        if style == "spacer":
            pdf.ln(4)
            continue
        # fpdf2 (2.8.7) a un bug reproductible : quand un multi_cell() qui vient
        # de replier son texte sur 2 lignes est immédiatement suivi d'un autre
        # multi_cell(), le second voit son texte tronqué dans le flux PDF rendu
        # (le texte Python, lui, est intact — le bug est interne à fpdf2). Forcer
        # la position avant CHAQUE multi_cell neutralise le problème. Reproduit
        # et corrigé sur « Il/Elle est en poste depuis le... » (attestation de
        # travail) qui sortait tronqué à « Il/Elle est e ».
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        if style == "title":
            pdf.set_font("Helvetica", "B", 15)
            pdf.multi_cell(width, 8, text, align="C")
        elif style == "subtitle":
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(width, 6, text, align="L")
        elif style == "heading":
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(width, 6, text, align="L")
        elif style == "body_center":
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(width, 6, text, align="C")
        elif style == "body_right":
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(width, 6, text, align="R")
        elif style == "note":
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(128, 128, 128)
            pdf.multi_cell(width, 4, text, align="L")
            pdf.set_text_color(0, 0, 0)
        else:  # body
            # align="J" (justifié) a un bug de rendu dans fpdf2 sur certaines
            # phrases courtes tenant sur une seule ligne : le texte est purement
            # perdu (pas juste mal réparti) — reproduit avec « Il/Elle est en
            # poste depuis le... » dans l'attestation de travail. Alignement à
            # gauche : moins "propre" visuellement, mais fiable.
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(width, 6, text, align="L")

    out = pdf.output()  # fpdf2 ≥ 2.8 renvoie un bytearray
    return bytes(out)
