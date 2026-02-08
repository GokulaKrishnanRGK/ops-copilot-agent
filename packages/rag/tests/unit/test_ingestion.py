from opscopilot_rag.ingestion import normalize_text


def test_normalize_text_removes_extra_blank_lines():
    raw = "line1\n\n\nline2\r\n\r\nline3  \n"
    normalized = normalize_text(raw)
    assert normalized == "line1\n\nline2\n\nline3"
