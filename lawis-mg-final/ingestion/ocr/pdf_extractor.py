"""
Module OCR — extraction de texte depuis PDFs images (Bulletin Officiel)
Stratégie : tente d'abord l'extraction texte natif (PyMuPDF),
            si le PDF est en mode image → fallback OCR (Tesseract)
"""
import os
from pathlib import Path
from loguru import logger

import fitz          # PyMuPDF — extraction texte natif
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from core.config import settings

# Sur les postes Windows sans poppler/tesseract enregistrés dans le PATH du
# processus Python (le cas courant en dev local), on pointe explicitement
# vers les binaires plutôt que de dépendre du PATH — voir core/config.py.
# En Docker/Linux, ces réglages restent vides et le PATH système suffit.
_POPPLER_PATH = settings.POPPLER_PATH or None
if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Langues OCR : français + arabe (le BO marocain est bilingue)
OCR_LANGS = "fra+ara"
NATIVE_TEXT_THRESHOLD = 50  # nb de caractères minimum pour considérer un PDF "texte natif"
MAX_PDF_PAGES = 500  # garde-fou contre les PDF adversariaux (déni de service via OCR)


def _join_with_offsets(text_pages: list[str]) -> tuple[str, list[int]]:
    """Joint les textes de page et retourne, pour chaque page, l'offset (en
    caractères) où elle commence dans le texte joint — permet de retrouver
    plus tard la page d'origine d'un passage cité (traçabilité, BNF-02)."""
    offsets, offset = [], 0
    for t in text_pages:
        offsets.append(offset)
        offset += len(t) + 1  # +1 pour le "\n" séparateur
    return "\n".join(text_pages), offsets


def extract_text_native(pdf_path: Path) -> tuple[str, list[int]]:
    """Extraction texte natif avec PyMuPDF (rapide, pas d'OCR)."""
    text_pages = []
    try:
        doc = fitz.open(str(pdf_path))
        for page in doc:
            text_pages.append(page.get_text())
        doc.close()
    except Exception as e:
        logger.warning(f"PyMuPDF impossible sur {pdf_path.name} : {e}")
    return _join_with_offsets(text_pages)


def extract_text_ocr(pdf_path: Path) -> tuple[str, list[int]]:
    """OCR sur chaque page du PDF (pour PDFs images / fac-similés scannés)."""
    text_pages = []
    try:
        images = convert_from_path(str(pdf_path), dpi=300, poppler_path=_POPPLER_PATH)
        for i, image in enumerate(images):
            logger.debug(f"OCR page {i+1}/{len(images)} : {pdf_path.name}")
            text = pytesseract.image_to_string(image, lang=OCR_LANGS)
            text_pages.append(text)
    except Exception as e:
        logger.error(f"OCR impossible sur {pdf_path.name} : {e}")
    return _join_with_offsets(text_pages)


def extract_text(pdf_path: Path) -> dict:
    """
    Point d'entrée principal.
    Tente l'extraction native, bascule sur OCR si le texte est insuffisant.
    Retourne un dict avec le texte et les métadonnées d'extraction.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error(f"Fichier introuvable : {pdf_path}")
        return {"text": "", "method": "error", "path": str(pdf_path)}

    try:
        with fitz.open(str(pdf_path)) as doc:
            page_count = doc.page_count
    except Exception as e:
        logger.error(f"PDF illisible {pdf_path.name} : {e}")
        return {"text": "", "method": "error", "path": str(pdf_path)}
    if page_count > MAX_PDF_PAGES:
        logger.warning(f"PDF rejeté ({page_count} pages > {MAX_PDF_PAGES}) : {pdf_path.name}")
        return {"text": "", "method": "rejected_too_many_pages", "path": str(pdf_path)}

    # Tentative extraction native
    native_text, native_offsets = extract_text_native(pdf_path)
    clean_native = native_text.replace("\n", " ").strip()

    if len(clean_native) >= NATIVE_TEXT_THRESHOLD:
        logger.info(f"Texte natif extrait : {pdf_path.name} ({len(clean_native)} chars)")
        return {
            "text": native_text,
            "method": "native",
            "path": str(pdf_path),
            "char_count": len(clean_native),
            "page_offsets": native_offsets,
        }

    # Fallback OCR
    logger.info(f"PDF image détecté, OCR en cours : {pdf_path.name}")
    ocr_text, ocr_offsets = extract_text_ocr(pdf_path)
    return {
        "text": ocr_text,
        "method": "ocr",
        "path": str(pdf_path),
        "char_count": len(ocr_text.replace("\n", " ").strip()),
        "page_offsets": ocr_offsets,
    }


def batch_extract(pdf_dir: Path, output_dir: Path) -> list[dict]:
    """
    Extrait le texte de tous les PDFs d'un répertoire.
    Sauvegarde les textes en .txt dans output_dir.
    """
    pdf_dir = Path(pdf_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    pdf_files = list(pdf_dir.rglob("*.pdf"))
    logger.info(f"Extraction batch : {len(pdf_files)} PDFs dans {pdf_dir}")

    for pdf_path in pdf_files:
        txt_path = output_dir / (pdf_path.stem + ".txt")
        if txt_path.exists():
            logger.debug(f"Déjà extrait : {txt_path.name}")
            continue

        result = extract_text(pdf_path)
        if result["text"].strip():
            txt_path.write_text(result["text"], encoding="utf-8")
            logger.info(f"Sauvegardé : {txt_path.name} (méthode: {result['method']})")
        else:
            logger.warning(f"Texte vide pour : {pdf_path.name}")

        results.append({**result, "txt_path": str(txt_path)})

    return results


if __name__ == "__main__":
    # Test rapide sur le corpus CNDP (le plus compact)
    batch_extract(
        pdf_dir=Path("./data/raw/donnees_personnelles"),
        output_dir=Path("./data/processed/donnees_personnelles"),
    )
