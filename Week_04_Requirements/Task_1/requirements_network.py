"""Build a traceable requirements document from a directory of source documents.

Run from the repository root:
    python Week_04_Requirements\\Task_1\\requirements_network.py \
        Week_04_Requirements\\Task_1\\data\\corpus

The script intentionally loads credentials through python-dotenv only. It never
prints, validates, or otherwise exposes the credential value.
"""

import argparse
import os
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

KEY_FILE = Path(__file__).resolve().parent / "API_key.env"
if not load_dotenv(KEY_FILE):
    raise FileNotFoundError(f"Could not load environment file: {KEY_FILE}")
if not os.environ.get("OPENAI_API_KEY"):
    raise RuntimeError(f"{KEY_FILE.name} does not define OPENAI_API_KEY")

class CandidateRequirement(BaseModel):
    name: str = Field(description="Short, specific requirement name.")
    explanation: str = Field(description="One paragraph explaining the requirement.")
    priority: Literal["Must", "Should", "Could", "Won't"] = Field(
        description="MoSCoW priority."
    )
    sources: list[str] = Field(description="Exact source filenames supporting it.")


class CandidateBatch(BaseModel):
    requirements: list[CandidateRequirement]


class DiscardedCandidate(BaseModel):
    description: str
    reason: str
    sources: list[str]


class ConsolidationResult(BaseModel):
    requirements: list[CandidateRequirement]
    discarded: list[DiscardedCandidate]


class FinalRequirement(CandidateRequirement):
    requirement_id: str = Field(description="Stable identifier such as REQ-001.")


class ReviewResult(BaseModel):
    accepted: bool
    issues: list[str] = Field(
        description="Concrete defects which must be fixed; empty when accepted."
    )


class NetworkState(TypedDict, total=False):
    documents: list[dict[str, str]]
    candidates: list[CandidateRequirement]
    discarded: list[DiscardedCandidate]
    requirements: list[FinalRequirement]
    review: ReviewResult
    revision_count: int
    output_path: str


