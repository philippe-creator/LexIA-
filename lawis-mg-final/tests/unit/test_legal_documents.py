import pytest
from generation.legal_documents import (
    list_document_types, build_document, DOCUMENT_TYPES, _fmt_date, _money,
)
from generation.document_renderers import render_docx, render_pdf


def _full_data(doc_type):
    """Remplit tous les champs obligatoires d'un modèle avec des valeurs bidon."""
    data = {}
    for f in DOCUMENT_TYPES[doc_type]["fields"]:
        if f["type"] == "number":
            data[f["name"]] = "1000"
        elif f["type"] == "date":
            data[f["name"]] = "2026-01-15"
        elif f["type"] == "select":
            data[f["name"]] = f["options"][0]
        else:
            data[f["name"]] = f"valeur_{f['name']}"
    return data


def test_all_types_listed_without_build_callable():
    types = list_document_types()
    assert len(types) == 4
    for t in types:
        assert "build" not in t          # la fonction n'est pas sérialisable
        assert t["fields"] and t["legal_reference"]


@pytest.mark.parametrize("doc_type", list(DOCUMENT_TYPES.keys()))
def test_build_every_document_produces_blocks_and_reference(doc_type):
    doc = build_document(doc_type, _full_data(doc_type))
    assert doc["blocks"]
    assert doc["legal_reference"]
    # Le disclaimer indicatif doit toujours clôturer la pièce.
    assert any(b["style"] == "note" for b in doc["blocks"])


@pytest.mark.parametrize("doc_type", list(DOCUMENT_TYPES.keys()))
def test_render_docx_and_pdf_are_valid_binaries(doc_type):
    doc = build_document(doc_type, _full_data(doc_type))
    docx_bytes = render_docx(doc)
    pdf_bytes = render_pdf(doc)
    assert docx_bytes[:2] == b"PK"       # signature ZIP (DOCX)
    assert pdf_bytes[:4] == b"%PDF"      # signature PDF


def test_missing_required_field_raises():
    with pytest.raises(ValueError, match="obligatoires"):
        build_document("attestation_travail", {"signatory_name": "x"})


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="inconnu"):
        build_document("does_not_exist", {})


def test_cdi_trial_period_depends_on_category():
    cadre = build_document("cdi", {**_full_data("cdi"), "trial_category": "cadre"})
    ouvrier = build_document("cdi", {**_full_data("cdi"), "trial_category": "ouvrier"})
    cadre_text = " ".join(b["text"] for b in cadre["blocks"])
    ouvrier_text = " ".join(b["text"] for b in ouvrier["blocks"])
    assert "trois (3) mois" in cadre_text
    assert "quinze (15) jours" in ouvrier_text


def test_fmt_date_iso_to_french():
    assert _fmt_date("2026-07-21") == "21/07/2026"
    assert _fmt_date("le 3 mars") == "le 3 mars"   # texte libre inchangé


def test_money_thousands_separator():
    assert _money(12500) == "12 500,00"
    assert _money("abc") == "abc"                  # non numérique inchangé
