# Task 4 report

Task 3 uses the fallback representation: TF-IDF vectors enriched with
cached `gpt-4o-mini` summaries, not neural embeddings. The selected storage
contains 960 chunks with 2,633 dimensions, and the vectors are L2
normalized. `retrieve.py` uses `embed_query` from Task 3, which transforms
queries locally with the persisted vectorizer and does not make an API call.

The index uses cosine similarity. This compares vector direction rather than
magnitude, which is appropriate for text representations whose magnitude can
vary with chunk length. Because Task 3 normalizes vectors, cosine similarity
is a dot product, so each query requires one NumPy matrix-vector product.
The implementation re-normalizes loaded rows defensively and never returns
zero-norm or non-finite rows. It accepts one-dimensional queries and
single-row two-dimensional queries, and reports clear errors for invalid
norms, non-finite values, or dimension mismatches.

Search is exact brute-force NumPy search rather than an ANN index or vector
database. For 960 chunks this is simple, predictable, and returns exact
results. The measured mean for 100 repeated retrievals was 1.269786 ms.
FAISS, HNSW, or another ANN system would become worthwhile for a much larger
collection or when latency and memory requirements make scanning every
chunk expensive. The top-n implementation uses `np.argpartition` for
linear-time candidate selection and sorts only the selected results. The
default is five because Task 5 uses the top five as its prompt context.

Each result includes rank and score for diagnostics, ID and symbol for
retrieval checks, source and line range for traceability, and the complete
text for prompt construction. `format_chunks_for_prompt` renders those
fields as readable source blocks. A lazily initialized default index avoids
reloading storage across repeated Task 5 calls.

All synthetic unit checks passed, including ordering, identical-vector score
1.0, oversized n, invalid n, empty storage, dimension mismatch, zero query,
and deterministic ties. Self-retrieval passed for five stored chunks; each
returned itself first with a score of approximately 1.0. For the ten
`missing_code.json` queries, the target file appeared in the top five for
9/10 and the exact target method appeared for 8/10. The target-file hit rate
was 6/10 for n=1, 9/10 for n=3, 9/10 for n=5, and 10/10 for n=8.

The two target methods not found in the top five were
`Customer.can_afford` and `BulkDiscountPricing.price`. The latter also
missed its target file; the former retrieved another chunk from the correct
file. Retrieval has no re-ranking, hybrid keyword fusion, or similarity
threshold, and its quality is bounded by the lexical TF-IDF representation
and cached summary quality.
