"""Groq LLM call, versioned prompt, and citation enforcement.

Two checks run on every answer before it's returned to a caller:
1. Insufficient-context signal — if the model followed the v2 prompt's rule
   and returned `INSUFFICIENT_CONTEXT`, that's surfaced as a clear decline
   rather than passed through as if it were a real answer.
2. Citation validity — every `[n]` in the answer must refer to a chunk that
   was actually in context. A citation pointing outside that range is a
   hallucinated source.

This is a structural check (citations point to real chunks), not a semantic
one (the cited chunk actually supports the sentence it's attached to) — that
kind of faithfulness scoring is what Phase-3's `ragas` evaluation is for.
"""

from __future__ import annotations

import re
from functools import lru_cache

from langchain_core.documents import Document

from .prompts import get_prompt_template

CITATION_PATTERN = re.compile(r"\[(\d+)\]")
INSUFFICIENT_CONTEXT_SIGNAL = "INSUFFICIENT_CONTEXT"


@lru_cache(maxsize=1)
def get_llm(model: str, api_key: str, temperature: float = 0.0):
    from langchain_groq import ChatGroq

    return ChatGroq(model=model, temperature=temperature, groq_api_key=api_key)


def format_context(docs: list[Document]) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        src = d.metadata.get("source", "unknown")
        lines.append(f"[{i}] (source: {src})\n{d.page_content}")
    return "\n\n".join(lines)


def check_citations(answer: str, num_chunks: int) -> dict:
    cited_numbers = {int(n) for n in CITATION_PATTERN.findall(answer)}
    invalid = {n for n in cited_numbers if n < 1 or n > num_chunks}
    return {
        "cited_numbers": sorted(cited_numbers),
        "invalid_citations": sorted(invalid),
        "has_invalid_citations": bool(invalid),
    }


def enforce_citations(answer: str, num_chunks: int) -> dict:
    """Returns whether `answer` should be shown as-is, or replaced with a
    decline message, plus why."""
    if answer.strip() == INSUFFICIENT_CONTEXT_SIGNAL:
        return {
            "accepted": False,
            "reason": "model signaled insufficient context",
            "final_answer": "I don't have enough information in the retrieved documents to answer that.",
        }

    citation_check = check_citations(answer, num_chunks)
    if citation_check["has_invalid_citations"]:
        invalid = citation_check["invalid_citations"]
        return {
            "accepted": False,
            "reason": f"answer cited out-of-range chunk(s): {invalid}",
            "final_answer": (
                "I couldn't verify the sources for this answer, so I'm declining "
                "rather than risk citing something unsupported."
            ),
        }

    return {"accepted": True, "reason": None, "final_answer": answer}


def generate_answer(llm, question: str, docs: list[Document], prompt_version: str | None = None) -> dict:
    """Runs generation + enforcement. Returns a dict with `final_answer`,
    `accepted`, and `reason` — never raises on a declined answer, since
    declining is expected, valid behavior, not an error."""
    template = get_prompt_template(prompt_version)
    context = format_context(docs)
    prompt = template.format(context=context, question=question)

    raw_answer = llm.invoke(prompt).content
    return enforce_citations(raw_answer, num_chunks=len(docs))
