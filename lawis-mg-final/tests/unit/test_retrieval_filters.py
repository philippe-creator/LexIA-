"""Régression : un filtre vide (« Tous types » / « Toutes années » → "") ne doit
pas être appliqué comme filtre littéral, sinon Chroma ne renvoie plus rien."""
import retrieval.hybrid_retriever as hr


def _stub_retrieval(monkeypatch):
    """Neutralise la pile ML et capture les doc_type/year vus par la recherche."""
    seen = {}

    def fake_vector(variant, domains, n_results_per_domain, user_id, doc_type, year):
        seen["vector"] = (doc_type, year)
        return []

    def fake_keyword(variant, domain, n_results, doc_type=None, year=None):
        seen["keyword"] = (doc_type, year)
        return []

    monkeypatch.setattr(hr, "route_query", lambda q: ["travail"])
    monkeypatch.setattr(hr, "expand_query", lambda q, n: [q])
    monkeypatch.setattr(hr, "multi_domain_vector_search", fake_vector)
    monkeypatch.setattr(hr, "keyword_search", fake_keyword)
    monkeypatch.setattr(hr, "rerank", lambda q, docs, top_k: docs)
    monkeypatch.setattr(hr, "compute_confidence", lambda docs: (0.0, "insuffisant"))
    return seen


def test_empty_string_filters_become_none(monkeypatch):
    seen = _stub_retrieval(monkeypatch)
    hr.retrieve("c'est quoi le travail ?", doc_type="", year="")
    assert seen["vector"] == (None, None)
    assert seen["keyword"] == (None, None)


def test_whitespace_filters_become_none(monkeypatch):
    seen = _stub_retrieval(monkeypatch)
    hr.retrieve("question", doc_type="   ", year="  ")
    assert seen["vector"] == (None, None)


def test_real_filters_are_preserved(monkeypatch):
    seen = _stub_retrieval(monkeypatch)
    hr.retrieve("question", doc_type="loi", year=2025)
    assert seen["vector"] == ("loi", 2025)
