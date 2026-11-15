"""Chunk a source repository into metadata-rich JSONL records."""

from __future__ import annotations

import argparse
import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

TARGET_MAX_CHARS = 2000
MIN_CHARS = 200
OVERLAP_LINES = 5

EXCLUDED_DIRECTORIES = {".git", "__pycache__", "node_modules", ".venv", "venv", "env"}
INCLUDED_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".yaml", ".yml",
    ".rst", ".csv", ".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".xml",
}
INCLUDED_FILENAMES = {".gitignore", "Dockerfile", "Makefile"}


@dataclass(frozen=True)
class Unit:
    start: int
    end: int
    kind: str
    symbol: str | None


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _line_text(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1:end])


def _node_start(node: ast.AST) -> int:
    starts = [getattr(node, "lineno", 1)]
    starts.extend(getattr(decorator, "lineno", starts[0]) for decorator in getattr(node, "decorator_list", []))
    return min(starts)


def _is_class_level_statement(node: ast.stmt) -> bool:
    return not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))


def _python_units(tree: ast.Module) -> list[Unit]:
    units: list[Unit] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            units.append(Unit(_node_start(node), node.end_lineno or node.lineno, "function", node.name))
        elif isinstance(node, ast.ClassDef):
            methods = [
                child for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            header_end = (_node_start(methods[0]) - 1) if methods else (node.end_lineno or node.lineno)
            if header_end >= _node_start(node):
                units.append(Unit(_node_start(node), header_end, "class_header", node.name))
            for method in methods:
                units.append(
                    Unit(
                        _node_start(method),
                        method.end_lineno or method.lineno,
                        "method",
                        f"{node.name}.{method.name}",
                    )
                )
        else:
            end = getattr(node, "end_lineno", getattr(node, "lineno", 1))
            units.append(Unit(node.lineno, end, "module", None))
    return sorted(units, key=lambda unit: (unit.start, unit.end, unit.kind))


def _line_windows(
    lines: list[str],
    start: int,
    end: int,
    max_chars: int,
    kind: str,
    symbol: str | None,
) -> Iterator[tuple[int, int, str, str | None]]:
    current = start
    while current <= end:
        window_end = current
        char_count = 0
        while window_end <= end:
            next_count = char_count + len(lines[window_end - 1])
            if window_end > current and next_count > max_chars:
                break
            char_count = next_count
            window_end += 1
            if next_count >= max_chars:
                break
        final_end = window_end - 1
        if final_end < current:
            final_end = current
        yield current, final_end, kind, symbol
        if final_end >= end:
            break
        current = max(current + 1, final_end - OVERLAP_LINES + 1)


def _emit_unit(
    lines: list[str],
    unit: Unit,
    max_chars: int,
) -> Iterator[tuple[int, int, str, str | None]]:
    text = _line_text(lines, unit.start, unit.end)
    if len(text) <= max_chars:
        yield unit.start, unit.end, unit.kind, unit.symbol
    else:
        yield from _line_windows(lines, unit.start, unit.end, max_chars, unit.kind, unit.symbol)


def _text_units(lines: list[str], max_chars: int) -> Iterator[tuple[int, int, str, str | None]]:
    start = 1
    while start <= len(lines):
        end = start
        chars = 0
        while end <= len(lines):
            candidate = chars + len(lines[end - 1])
            if end > start and candidate > max_chars:
                break
            chars = candidate
            end += 1
            if candidate >= max_chars:
                break
        final_end = end - 1
        if final_end < start:
            final_end = start
        while final_end > start and not lines[final_end - 1].strip():
            final_end -= 1
        yield start, final_end, "text_window", None
        if final_end >= len(lines):
            break
        next_start = max(start + 1, final_end - OVERLAP_LINES + 1)
        while next_start <= len(lines) and not lines[next_start - 1].strip():
            next_start += 1
        start = next_start


def _chunks_for_file(path: Path, source: str, relative: str, max_chars: int) -> list[dict[str, object]]:
    lines = source.splitlines(keepends=True)
    units: Iterable[tuple[int, int, str, str | None]]
    if path.suffix.lower() == ".py":
        try:
            tree = ast.parse(source, filename=relative)
            units = (part for unit in _python_units(tree) for part in _emit_unit(lines, unit, max_chars))
        except SyntaxError:
            units = _line_windows(lines, 1, len(lines), max_chars, "text_window", None)
    else:
        units = _text_units(lines, max_chars)

    chunks: list[dict[str, object]] = []
    for index, (line_start, line_end, kind, symbol) in enumerate(units):
        text = _line_text(lines, line_start, line_end)
        chunks.append(
            {
                "id": f"{relative}::{symbol or kind}::{index}",
                "source": relative,
                "chunk_index": index,
                "line_start": line_start,
                "line_end": line_end,
                "kind": kind,
                "symbol": symbol,
                "char_count": len(text),
                "text": text,
            }
        )
    return chunks


def _iter_files(repo: Path) -> Iterator[tuple[Path, str | None]]:
    for root, directories, filenames in os.walk(repo):
        directories[:] = sorted(directories)
        filenames.sort()
        excluded = [name for name in directories if name in EXCLUDED_DIRECTORIES]
        directories[:] = [name for name in directories if name not in EXCLUDED_DIRECTORIES]
        for directory in excluded:
            excluded_root = Path(root) / directory
            for excluded_file in sorted(path for path in excluded_root.rglob("*") if path.is_file()):
                yield excluded_file, "excluded directory"
        for filename in filenames:
            path = Path(root) / filename
            relative = path.relative_to(repo).as_posix()
            if path.name not in INCLUDED_FILENAMES and path.suffix.lower() not in INCLUDED_EXTENSIONS:
                yield path, "excluded extension"
            else:
                yield path, None


def chunk_repository(
    repo: Path,
    output: Path,
    skipped_output: Path,
    max_chars: int = TARGET_MAX_CHARS,
) -> list[dict[str, object]]:
    """Chunk supported text files under *repo* and write JSONL and skip records."""
    chunks: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    for path, exclusion in _iter_files(repo):
        relative = path.relative_to(repo).as_posix()
        if exclusion:
            skipped.append({"path": relative, "reason": exclusion})
            continue
        try:
            raw = path.read_bytes()
            if b"\x00" in raw:
                skipped.append({"path": relative, "reason": "binary"})
                continue
            source = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped.append({"path": relative, "reason": "binary"})
            continue
        if not source.strip():
            skipped.append({"path": relative, "reason": "empty"})
            continue
        chunks.extend(_chunks_for_file(path, source, relative, max_chars))

    chunks.sort(key=lambda chunk: (str(chunk["source"]), int(chunk["chunk_index"])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")
    with skipped_output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(sorted(skipped, key=lambda item: item["path"]), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return chunks


def load_chunks(path: str | Path) -> list[dict[str, object]]:
    """Load chunk records from a JSONL file."""
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    """Parse command-line arguments and chunk the repository."""
    parser = argparse.ArgumentParser(description=__doc__)
    default_repo = Path(__file__).parent.parent / "Task_1" / "AI4SE_Playground"
    parser.add_argument("--repo", type=Path, default=default_repo)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "repository_chunks.jsonl")
    parser.add_argument("--skipped-output", type=Path, default=Path(__file__).parent / "skipped_files.json")
    parser.add_argument("--max-chars", type=int, default=TARGET_MAX_CHARS)
    args = parser.parse_args()
    chunks = chunk_repository(args.repo, args.output, args.skipped_output, args.max_chars)
    print(f"Wrote {len(chunks)} chunks to {args.output}")


if __name__ == "__main__":
    main()
