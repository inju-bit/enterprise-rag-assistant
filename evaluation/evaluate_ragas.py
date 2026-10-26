import asyncio
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from openai import AsyncOpenAI

from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecisionWithReference,
)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

INPUT_FILE = BASE_DIR / "results" / "collected_answers.json"
OUTPUT_JSON = BASE_DIR / "results" / "ragas_scores.json"
OUTPUT_CSV = BASE_DIR / "results" / "ragas_scores.csv"

EVALUATION_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# Run one case at a time to make debugging easier.
# Set to 1 for your first test, then 5 for all questions.
MAX_CASES = 5

load_dotenv(PROJECT_DIR / ".env")


def load_cases():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing evaluation file: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    cases = [
        case for case in dataset.get("results", [])
        if case.get("status") == "success"
    ]

    if not cases:
        raise ValueError("No successful evaluation cases found.")

    return cases[:MAX_CASES]


def save_results(records):
    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    metric_names = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
    ]

    averages = {}

    for metric_name in metric_names:
        values = [
            record[metric_name]
            for record in records
            if isinstance(record.get(metric_name), (int, float))
        ]

        averages[metric_name] = (
            round(mean(values), 4) if values else None
        )

    output = {
        "evaluation_name": "Enterprise RAGAS Evaluation",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "evaluation_model": EVALUATION_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "total_evaluated": len(records),
        "reference_status": (
            "Unverified references are exploratory only."
        ),
        "average_scores": averages,
        "results": records,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    columns = [
        "id",
        "question",
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "reference_verified",
        "evaluation_status",
        "error",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(records)

    return output


async def evaluate_case(case, metrics):
    question = case["question"]
    answer = case["response"]
    reference = case.get("reference", "")

    contexts = [
        text for text in case.get("retrieved_contexts", [])
        if isinstance(text, str) and text.strip()
    ]

    print("\n" + "=" * 60)
    print(f"Evaluating {case['id']}")
    print(f"Question: {question}")
    print(f"Retrieved passages: {len(contexts)}")

    record = {
        "id": case["id"],
        "question": question,
        "reference_verified": case.get(
            "reference_verified", False
        ),
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
        "evaluation_status": "pending",
        "error": "",
    }

    if not answer.strip() or not contexts:
        record["evaluation_status"] = "skipped"
        record["error"] = "Missing answer or retrieved contexts"
        return record

    # Faithfulness measures answer support in retrieved text.
    try:
        result = await metrics["faithfulness"].ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )

        record["faithfulness"] = round(
            float(result.value), 4
        )
        print("Faithfulness:", record["faithfulness"])

    except Exception as exc:
        print("Faithfulness failed:", exc)
        record["error"] += f"Faithfulness: {exc}; "

    # Answer relevancy does not require a reference answer.
    try:
        result = await metrics["answer_relevancy"].ascore(
            user_input=question,
            response=answer,
        )

        record["answer_relevancy"] = round(
            float(result.value), 4
        )
        print("Answer relevancy:", record["answer_relevancy"])

    except Exception as exc:
        print("Answer relevancy failed:", exc)
        record["error"] += f"Answer relevancy: {exc}; "

    # Context precision uses the supplied reference answer.
    # Unverified references produce provisional scores.
    if reference.strip():
        try:
            result = await metrics["context_precision"].ascore(
                user_input=question,
                reference=reference,
                retrieved_contexts=contexts,
            )

            record["context_precision"] = round(
                float(result.value), 4
            )
            print(
                "Context precision:",
                record["context_precision"]
            )

        except Exception as exc:
            print("Context precision failed:", exc)
            record["error"] += f"Context precision: {exc}; "

    completed = sum(
        record[name] is not None
        for name in (
            "faithfulness",
            "answer_relevancy",
            "context_precision",
        )
    )

    record["evaluation_status"] = (
        "success" if completed == 3
        else "partial" if completed else "failed"
    )

    return record


async def main():
    print("=" * 60)
    print("ENTERPRISE AI - RAGAS 0.4.3 EVALUATION")
    print("=" * 60)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY not found in project .env file."
        )

    cases = load_cases()

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        timeout=90.0,
        max_retries=2,
    )

    llm = llm_factory(
        EVALUATION_MODEL,
        client=client,
    )

    embeddings = embedding_factory(
        "openai",
        model=EMBEDDING_MODEL,
        client=client,
    )

    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(
            llm=llm,
            embeddings=embeddings,
        ),
        "context_precision": ContextPrecisionWithReference(
            llm=llm,
        ),
    }

    records = []

    for case in cases:
        result = await evaluate_case(case, metrics)
        records.append(result)

        # Preserve each result in case a later question fails.
        save_results(records)

    output = save_results(records)

    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)

    print("Cases evaluated:", len(records))

    for name, score in output["average_scores"].items():
        if score is None:
            print(f"{name}: unavailable")
        else:
            print(f"{name}: {score:.4f}")

    print("\nResults:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)

    print(
        "\nNote: Results using unverified reference "
        "answers are exploratory."
    )


if __name__ == "__main__":
    asyncio.run(main())