from retrieval import reranker


class _FakeCrossEncoder:
    """Renvoie le même logit pour toutes les paires — isole le test du vrai
    modèle (lent à charger) tout en laissant le boost par article agir seul."""
    def predict(self, pairs):
        return [0.0] * len(pairs)  # sigmoid(0) = 0.5 pour tous, avant boost


def test_article_boost_favors_matching_article(monkeypatch):
    monkeypatch.setattr(reranker, "get_reranker", lambda: _FakeCrossEncoder())
    candidates = [
        {"text": "Article 12 — Disposition sans rapport avec la question posée ici."},
        {"text": "Article 52 — L'indemnité de licenciement est calculée selon..."},
    ]
    result = reranker.rerank("Que dit l'article 52 sur l'indemnité ?", candidates, top_k=2)
    assert result[0]["text"].startswith("Article 52")
    assert result[0]["rerank_score"] > result[1]["rerank_score"]


def test_article_boost_is_capped_at_one(monkeypatch):
    class _HighScoreEncoder:
        def predict(self, pairs):
            return [10.0] * len(pairs)  # sigmoid(10) ≈ 0.9999, boost ne doit pas dépasser 1.0
    monkeypatch.setattr(reranker, "get_reranker", lambda: _HighScoreEncoder())
    candidates = [{"text": "Article 7 — Texte quelconque."}]
    result = reranker.rerank("article 7 ?", candidates, top_k=1)
    assert result[0]["rerank_score"] <= 1.0


def test_no_boost_when_query_has_no_article_reference(monkeypatch):
    monkeypatch.setattr(reranker, "get_reranker", lambda: _FakeCrossEncoder())
    candidates = [{"text": "Article 9 — Texte quelconque."}]
    result = reranker.rerank("Quels sont mes droits ?", candidates, top_k=1)
    assert result[0]["rerank_score"] == 0.5  # sigmoid(0), aucun boost appliqué
