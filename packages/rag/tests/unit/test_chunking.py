from opscopilot_rag.chunking import chunk_text


def test_chunk_text_applies_overlap():
    text = "abcdefghij"
    chunks = chunk_text("doc", text, chunk_size=4, chunk_overlap=1)
    assert [chunk.text for chunk in chunks] == ["abcd", "defg", "ghij"]


def test_chunk_text_validates_overlap():
    try:
        chunk_text("doc", "data", chunk_size=4, chunk_overlap=4)
    except ValueError as exc:
        assert "chunk_overlap" in str(exc)
    else:
        raise AssertionError("expected ValueError")
