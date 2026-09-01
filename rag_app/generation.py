"""Groq LLM call + citation-aware prompt.

Phase-1: the prompt *asks* the model to answer only from context and cite
sources, but nothing enforces it. Phase-2's citation enforcement (refuse to
answer when chunks don't support a claim) hooks in right after
`generate_answer` returns, before the answer is sent to the client.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.documents import Document

PROMPT_TEMPLATE = """You are a helpful assistant answering questions using only the context below.
Cite the source number (e.g. [1]) after every claim you make. If the context does not contain
enough information to answer, say so explicitly instead of guessing.

Context:
{context}

Question: {question}

Answer (with citations):"""


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


def generate_answer(llm, question: str, docs: list[Document]) -> str:
    context = format_context(docs)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    response = llm.invoke(prompt)
    return response.content
