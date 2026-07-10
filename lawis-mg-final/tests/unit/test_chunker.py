from processing.chunker import chunk_document, split_by_articles, split_by_size


ARTICLE_TEXT = """
Article 1 — Le présent code régit les relations entre employeurs et salariés.
Il s'applique à toutes les entreprises exerçant leur activité au Maroc.

Article 2 — Les dispositions du présent code sont d'ordre public.
Toute convention contraire est nulle de plein droit.

Article 3 — Les litiges relatifs à l'application du présent code relèvent
de la juridiction compétente.
"""


def test_split_by_articles_detects_structure():
    sections = split_by_articles(ARTICLE_TEXT)
    assert len(sections) == 3
    assert sections[0].startswith("Article 1")


def test_split_by_articles_returns_empty_without_structure():
    assert split_by_articles("Un texte quelconque sans structure d'article.") == []


def test_chunk_document_uses_article_method_when_structured():
    chunks = chunk_document(ARTICLE_TEXT, metadata={"domain": "travail"})
    assert len(chunks) == 3
    assert all(c.metadata["method"] == "article" for c in chunks)
    assert all(c.metadata["domain"] == "travail" for c in chunks)


def test_chunk_document_falls_back_to_size_without_structure():
    text = "Phrase un. " * 200  # pas de structure d'article, texte long
    chunks = chunk_document(text)
    assert len(chunks) >= 1
    assert all(c.metadata["method"] == "size" for c in chunks)


def test_chunk_document_empty_text_returns_no_chunks():
    assert chunk_document("") == []
    assert chunk_document("   ") == []


def test_split_by_size_respects_overlap():
    text = "Phrase numéro un. " * 100
    chunks = split_by_size(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    # Chaque chunk (sauf le premier) doit partager un préfixe avec la fin du précédent.
    for prev, cur in zip(chunks, chunks[1:]):
        assert cur[:20] in prev[-70:] or len(cur) < 20
