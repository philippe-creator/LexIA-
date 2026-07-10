from retrieval.reranker import compute_confidence


def test_empty_input_is_insuffisant():
    score, label = compute_confidence([])
    assert score == 0.0
    assert label == "insuffisant"


def test_rerank_score_used_directly_without_double_sigmoid():
    """Régression : rerank_score est déjà normalisé en [0,1] par le sigmoid
    appliqué dans rerank() — compute_confidence ne doit PAS le re-sigmoider
    (bug historique qui écrasait tous les scores vers ~0.5-0.7)."""
    score, label = compute_confidence([{"rerank_score": 0.95}])
    assert score == 0.95
    assert label == "élevé"


def test_rerank_score_zero_point_five_is_moyen_not_double_squashed():
    score, label = compute_confidence([{"rerank_score": 0.5}])
    assert score == 0.5
    assert label == "faible"


def test_fallback_to_rrf_score_when_no_reranker():
    score, label = compute_confidence([{"rrf_score": 0.03}])
    assert 0.5 < score < 0.51  # sigmoid(0.03) ≈ 0.5075
    assert label == "faible"


def test_labels_cover_full_range():
    assert compute_confidence([{"rerank_score": 0.9}])[1] == "élevé"
    assert compute_confidence([{"rerank_score": 0.7}])[1] == "moyen"
    assert compute_confidence([{"rerank_score": 0.5}])[1] == "faible"
    assert compute_confidence([{"rerank_score": 0.1}])[1] == "insuffisant"
