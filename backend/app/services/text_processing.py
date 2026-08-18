"""Text preprocessing utilities shared by all services."""
from __future__ import annotations

import re
import string
from typing import Iterable, List

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Lazy / quiet download
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)
try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet", quiet=True)


_LEMMATIZER = WordNetLemmatizer()
_STOPWORDS = set(stopwords.words("english"))

# Common technical tokens we want to preserve as single units
_PRESERVE = {
    "node.js", "next.js", "vue.js", "react.js", "ci/cd", "rest api",
    "aws", "gcp", "nlp", "ml", "mlops", "etl", "bi", "ui/ux",
    "c++", "c#", ".net", "objective-c", "no-sql", "scikit-learn",
    "pytorch", "tensorflow", "pandas", "numpy", "scipy",
    "postgresql", "mongodb", "mysql", "redis", "kafka", "airflow",
    "kubernetes", "terraform", "graphql", "html", "css",
}

_PUNCT_RE = re.compile(f"[{re.escape(string.punctuation)}]")


def normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip control characters."""
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def clean_text(text: str) -> str:
    """Normalize + remove punctuation but keep well-known tech tokens."""
    text = normalize_text(text)
    # Replace preserve tokens with sentinel placeholders, restore after punting
    # punctuation. We use a dedicated token pattern that survives punctuation
    # stripping (sentinels contain underscores + digits, no chars we strip).
    sentinels: list[tuple[str, str]] = []  # (sentinel, original_token)
    for idx, token in enumerate(_PRESERVE):
        sentinel = f"PRESERVEDTOKEN{idx}PRESERVED"
        if token in text:
            sentinels.append((sentinel, token))
            text = text.replace(token, sentinel)
    text = _PUNCT_RE.sub(" ", text)
    for sentinel, token in sentinels:
        text = text.replace(sentinel, token)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    """Tokenize text after cleaning."""
    cleaned = clean_text(text)
    if not cleaned:
        return []
    return [t for t in cleaned.split(" ") if t]


def lemmatize_tokens(tokens: Iterable[str]) -> List[str]:
    """Lemmatize tokens and remove generic English stopwords."""
    out: list[str] = []
    for tok in tokens:
        if not tok or tok in _STOPWORDS or len(tok) <= 1:
            continue
        lemma = _LEMMATIZER.lemmatize(tok)
        if lemma and lemma not in _STOPWORDS:
            out.append(lemma)
    return out


def preprocess(text: str) -> str:
    """Full preprocess pipeline -> cleaned string suitable for TF-IDF."""
    return " ".join(lemmatize_tokens(tokenize(text)))


def split_into_lines(text: str) -> List[str]:
    """Split into clean single-line entries."""
    return [line.strip() for line in text.splitlines() if line.strip()]
