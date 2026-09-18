import numpy as np

from econsight.rag.grounding import (
    build_report,
    parse_citations,
    split_sentences,
)


def test_split_sentences_basic():
    s = split_sentences("CPI rose. Rates held steady! Why? Because inflation.")
    assert len(s) == 4


def test_parse_citations_extracts_indices():
    assert parse_citations("Inflation eased [1] then rose [3].") == {1, 3}
    assert parse_citations("No citations here.") == set()


class _FakeEncoder:
    """Encodes text as a 2-d vector by keyword, so cosine similarity is controllable."""
    def encode(self, texts):
        out = []
        for t in texts:
            t = t.lower()
            out.append([1.0, 0.0] if "inflation" in t else [0.0, 1.0])
        return np.array(out)


def test_build_report_flags_unsupported_sentence():
    chunks = [
        {"title": "Inflation", "text": "Inflation eased over the quarter."},
    ]
    answer = "Inflation eased steadily [1]. Unemployment surged unexpectedly."
    report = build_report(answer, chunks, encoder=_FakeEncoder(), threshold=0.5)
    # sentence 1 matches the inflation chunk; sentence 2 does not
    assert report["sentences"][0]["supported"] is True
    assert report["sentences"][1]["supported"] is False
    assert 0.0 <= report["groundedness"] <= 1.0
    assert report["groundedness"] == 0.5
    assert report["sources"][0]["chunk_id"] == 1


def test_build_report_empty_answer():
    report = build_report("", [], encoder=_FakeEncoder())
    assert report["groundedness"] is None
