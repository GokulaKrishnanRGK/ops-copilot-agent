from opscopilot_rag.retrieval import build_knn_query


def test_build_knn_query_includes_vector():
    query = build_knn_query([0.1, 0.2], top_k=3)
    assert query["size"] == 3
    assert query["query"]["knn"]["embedding"]["vector"] == [0.1, 0.2]
