from retrieval.hybrid_retriever import _rrf


def _doc(text: str) -> dict:
    return {"text": text, "metadata": {}}


def test_single_list_preserves_rank_order():
    docs = [_doc("Premier passage pertinent"), _doc("Second passage")]
    fused = _rrf([docs])
    assert [d["text"] for d in fused] == [d["text"] for d in docs]
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


def test_document_ranked_highly_in_both_lists_wins_fusion():
    shared = _doc("Passage présent dans les deux listes")
    list_a = [shared, _doc("Autre passage A")]
    list_b = [shared, _doc("Autre passage B")]
    fused = _rrf([list_a, list_b])
    assert fused[0]["text"] == shared["text"]


def test_dedup_by_text_prefix_keeps_first_occurrence():
    long_text = "x" * 200
    fused = _rrf([[{"text": long_text, "metadata": {"source": "a"}}], [{"text": long_text, "metadata": {"source": "b"}}]])
    assert len(fused) == 1
    assert fused[0]["metadata"]["source"] == "a"


def test_empty_lists_return_empty_fusion():
    assert _rrf([]) == []
    assert _rrf([[]]) == []
