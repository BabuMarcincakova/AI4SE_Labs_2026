"""Solve missing repository methods with retrieval-augmented LLM generation."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

TASK5_DIR = Path(__file__).resolve().parent
ASSIGNMENTS_DIR = TASK5_DIR.parent
REPO_DIR = ASSIGNMENTS_DIR / "Task_1" / "AI4SE_Playground"
TASKS_PATH = ASSIGNMENTS_DIR / "missing_code.json"
DEFAULT_LOG = TASK5_DIR / "run_log.json"
ALLOWED_MODELS = {
    "gpt-6-luna",
    "gpt-5.6-luna",
    "gpt-5.4-nano",
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-4.1-nano",
    "gpt-4o-mini",
}
DEFAULT_MODEL = "gpt-4o-mini"

TASK4_DIR = ASSIGNMENTS_DIR / "Task_4"
if str(TASK4_DIR) not in sys.path:
    sys.path.insert(0, str(TASK4_DIR))
from retrieve import ChunkIndex, format_chunks_for_prompt, retrieve_for_text


def _sanitize_error(exc: Exception) -> str:
    message = re.sub(r"(?i)(sk-[A-Za-z0-9_-]+|bearer\s+\S+)", "[redacted]", str(exc))
    return f"{type(exc).__name__}: {message}"


def _load_client() -> OpenAI:
    load_dotenv(Path(__file__).resolve().parents[2] / "API_key_6.env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY was not loaded.")
    return OpenAI(timeout=60.0)


def _find_target(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                    return child
    return None


def _defined_names(tree: ast.AST) -> set[tuple[str, str]]:
    names: set[tuple[str, str]] = set()

    def visit(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add((scope, child.name))
                visit(child, f"{scope}.{child.name}")
            else:
                visit(child, scope)

    visit(tree, "")
    return names


def _extract_code(response: str) -> str:
    fenced = re.search(r"```(?:python)?\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    return (fenced.group(1) if fenced else response).strip()


def _prepare_generated_method(code: str, original_indent: str, newline: str) -> tuple[str, list[str]]:
    parsed = ast.parse(code)
    imports: list[str] = []
    kept_lines = code.splitlines()
    import_line_numbers = set()
    for node in parsed.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.extend(code.splitlines()[node.lineno - 1:node.end_lineno])
            import_line_numbers.update(range(node.lineno, node.end_lineno + 1))
    method_nodes = [
        node for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len(method_nodes) != 1:
        raise ValueError("Generated response must contain exactly one method definition.")
    method_node = method_nodes[0]
    method_start = min([method_node.lineno] + [decorator.lineno for decorator in method_node.decorator_list])
    method_lines = code.splitlines()[method_start - 1:method_node.end_lineno]
    if not method_lines:
        raise ValueError("Generated method is empty.")
    dedented = textwrap.dedent("\n".join(method_lines))
    indented = "\n".join(
        original_indent + line if line.strip() else line
        for line in dedented.splitlines()
    )
    return indented.replace("\n", newline), imports


def _merge_imports(source: str, imports: list[str], newline: str) -> str:
    if not imports:
        return source
    lines = source.splitlines(keepends=True)
    existing = {line.strip() for line in lines if line.lstrip().startswith(("import ", "from "))}
    additions = [line for line in imports if line.strip() not in existing]
    if not additions:
        return source
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    while insert_at < len(lines) and (
        lines[insert_at].startswith("#") or not lines[insert_at].strip()
    ):
        insert_at += 1
    rendered = [line.rstrip("\r\n") + newline for line in additions]
    lines[insert_at:insert_at] = rendered
    return "".join(lines)


def patch_target(repo: Path, target: dict[str, Any], generated: str) -> None:
    """Replace exactly one target method after AST and name-set validation."""
    path = repo / Path(target["file"])
    source_bytes = path.read_bytes()
    newline = "\r\n" if b"\r\n" in source_bytes else "\n"
    source = source_bytes.decode("utf-8")
    tree = ast.parse(source, filename=str(path))
    method = _find_target(tree, target["class"], target["method"])
    if method is None:
        raise ValueError("Target method was not found.")
    original_names = _defined_names(tree)
    lines = source.splitlines(keepends=True)
    start = min([method.lineno] + [decorator.lineno for decorator in method.decorator_list]) - 1
    end = method.end_lineno
    indent = " " * method.col_offset
    replacement, imports = _prepare_generated_method(generated, indent, newline)
    new_source = "".join(lines[:start]) + replacement + newline + "".join(lines[end:])
    new_source = _merge_imports(new_source, imports, newline)
    new_tree = ast.parse(new_source, filename=str(path))
    if _defined_names(new_tree) != original_names:
        raise ValueError("Generated patch changed the set of defined names.")
    path.write_bytes(new_source.encode("utf-8"))


def _target_stub(repo: Path, target: dict[str, Any]) -> str:
    path = repo / Path(target["file"])
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = _find_target(tree, target["class"], target["method"])
    if method is None:
        raise ValueError("Target method was not found.")
    lines = source.splitlines(keepends=True)
    start = min([method.lineno] + [decorator.lineno for decorator in method.decorator_list]) - 1
    return "".join(lines[start:method.end_lineno]).rstrip()


def _supporting_context(repo: Path, target: dict[str, Any]) -> str:
    """Return the target class and imported local definitions as extra API context."""
    path = repo / Path(target["file"])
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {target["class"]}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            wanted.update(alias.name for alias in node.names if alias.name != "*")
    blocks: list[str] = []
    for candidate in sorted(repo.rglob("*.py")):
        candidate_source = candidate.read_text(encoding="utf-8")
        try:
            candidate_tree = ast.parse(candidate_source)
        except SyntaxError:
            continue
        lines = candidate_source.splitlines(keepends=True)
        for node in candidate_tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
                blocks.append(
                    f"{candidate.relative_to(repo).as_posix()}:\n"
                    + "".join(lines[node.lineno - 1:node.end_lineno]).rstrip()
                )
    return "\n\n".join(blocks)


def _build_prompt(task_text: str, target: dict[str, Any], stub: str, results: list[dict[str, Any]]) -> str:
    return f"""Complete the missing method in an existing Python codebase.
