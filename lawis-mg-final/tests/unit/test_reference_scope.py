import pytest
from api.routes.reference_search import (
    detect_scope_domain, detect_scope, detect_refs, exact_ref_boost, filename_boost,
    content_tokens, has_lexical_overlap,
)


@pytest.mark.parametrize("query,expected", [
    ("article 62 code du travail", "travail"),
    ("loi 65-99", "travail"),
    ("CGI 2026", "fiscal"),
    ("code général des impôts", "fiscal"),
    ("loi de finances 2025", "fiscal"),
    ("loi 17-95", "societes"),
    ("code de commerce article 592", "societes"),
    ("loi 09-08", "donnees_personnelles"),
])
def test_scope_domain_detected(query, expected):
    assert detect_scope_domain(query) == expected


@pytest.mark.parametrize("query", ["article 62", "dahir 1-72-184", "quelque chose"])
def test_no_scope_when_no_code_named(query):
    assert detect_scope_domain(query) is None


def test_article_and_code_are_both_detected_as_refs():
    # Les deux références sont repérées, mais seule « article 62 » doit être
    # cherchée comme chaîne — « code du travail » sert de périmètre.
    refs = detect_refs("article 62 code du travail")
    assert any("article 62" in r.lower() for r in refs)
    assert any(detect_scope_domain(r) == "travail" for r in refs)
    search_refs = [r for r in refs if detect_scope_domain(r) is None]
    assert search_refs and all("code du travail" not in r.lower() for r in search_refs)


def test_exact_article_outranks_a_mere_cross_reference():
    article = "Article 62 Avant le licenciement du salarié, il doit pouvoir se défendre."
    renvoi = "62 - Voir note correspondant à l'article 389."
    assert exact_ref_boost(article, "article 62") > exact_ref_boost(renvoi, "article 62")


def test_boost_tiers():
    assert exact_ref_boost("Article 62 Avant le licenciement...", "article 62") == 3.0
    assert exact_ref_boost("Le présent article 62 dispose que...", "article 62") == 1.5
    assert exact_ref_boost("x" * 300 + " article 62", "article 62") == 1.0


def test_boost_ignores_whitespace_noise():
    assert exact_ref_boost("Article   62\n  Avant le licenciement", "article 62") == 3.0


def test_scope_carries_a_filename_hint():
    assert detect_scope("article 62 code du travail") == ("travail", "code-du-travail")
    assert detect_scope("article 592 code de commerce") == ("societes", "code-de-commerce")
    assert detect_scope("rien de particulier") == (None, None)


def test_filename_boost_prefers_the_named_document():
    # Le domaine « travail » contient aussi la loi 65-00 (AMO), qui a un art. 62 :
    # à domaine égal, le document nommé dans la requête doit primer.
    code = {"filename": "Code-du-travail-65-99.pdf"}
    amo = {"filename": "loi-65-00-amo_0.pdf"}
    assert filename_boost(code, "code-du-travail") == 2.0
    assert filename_boost(amo, "code-du-travail") == 1.0


def test_filename_boost_is_neutral_without_hint():
    assert filename_boost({"filename": "x.pdf"}, None) == 1.0
    assert filename_boost(None, "code-du-travail") == 1.0


def test_content_tokens_keeps_meaningful_words():
    toks = content_tokens("note circulaire TVA")
    assert "note" in toks and "circulaire" in toks and "tva" in toks


def test_content_tokens_drops_stopwords_and_short():
    # « de », « la », « article », « loi » sont ignorés (mots-outils / génériques).
    toks = content_tokens("article 62 de la loi")
    assert "article" not in toks and "loi" not in toks and "de" not in toks
    assert "62" in toks


def test_overlap_rejects_unrelated_passage():
    # Cas réel : « note circulaire TVA » vs des passages sans aucun de ces mots.
    tokens = content_tokens("note circulaire TVA")
    assert not has_lexical_overlap("Titre V Dispositions transitoires", tokens)
    assert not has_lexical_overlap("Article 162 : Dans une lettre de change payable à vue", tokens)


def test_overlap_accepts_passage_mentioning_a_query_word():
    tokens = content_tokens("note circulaire TVA")
    assert has_lexical_overlap("La TVA est exigible au taux normal de 20%.", tokens)


def test_overlap_true_when_no_tokens():
    assert has_lexical_overlap("n'importe quoi", [])


def test_code_alone_stays_searchable():
    # Si le code est la SEULE référence, la requête porte bien sur le texte :
    # le repli doit conserver la référence plutôt que de chercher dans le vide.
    refs = detect_refs("code du travail")
    search_refs = [r for r in refs if detect_scope_domain(r) is None] or refs
    assert search_refs
