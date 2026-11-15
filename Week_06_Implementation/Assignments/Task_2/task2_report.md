# Task 2 report

The input repository contains 27 Python files. The inspection found 103
classes and 698 definitions, including 689 indented methods. The largest
file has 498 lines, and the only empty or trivially small file is
`playground/tests/__init__.py`, which is empty. The repository has three
non-Python text windows in addition to the Python chunks. The ten entries in
`missing_code.json` all identify class methods, so preserving method symbols
was important for retrieval.

The chunker uses a maximum of 2,000 characters, with `MIN_CHARS = 200` kept
as the named threshold for future small-unit merging and
`OVERLAP_LINES = 5` for line-window splitting. About 2,000 characters is
approximately 500 tokens for common source text, so it fits typical
embedding-model limits without truncation. It also keeps individual
embeddings focused and leaves room for five retrieved chunks in a later LLM
context, while usually being large enough to retain a complete method and
its docstring. The measured output had 960 chunks: the minimum was 11
characters, the maximum was 1,997, the mean was 174.34, and the median was
142 characters. No chunk exceeded 2,000 characters; 174 were shorter than
50 characters.

Python files are parsed with `ast`. Top-level functions, class headers, and
individual methods become separate units, with decorators and docstrings
remaining in the exact source slice. This is preferable to fixed windows
because the later tasks retrieve methods, and a method-sized chunk avoids
cutting a function in half or diluting its embedding with unrelated code.
Class headers retain the class signature, docstring, and leading
class-level context. Oversized units use line windows with five-line
overlap. If parsing fails, the whole Python file falls back to those
windows. Non-Python text uses the same bounded line-window approach and
prefers ending before blank lines. Small units are retained rather than
silently discarded, so every non-skipped file remains represented.

The walker includes source and documentation extensions such as `.py`,
`.md`, `.txt`, `.json`, `.toml`, `.cfg`, `.yaml`, and `.yml`, plus common
extensionless files such as `.gitignore`. It excludes `.git`,
`__pycache__`, `node_modules`, and virtual-environment directories, as well
as unsupported extensions, binary or non-UTF-8 files, and whitespace-only
files. In this run the skipped-file summary was one `empty` file:
`playground/tests/__init__.py`. There were no binary, excluded-extension,
or excluded-directory records in the output because the repository's
discovered files did not produce those cases.

Chunks are stored as JSONL so each record can be streamed or loaded
independently. Every record contains an `id` for linking to future
embeddings, `source` and `line_start`/`line_end` for constructing prompts,
`chunk_index` for stable ordering, `kind` and `symbol` for retrieval and
target checks, `char_count` for filtering, and exact `text` for context.
The output is deterministic: two runs produced identical chunk and skipped
files output. Validation found unique IDs, non-empty text, valid line
ranges, no Python non-blank-line coverage gaps, and exact source-text
matches for the five sampled chunks. All ten targets from
`missing_code.json` had matching symbol/file chunks.

The main limitation is that class-level context is separate from method
chunks; class-header chunks and qualified symbols partly address that
separation. Non-Python files use plain windows rather than syntax-aware
units, and character count is only an approximation of token count.