Follow the repository's style and existing APIs. Return ONLY the complete method
definition, including its signature and docstring, in a single ```python block.
Do not include explanations. Use only imports that already exist, or list any
needed new imports as separate lines at the top of the block.

Task description:
{task_text}

Target:
file: {target['file']}
class: {target['class']}
method: {target['method']}
current stub with exact signature:
{stub}

Relevant existing local API definitions:
{_supporting_context(REPO_DIR, target)}

Retrieved repository context:
{format_chunks_for_prompt(results)}
"""


def _call_model(client: OpenAI, prompt: str, model: str) -> tuple[str, dict[str, Any]]:
    base = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You complete missing methods accurately and return only requested code."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        response = client.chat.completions.create(**base, temperature=0, timeout=60)
    except Exception as exc:
        if getattr(exc, "status_code", None) == 400 and "temperature" in str(exc).lower():
            response = client.chat.completions.create(**base, max_completion_tokens=500, timeout=60)
        else:
            raise
    usage = {}
    if response.usage is not None:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    return response.choices[0].message.content or "", usage


def solve_task(
    task_text: str,
    target: dict[str, Any],
    model: str,
    top_n: int = 5,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate code with the LLM and print it, but do not modify any files.

    This still makes one API call per task.
    """
    if model not in ALLOWED_MODELS:
        raise ValueError(f"Model is not allowed: {model}")
    query = f"{target['class']} {target['method']} {task_text}"
    results = retrieve_for_text(query, n=top_n)
    result: dict[str, Any] = {
        "task": f"{target['class']}.{target['method']}",
        "target_file": target["file"],
        "retrieved_chunk_ids": [item["id"] for item in results],
        "retrieved_sources": sorted({item["source"] for item in results}),
        "model": model,
        "success": False,
        "error": None,
        "token_usage": {},
    }
    try:
        stub = _target_stub(REPO_DIR, target)
        prompt = _build_prompt(task_text, target, stub, results)
        client = _load_client()
        response, usage = _call_model(client, prompt, model)
        generated = _extract_code(response)
        result["token_usage"] = usage
        result["generated_code"] = generated
        if dry_run:
            result["prompt"] = prompt
        else:
            patch_target(REPO_DIR, target, generated)
        result["success"] = True
    except Exception as exc:
        result["error"] = _sanitize_error(exc)
    return result


def _load_tasks(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Run the solver for selected or all missing-code tasks."""
    global REPO_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-file", type=Path, default=TASKS_PATH)
    parser.add_argument("--repo", type=Path, default=REPO_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate code with the LLM and print it, but do not modify any files. "
        "This still makes one API call per task.",
    )
    parser.add_argument("--only")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()
    if args.model not in ALLOWED_MODELS:
        raise ValueError(f"Model is not allowed: {args.model}")
    REPO_DIR = args.repo.resolve()
    tasks = _load_tasks(args.tasks_file)
    if args.only is not None:
        tasks = [
            task for index, task in enumerate(tasks)
            if str(index) == args.only or task["method"] == args.only
        ]
    logs = []
    for task in tasks:
        result = solve_task(task["docstring"], task, args.model, args.top_n, args.dry_run)
        logs.append(result)
        print(
            f"{result['task']} target={result['target_file']} "
            f"sources={','.join(result['retrieved_sources'])} "
            f"{'success' if result['success'] else 'failure'}"
        )
        if args.dry_run:
            print("PROMPT:\n" + result.get("prompt", ""))
            print("GENERATED CODE:\n" + result.get("generated_code", ""))
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(json.dumps(logs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
