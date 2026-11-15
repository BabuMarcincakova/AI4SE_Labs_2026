"""Build and load lexical chunk vectors enriched with cached chat summaries."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

CHUNK_MODEL = "gpt-4o-mini"
SUMMARY_PATH = Path(__file__).parent / "chunk_summaries.json"
FAILURES_PATH = Path(__file__).parent / "summary_failures.json"
VECTORIZER_PATH = Path(__file__).parent / "tfidf_vectorizer.joblib"
SVD_PATH = Path(__file__).parent / "tfidf_svd.joblib"
VECTORS_PATH = Path(__file__).parent / "chunk_vectors.npy"
METADATA_PATH = Path(__file__).parent / "chunk_metadata.json"
MAX_SUMMARY_RETRIES = 2
SVD_MAX_COMPONENTS = 256
USE_SVD = False

_vectorizer: TfidfVectorizer | None = None
_svd: TruncatedSVD | None = None
_summaries: dict[str, dict[str, Any]] = {}
_metadata: list[dict[str, Any]] = []


def identifier_tokens(text: str) -> list[str]:
    """Return original identifiers and their snake/camel-case components."""
    identifiers = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
    tokens: list[str] = []
    for identifier in identifiers:
        tokens.append(identifier)
        parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier).split("_")
        tokens.extend(part.lower() for part in parts if part)
    return tokens


def _tokenizer(text: str) -> list[str]:
    return identifier_tokens(text)


def build_embedding_text(chunk: dict[str, Any]) -> str:
    """Compose the path, symbol, cached summary, keywords, and source text."""
    summary = _summaries.get(str(chunk["id"]), {})
    description = str(summary.get("description", ""))
    keywords = summary.get("keywords", [])
    keyword_text = " ".join(str(keyword) for keyword in keywords)
    return "\n".join(
        [
            f"path: {chunk['source']}",
            f"symbol: {chunk.get('symbol') or ''}",
            f"summary: {description}",
            f"keywords: {keyword_text}",
            "code:",
            str(chunk["text"]),
        ]
    )


def _load_summary_cache() -> None:
    global _summaries
    if SUMMARY_PATH.exists():
        _summaries = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def _save_summary_cache() -> None:
    SUMMARY_PATH.write_text(
        json.dumps(_summaries, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parse_summary(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        return {
            "description": str(parsed.get("description", "")),
            "keywords": [str(item) for item in parsed.get("keywords", [])],
        }
    except (json.JSONDecodeError, AttributeError):
        return {"description": content.strip(), "keywords": []}


def _summarize_chunk(client: OpenAI, chunk: dict[str, Any]) -> dict[str, Any]:
    prompt = (
        "Describe this code chunk in 2-3 plain-language sentences. Return JSON with "
        'exactly two fields: "description" (string) and "keywords" (array of strings). '
        "Include class, method, and important concept names in keywords.\n\n"
        f"Path: {chunk['source']}\nSymbol: {chunk.get('symbol') or ''}\nCode:\n{chunk['text']}"
    )
    last_error: Exception | None = None
    for attempt in range(MAX_SUMMARY_RETRIES + 1):
        try:
            kwargs: dict[str, Any] = {
                "model": CHUNK_MODEL,
                "messages": [
                    {"role": "system", "content": "You summarize source code accurately and concisely."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            }
            if attempt == 1:
                kwargs.pop("temperature")
                kwargs["max_completion_tokens"] = 180
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            return _parse_summary(content)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"summary failed after retries: {type(last_error).__name__}") from last_error


def _ensure_summaries(chunks: list[dict[str, Any]]) -> list[str]:
    """Populate the persistent summary cache and return failed chunk IDs."""
    _load_summary_cache()
    failures: list[str] = []
    load_dotenv(Path(__file__).resolve().parents[2] / "API_key_6.env")
    client = OpenAI()
    for chunk in chunks:
        chunk_id = str(chunk["id"])
        if chunk_id in _summaries:
            continue
        try:
            _summaries[chunk_id] = _summarize_chunk(client, chunk)
        except RuntimeError:
            _summaries[chunk_id] = {"description": "", "keywords": []}
            failures.append(chunk_id)
        _save_summary_cache()
    FAILURES_PATH.write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
    return failures


def _fit_vectorizer(chunks: list[dict[str, Any]]) -> np.ndarray:
    global _vectorizer, _svd, _metadata
    texts = [build_embedding_text(chunk) for chunk in chunks]
    _vectorizer = TfidfVectorizer(
        tokenizer=_tokenizer,
        token_pattern=None,
        lowercase=True,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = _vectorizer.fit_transform(texts)
    _svd = None
    if USE_SVD and min(256, len(chunks) - 1, matrix.shape[1] - 1) >= 2:
        _svd = TruncatedSVD(
            n_components=min(SVD_MAX_COMPONENTS, len(chunks) - 1, matrix.shape[1] - 1),
            random_state=0,
        )
        matrix = _svd.fit_transform(matrix)
        matrix = normalize(matrix, norm="l2")
    _metadata = [
        {
            key: chunk[key]
            for key in (
                "id", "source", "line_start", "line_end", "kind", "symbol", "char_count", "text"
            )
        }
        for chunk in chunks
    ]
    return np.asarray(matrix.toarray() if hasattr(matrix, "toarray") else matrix, dtype=np.float32)


def _transform(texts: list[str]) -> np.ndarray:
    if _vectorizer is None:
        raise RuntimeError("Storage is not loaded; call load_storage first.")
    matrix = _vectorizer.transform(texts)
    if _svd is not None:
        matrix = _svd.transform(matrix)
    normalized = normalize(matrix, norm="l2")
    return np.asarray(normalized.toarray() if hasattr(normalized, "toarray") else normalized, dtype=np.float32)


def embed_chunk(chunk: dict[str, Any]) -> np.ndarray:
    """Embed one chunk in the persisted vector space."""
    return _transform([build_embedding_text(chunk)])[0]


def embed_chunks(chunks: list[dict[str, Any]]) -> np.ndarray:
    """Embed a batch of chunks in the persisted vector space."""
    return _transform([build_embedding_text(chunk) for chunk in chunks])


def embed_query(text: str) -> np.ndarray:
    """Embed a query using the same lexical representation without summaries."""
    return _transform([text])[0]


def load_storage(dir: str | Path | None = None) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Load vector storage and fitted transforms from a Task 3 directory."""
    global _vectorizer, _svd, _metadata, SUMMARY_PATH
    directory = Path(dir) if dir is not None else Path(__file__).parent
    _vectorizer = joblib.load(directory / VECTORIZER_PATH.name)
    svd_path = directory / SVD_PATH.name
    _svd = joblib.load(svd_path) if svd_path.exists() else None
    _metadata = json.loads((directory / METADATA_PATH.name).read_text(encoding="utf-8"))
    SUMMARY_PATH = directory / SUMMARY_PATH.name
    _load_summary_cache()
    return np.load(directory / VECTORS_PATH.name), _metadata


