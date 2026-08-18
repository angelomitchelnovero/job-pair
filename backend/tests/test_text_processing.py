"""Tests for text preprocessing utilities."""
from app.services.text_processing import (
    clean_text,
    lemmatize_tokens,
    normalize_text,
    preprocess,
    tokenize,
)


def test_normalize_text_lowercases_and_collapsed():
    assert normalize_text("  Hello   World  ") == "hello world"
    assert normalize_text("FOO\tBAR") == "foo bar"


def test_clean_text_preserves_tech_tokens():
    txt = "We love Node.js, Vue.js, scikit-learn and CI/CD"
    cleaned = clean_text(txt)
    assert "nodejs" in cleaned or "node js" in cleaned
    assert "vuejs" in cleaned or "vue js" in cleaned
    assert "scikit learn" in cleaned or "sklearn" in cleaned
    assert "ci/cd" in cleaned or "ci cd" in cleaned


def test_tokenize_returns_lowercased_words():
    tokens = tokenize("Build React Apps with TypeScript")
    assert all(t == t.lower() for t in tokens)


def test_lemmatize_tokens_drops_stopwords():
    out = lemmatize_tokens(["running", "is", "the", "code"])
    assert "running" in out or "run" in out
    assert "the" not in out
    assert "is" not in out


def test_preprocess_empty():
    assert preprocess("") == ""


def test_preprocess_round_trip():
    out = preprocess("Python developer with FastAPI experience")
    assert "python" in out
    assert "developer" in out or "develop" in out
