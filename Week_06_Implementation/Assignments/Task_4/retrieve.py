"""Retrieve the most relevant repository chunks by cosine similarity."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

TASK3_DIR = Path(__file__).resolve().parent.parent / "Task_3"
if str(TASK3_DIR) not in sys.path:
    sys.path.insert(0, str(TASK3_DIR))

from embed_chunks import embed_query, load_storage


class ChunkIndex:
    """An in-memory exact cosine-similarity index over stored chunks."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        vectors, metadata = load_storage(storage_dir)
        self.metadata = list(metadata)
        self.vectors = np.asarray(vectors, dtype=np.float32)
        if self.vectors.ndim != 2:
            raise ValueError(f"Expected a 2-D vector matrix, got {self.vectors.ndim}-D.")
        if self.vectors.shape[0] != len(self.metadata):
            raise ValueError(
                f"Vector rows ({self.vectors.shape[0]}) do not match "
                f"metadata length ({len(self.metadata)})."
            )
        norms = np.linalg.norm(self.vectors, axis=1)
        nonzero = norms > 0
        self.vectors[nonzero] /= norms[nonzero, None]
        self._valid = nonzero & np.isfinite(norms)

    def retrieve_top_n(self, query_embedding: Any, n: int = 5) -> list[dict[str, Any]]:
        """Return up to *n* valid chunks ordered by descending cosine score."""
        if n < 1:
            raise ValueError("n must be at least 1.")
        if self.vectors.shape[0] == 0:
            return []
        query = np.asarray(query_embedding, dtype=np.float32)
        if query.ndim == 2:
            if query.shape[0] != 1:
                raise ValueError("query_embedding must have shape (dim,) or (1, dim).")
            query = query[0]
        if query.ndim != 1:
            raise ValueError("query_embedding must have shape (dim,) or (1, dim).")
        dimension = self.vectors.shape[1]
        if query.shape[0] != dimension:
            raise ValueError(
                f"Query dimension ({query.shape[0]}) does not match index dimension ({dimension})."
            )
        if not np.isfinite(query).all():
            raise ValueError("query_embedding must contain only finite values.")
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            raise ValueError("query_embedding must have a non-zero norm.")
        query = query / query_norm
        scores = self.vectors @ query
        scores[~self._valid] = -np.inf
        count = min(n, self.vectors.shape[0])
        indices = np.flatnonzero(self._valid)
        if len(indices) == 0:
            return []
        count = min(count, len(indices))
        valid_scores = scores[indices]
        tie_break = np.finfo(np.float32).eps * indices.astype(np.float32)
        selected = np.argpartition(-(valid_scores - tie_break), count - 1)[:count]
        selected_indices = indices[selected]
        selected_indices = sorted(selected_indices.tolist(), key=lambda index: (-float(scores[index]), index))
        return [
            {
                "rank": rank,
                "score": float(scores[index]),
                **{key: self.metadata[index].get(key) for key in (
                    "id", "source", "line_start", "line_end", "kind", "symbol", "char_count", "text"
                )},
            }
            for rank, index in enumerate(selected_indices, 1)
        ]


_default_index: ChunkIndex | None = None


def retrieve_for_text(
    task_text: str,
    n: int = 5,
    index: ChunkIndex | None = None,
) -> list[dict[str, Any]]:
    """Embed text locally and retrieve its top matching chunks."""
    global _default_index
    active_index = index
    if active_index is None:
        if _default_index is None:
            _default_index = ChunkIndex()
        active_index = _default_index
    return active_index.retrieve_top_n(embed_query(task_text), n)


def format_chunks_for_prompt(results: list[dict[str, Any]]) -> str:
    """Render retrieved chunks as readable prompt blocks."""
    blocks = []
    for result in results:
        symbol = result.get("symbol") or "(module)"
        blocks.append(
            f"Source: {result['source']}:{result['line_start']}-{result['line_end']}\n"
            f"Symbol: {symbol}\n"
            f"Code:\n{result['text']}"
        )
    return "\n\n".join(blocks)


def main() -> None:
    """Run retrieval from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Task description to search for.")
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--show-text", action="store_true")
    args = parser.parse_args()
    for result in retrieve_for_text(args.query, args.n):
        symbol = result.get("symbol") or "(module)"
        print(
            f"{result['rank']}. score={result['score']:.6f} id={result['id']} "
            f"source={result['source']} lines={result['line_start']}-{result['line_end']} "
            f"symbol={symbol}"
        )
        if args.show_text:
            print(result["text"])


if __name__ == "__main__":
    main()