def generate(chunks_path: Path) -> tuple[int, int, list[str]]:
    """Generate summaries, fit transforms, and write all storage files."""
    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    failures = _ensure_summaries(chunks)
    vectors = _fit_vectorizer(chunks)
    joblib.dump(_vectorizer, VECTORIZER_PATH)
    if _svd is not None:
        joblib.dump(_svd, SVD_PATH)
    elif SVD_PATH.exists():
        SVD_PATH.unlink()
    np.save(VECTORS_PATH, vectors)
    METADATA_PATH.write_text(json.dumps(_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(chunks), vectors.shape[1], failures


def main() -> None:
    """Generate the Task 3 storage from Task 2 JSONL."""
    sys.modules.setdefault("embed_chunks", sys.modules[__name__])
    identifier_tokens.__module__ = "embed_chunks"
    _tokenizer.__module__ = "embed_chunks"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path(__file__).parent.parent / "Task_2" / "repository_chunks.jsonl",
    )
    args = parser.parse_args()
    count, dimension, failures = generate(args.chunks)
    print(f"mode=fallback model={CHUNK_MODEL} chunks={count} dimension={dimension}")
    print(f"api_calls={len(_summaries)} summary_failures={len(failures)}")
    if failures:
        print("failed_chunk_ids=" + json.dumps(failures))


if __name__ == "__main__":
    main()
