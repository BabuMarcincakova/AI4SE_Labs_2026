# Task 3 report

The Task 2 input contained 960 chunks, with a maximum chunk size of 1,997
characters. The model diagnostic successfully listed six models:
`gpt-4o-mini`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5.4-nano`,
`gpt-5.6-luna`, and `gpt-6-luna`. The three tested embedding models
(`text-embedding-3-large`, `text-embedding-ada-002`, and
`text-embedding-3-small`) were each rejected with
`PermissionDeniedError` (HTTP 403, model access unavailable). Therefore,
the fallback mode was used with `gpt-4o-mini`.

For each chunk, the fallback made one chat request asking for a two- or
three-sentence description and a keyword list. Results are cached by chunk
ID in `chunk_summaries.json`; all 960 requests succeeded and no summary
failures were recorded. The embedded representation is the relative path,
qualified symbol, cached description, keywords, and the original chunk
text. This combines exact code identifiers with a short semantic
description, which helps lexical retrieval when a query uses related words
rather than the exact source spelling. These are not neural embeddings:
they are locally generated TF-IDF lexical vectors enriched by LLM summaries.

The local vectorizer uses an identifier-aware tokenizer that keeps original
identifiers and also splits snake_case and camelCase components. It uses
lowercasing, sublinear term frequency, and L2 normalization. I compared
TruncatedSVD with no reduction using the ten targets in `missing_code.json`.
The 256-dimensional SVD representation found a chunk from the target file
for 9/10 targets and the exact target method for 6/10. The unreduced
representation found target files for 9/10 and exact target methods for
8/10, so the unreduced representation was selected. It has 2,633
dimensions. Every vector is normalized, making its dot product equivalent
to cosine similarity for Task 4.

Storage uses a float32 NumPy matrix in `chunk_vectors.npy` and a JSON list
in `chunk_metadata.json`. Metadata rows have the same order as matrix rows
and include the chunk ID, source, line range, kind, symbol, character
count, and complete text. The fitted TF-IDF vectorizer is stored with
joblib so query and chunk transformations use identical vocabulary and
tokenization. This repository has only 960 chunks, so an in-memory matrix
and exact NumPy search are simpler and faster than introducing a vector
database. A vector database would become worthwhile for much larger
collections, persistent multi-user indexes, or approximate nearest-neighbor
search.

Validation passed all checks: vector count, metadata count, and Task 2
chunk count were each 960; vectors were finite, non-zero, and unit
normalized; IDs were unique and matched Task 2; query embedding had the
same 2,633 dimensions and unit norm; and re-embedding a stored chunk had
cosine similarity above 0.99999. The output sizes were 10,110,848 bytes
for the vector matrix, 472,236 bytes for metadata, 543,856 bytes for the
summary cache, and 68,599 bytes for the vectorizer.

Limitations are lexical mismatch risk, dependence on summary quality, and
the API requirement during indexing. Queries do not require API calls in
this mode, because they use the persisted local vectorizer directly.
