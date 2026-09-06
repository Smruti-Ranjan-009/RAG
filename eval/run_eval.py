"""Phase-3 offline evaluation.

Runs every question in the golden Q&A set through the actual production
pipeline (rag_app.pipeline.run_query_for_eval — same retrieval, re-ranking,
generation, and enforcement code the API uses), then scores two things:

1. Coverage / decline accuracy — did enforcement behave correctly? Answerable
   questions should be answered; the out-of-scope ones should be declined.
   This is checked directly, no LLM judge needed.
2. Faithfulness — for every answer that WAS accepted, does ragas' Faithfulness
   metric (an LLM-as-judge check) agree the claims are actually supported by
   the retrieved context? Declined answers are excluded from this score on
   purpose — an enforcement decline has no claims to check faithfulness on;
   including it would either error out or silently inflate/deflate the score
   for the wrong reason.

Exits 0 (pass) or 1 (fail) so this can gate a CI pipeline directly.

Usage:
    python eval/run_eval.py
    python eval/run_eval.py --threshold 0.75 --golden-set eval/golden_qa.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from rag_app.config import settings  # noqa: E402  (import after load_dotenv on purpose)
from rag_app.generation import get_llm  # noqa: E402
from rag_app.pipeline import run_query_for_eval  # noqa: E402

DEFAULT_GOLDEN_SET = Path(__file__).parent / "golden_qa.json"
DEFAULT_THRESHOLD = 0.7


def load_golden_set(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if not data:
        raise ValueError(f"{path} is empty — nothing to evaluate.")
    return data


def run_pipeline_over_golden_set(golden_set: list[dict]) -> list[dict]:
    results = []
    for item in golden_set:
        print(f"  [{item['id']}] {item['question']!r}")
        response = run_query_for_eval(settings, item["question"])
        results.append({**item, **response})
    return results


def score_coverage(results: list[dict]) -> dict:
    """Enforcement correctness, independent of faithfulness."""
    answerable = [r for r in results if r["expect_answerable"]]
    unanswerable = [r for r in results if not r["expect_answerable"]]

    correctly_answered = [r for r in answerable if r["accepted"]]
    correctly_declined = [r for r in unanswerable if not r["accepted"]]

    coverage = len(correctly_answered) / len(answerable) if answerable else None
    decline_accuracy = len(correctly_declined) / len(unanswerable) if unanswerable else None

    return {
        "answerable_count": len(answerable),
        "unanswerable_count": len(unanswerable),
        "coverage": coverage,
        "decline_accuracy": decline_accuracy,
        "correctly_answered": correctly_answered,
    }


def score_faithfulness(correctly_answered: list[dict]) -> dict:
    """Runs ragas' Faithfulness metric over every accepted, expected-answerable
    result. Returns a dict with the mean score AND how many samples actually
    completed — ragas silently produces NaN for any sample whose judge-LLM
    call fails (timeout, rate limit, etc.) and pandas' .mean() skips NaN by
    default, so a "perfect" score computed over 2 survivors out of 15 looks
    identical to a genuine 15/15 pass unless you check for this explicitly."""
    if not correctly_answered:
        return {"mean_score": None, "completed": 0, "total": 0}

    from ragas import EvaluationDataset, RunConfig, SingleTurnSample, evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness

    samples = [
        SingleTurnSample(
            user_input=item["question"],
            retrieved_contexts=item["contexts"],
            response=item["answer"],
        )
        for item in correctly_answered
    ]
    dataset = EvaluationDataset(samples=samples)

    # Default max_workers=16 fires that many concurrent judge-LLM calls at
    # once, which reliably hits Groq's rate limits and times out most of
    # them. Low concurrency + a generous per-call timeout is slower but
    # actually completes.
    run_config = RunConfig(max_workers=2, timeout=180)

    # Same Groq LLM the pipeline itself uses, reused here as ragas' judge —
    # no separate API key or provider needed.
    judge_llm = LangchainLLMWrapper(get_llm(settings.groq_model, settings.groq_api_key, temperature=0))

    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness()],
        llm=judge_llm,
        run_config=run_config,
        raise_exceptions=False,  # explicit: we handle failures ourselves via NaN detection below
        show_progress=False,
    )

    df = result.to_pandas()
    total = len(df)
    completed = df["faithfulness"].notna().sum()

    return {
        "mean_score": float(df["faithfulness"].mean()) if completed > 0 else None,
        "completed": int(completed),
        "total": int(total),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-3 faithfulness evaluation")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum mean faithfulness score to pass (0-1). Default: 0.7",
    )
    parser.add_argument(
        "--max-incomplete-fraction",
        type=float,
        default=0.0,
        help="Fraction of faithfulness judgments allowed to fail (timeout/rate-limit) "
        "before treating the whole run as untrustworthy and failing regardless of the "
        "score. Default: 0.0 (strict — any failure fails the run). Raise this only if "
        "occasional transient failures are making CI flaky for reasons unrelated to "
        "actual answer quality.",
    )
    args = parser.parse_args()

    golden_set = load_golden_set(args.golden_set)
    print(f"Loaded {len(golden_set)} golden Q&A pairs from {args.golden_set}")

    print("\nRunning pipeline over golden set (calls the live LLM once per question)...")
    results = run_pipeline_over_golden_set(golden_set)

    coverage_stats = score_coverage(results)
    coverage = coverage_stats["coverage"]
    decline_accuracy = coverage_stats["decline_accuracy"]

    print(f"\nAnswerable questions: {coverage_stats['answerable_count']}")
    print(f"Coverage (answerable questions actually answered): {coverage:.1%}" if coverage is not None else "n/a")
    print(f"Out-of-scope questions: {coverage_stats['unanswerable_count']}")
    print(
        f"Decline accuracy (correctly declined): {decline_accuracy:.1%}"
        if decline_accuracy is not None
        else "n/a"
    )

    print("\nScoring faithfulness with ragas (calls the LLM again, as a judge)...")
    faithfulness = score_faithfulness(coverage_stats["correctly_answered"])

    if faithfulness["mean_score"] is None:
        print("\nNo accepted answers to score faithfulness on. Treating as a failure.")
        return 1

    completed, total = faithfulness["completed"], faithfulness["total"]
    incomplete_fraction = (total - completed) / total if total else 0.0

    if incomplete_fraction > args.max_incomplete_fraction:
        print(
            f"\n{total - completed}/{total} faithfulness judgments failed to complete "
            f"(timeout or rate limit against the judge LLM) — the score below only "
            f"reflects the {completed} that succeeded, not all {total}."
        )
        print(
            f"Incomplete fraction {incomplete_fraction:.1%} exceeds the allowed "
            f"{args.max_incomplete_fraction:.1%}. Failing the run rather than reporting "
            f"a misleadingly high or low score — rerun, or raise "
            f"--max-incomplete-fraction if this is expected flakiness."
        )
        return 1

    print(f"\nMean faithfulness score: {faithfulness['mean_score']:.3f}  "
          f"(threshold: {args.threshold}, {completed}/{total} judgments completed)")

    if faithfulness["mean_score"] < args.threshold:
        print(f"\nFAIL: faithfulness {faithfulness['mean_score']:.3f} is below threshold {args.threshold}")
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())