def _model(name: str, temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(model=name, temperature=temperature, max_retries=2)


def load_documents(state: NetworkState) -> dict[str, list[dict[str, str]]]:
    """Deterministic node: read every supported file and preserve its filename."""
    corpus = Path(state["output_path"])
    if not corpus.is_dir():
        raise NotADirectoryError(f"Corpus directory does not exist: {corpus}")
    documents = []
    for path in sorted(p for p in corpus.rglob("*") if p.is_file()):
        if path.suffix.lower() not in {".txt", ".eml"}:
            continue
        documents.append({"name": path.relative_to(corpus).as_posix(), "text": path.read_text(encoding="utf-8")})
    if not documents:
        raise ValueError(f"No .txt or .eml documents found in {corpus}")
    return {"documents": documents}


def extract_candidates(state: NetworkState) -> dict[str, list[CandidateRequirement]]:
    extractor = _model("gpt-5.6-luna").with_structured_output(CandidateBatch)
    candidates: list[CandidateRequirement] = []
    for document in state["documents"]:
        prompt = """Extract explicit and strongly implied software requirements from this
source document. Do not invent functionality. Preserve all meaningful requirements,
including operational, reporting, security, data, and usability requirements. Assign
MoSCoW priority conservatively. Each source list must contain only this exact filename.
Return an empty list if the document contains no requirement.

SOURCE FILENAME: {name}
SOURCE TEXT:
{text}""".format(**document)
        result = extractor.invoke(
            [
                SystemMessage(content="You are a requirements analyst. Be precise and complete."),
                HumanMessage(content=prompt),
            ]
        )
        candidates.extend(result.requirements)
    return {"candidates": candidates}


def consolidate_requirements(state: NetworkState) -> dict[str, object]:
    consolidator = _model("gpt-5-mini").with_structured_output(ConsolidationResult)
    candidate_text = "\n\n".join(
        f"NAME: {item.name}\nPRIORITY: {item.priority}\nEXPLANATION: {item.explanation}\n"
        f"SOURCES: {', '.join(item.sources)}"
        for item in state["candidates"]
    )
    result = consolidator.invoke(
        [
            SystemMessage(content=(
                "You consolidate software requirements. Merge semantic duplicates, retain "
                "all distinct requirements, resolve wording conflicts by making scope explicit, "
                "and never drop a source without a reason. Use consistent terminology and "
                "paragraph-length explanations. Put conflicting, nonsensical, or otherwise "
                "rejected candidates in discarded with a concrete reason and their sources."
            )),
            HumanMessage(content=(
                "Consolidate these candidates. Every output source must be copied from the "
                "candidate source lists. Candidates:\n" + candidate_text
            )),
        ]
    )
    return {
        "requirements": [
            FinalRequirement(requirement_id=f"REQ-{index:03d}", **item.model_dump())
            for index, item in enumerate(result.requirements, start=1)
        ],
        "discarded": result.discarded,
    }


def deterministic_validate(state: NetworkState) -> dict[str, list[FinalRequirement]]:
    """Deterministic node: enforce IDs, non-empty fields, and stable source order."""
    checked: list[FinalRequirement] = []
    for index, requirement in enumerate(state["requirements"], start=1):
        if not requirement.name.strip() or not requirement.explanation.strip():
            raise ValueError(f"Requirement {index} has an empty name or explanation")
        if not requirement.sources:
            raise ValueError(f"Requirement {requirement.requirement_id} has no trace source")
        checked.append(
            requirement.model_copy(
                update={
                    "requirement_id": f"REQ-{index:03d}",
                    "sources": sorted(set(requirement.sources)),
                }
            )
        )
    return {"requirements": checked}


def review_requirements(state: NetworkState) -> dict[str, ReviewResult]:
    reviewer = _model("gpt-4o-mini").with_structured_output(ReviewResult)
    rendered = "\n".join(
        f"{r.requirement_id}: {r.name} | {r.priority} | {r.explanation} | {r.sources}"
        for r in state["requirements"]
    )
    result = reviewer.invoke(
        [
            SystemMessage(content=(
                "Audit this requirements set for semantic duplicates, contradictions, "
                "missing traceability, vague explanations, inconsistent vocabulary, and "
                "unjustified omissions. Be strict but actionable."
            )),
            HumanMessage(content=rendered),
        ]
    )
    return {"review": result}


def revise_requirements(state: NetworkState) -> dict[str, object]:
    reviser = _model("gpt-5.4-nano").with_structured_output(ConsolidationResult)
    requirements = "\n".join(
        f"{r.requirement_id}: {r.name} | {r.priority} | {r.explanation} | SOURCES={r.sources}"
        for r in state["requirements"]
    )
    result = reviser.invoke(
        [
            SystemMessage(content=(
                "Revise requirements using the audit findings. Preserve complete coverage "
                "and source traceability. Merge duplicates and repair contradictions without "
                "inventing facts. Keep the same output schema and retain a blacklist "
                "entry with a reason for every discarded candidate."
            )),
            HumanMessage(content=f"REQUIREMENTS:\n{requirements}\nAUDIT:\n{state['review'].issues}"),
        ]
    )
    revised = [
        FinalRequirement(requirement_id=f"REQ-{index:03d}", **item.model_dump())
        for index, item in enumerate(result.requirements, start=1)
    ]
    return {
        "requirements": revised,
        "discarded": result.discarded,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def route_review(state: NetworkState) -> str:
    if state["review"].accepted or state.get("revision_count", 0) >= 2:
        return "render"
    return "revise"


def render_document(state: NetworkState) -> dict[str, str]:
    output = Path(state["output_path"]).parent.parent / "requirements_document.md"
    lines = [
        "# Software Requirements Specification",
        "",
        "## Priority scale",
        "",
        "- **Must**: essential for an acceptable release.",
        "- **Should**: important, but a temporary workaround exists.",
        "- **Could**: valuable enhancement if time and resources allow.",
        "- **Won't**: explicitly deferred from this release.",
        "",
        "## Requirements",
        "",
    ]
    for requirement in state["requirements"]:
        name = requirement.name
        if name.startswith(f"{requirement.requirement_id} "):
            name = name[len(requirement.requirement_id) + 1 :]
        lines.extend([
            f"### {requirement.requirement_id}: {name}",
            "",
            f"**Priority:** {requirement.priority}",
            "",
            requirement.explanation,
            "",
            "**Traced to:** " + ", ".join(f"`{source}`" for source in requirement.sources),
            "",
        ])
    lines.extend(["## Discarded or conflicting candidates", ""])
    if state.get("discarded"):
        for index, candidate in enumerate(state["discarded"], start=1):
            lines.extend([
                f"### DISCARD-{index:03d}",
                "",
                candidate.description,
                "",
                f"**Reason:** {candidate.reason}",
                "",
                "**Sources:** " + ", ".join(f"`{source}`" for source in candidate.sources),
                "",
            ])
    else:
        lines.extend(["No candidates were discarded.", ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return {"output_path": str(output)}


def build_network():
    graph = StateGraph(NetworkState)
    graph.add_node("load_documents", load_documents)
    graph.add_node("extract_candidates", extract_candidates)
    graph.add_node("consolidate_requirements", consolidate_requirements)
    graph.add_node("deterministic_validate", deterministic_validate)
    graph.add_node("review_requirements", review_requirements)
    graph.add_node("revise_requirements", revise_requirements)
    graph.add_node("render", render_document)
    graph.add_edge(START, "load_documents")
    graph.add_edge("load_documents", "extract_candidates")
    graph.add_edge("extract_candidates", "consolidate_requirements")
    graph.add_edge("consolidate_requirements", "deterministic_validate")
    graph.add_edge("deterministic_validate", "review_requirements")
    graph.add_conditional_edges("review_requirements", route_review, {"revise": "revise_requirements", "render": "render"})
    graph.add_edge("revise_requirements", "deterministic_validate")
    graph.add_edge("render", END)
    return graph.compile()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", type=Path, help="Directory containing .txt and .eml source documents")
    args = parser.parse_args()
    result = build_network().invoke(
        {"output_path": str(args.corpus_dir.resolve()), "revision_count": 0}
    )
    print(f"Generated {len(result['requirements'])} requirements in {result['output_path']}")


if __name__ == "__main__":
    main()
