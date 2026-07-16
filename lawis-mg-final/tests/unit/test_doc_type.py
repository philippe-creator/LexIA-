from processing.doc_type import classify_doc_type, extract_year


def test_classifies_dahir():
    assert classify_doc_type("dahir n°1.22.65.pdf") == "dahir"


def test_classifies_decret_with_accent():
    assert classify_doc_type("decret-2-09-165.pdf") == "decret"
    assert classify_doc_type("décret d'application.pdf") == "decret"


def test_classifies_arrete():
    assert classify_doc_type("Arrêté n° 1019.20.pdf") == "arrete"


def test_classifies_loi():
    assert classify_doc_type("loi-65-00-amo_0.pdf") == "loi"


def test_recueil_classified_as_loi():
    assert classify_doc_type("Recueil-textes-juridiques07012026-RG.pdf") == "loi"


def test_unrecognized_filename_falls_back_to_autre():
    assert classify_doc_type("nomenclature marocaine des activités.pdf") == "autre"


def test_jurisprudence_domain_overrides_filename_pattern():
    """Un arrêt de la Cour de cassation reste 'jurisprudence' même si son nom
    de fichier contient un mot-clé comme 'arrêté'."""
    assert classify_doc_type("arret-cour-cassation-2024.pdf", domain="jurisprudence") == "jurisprudence"


def test_extract_year_finds_plausible_year():
    assert extract_year("Recueil-textes-juridiques07012026-RG.pdf") == 2026


def test_extract_year_returns_none_when_absent():
    assert extract_year("loi-65-00-amo_0.pdf") is None


def test_extract_year_handles_empty_filename():
    assert extract_year("") is None
    assert extract_year(None) is None
