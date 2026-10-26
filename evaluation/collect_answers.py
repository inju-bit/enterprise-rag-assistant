import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent

DATASET_FILE = BASE_DIR / "datasets" / "rag_evaluation.json"
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "collected_answers.json"

API_BASE_URL = "http://127.0.0.1:8000"
ASK_URL = f"{API_BASE_URL}/ask"
HEALTH_URL = f"{API_BASE_URL}/health"

TOP_K = 5
REQUEST_TIMEOUT = 120


def load_dataset():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_FILE}\n"
            "Run python create_dataset.py first."
        )

    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    cases = dataset.get("evaluation_cases", [])

    if not cases:
        raise ValueError("No evaluation cases found in dataset.")

    return dataset, cases


def check_backend(session):
    print("Checking FastAPI backend...")

    try:
        response = session.get(
            HEALTH_URL,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "healthy":
            raise RuntimeError(
                f"Unexpected backend status: {data}"
            )

        print("FastAPI backend is healthy.\n")

    except requests.RequestException as error:
        raise RuntimeError(
            "Cannot connect to FastAPI on port 8000. "
            "Start the backend before running evaluation."
        ) from error


def evaluate_question(session, case):
    question = case["question"]

    print("-" * 60)
    print(f"Evaluating {case['id']}")
    print(f"Question: {question}")

    start = time.perf_counter()

    try:
        response = session.post(
            ASK_URL,
            json={
                "question": question,
                "top_k": TOP_K
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        elapsed = round(
            time.perf_counter() - start,
            3
        )

        if not isinstance(data.get("answer"), str):
            raise ValueError(
                "Response does not contain a valid answer."
            )

        sources = data.get("sources", [])

        if not isinstance(sources, list):
            raise ValueError(
                "Response sources must be a list."
            )

        retrieved_contexts = [
            source["text"]
            for source in sources
            if isinstance(source, dict)
            and isinstance(source.get("text"), str)
        ]

        print(f"Status: SUCCESS")
        print(f"Response time: {elapsed} seconds")
        print(f"Retrieved contexts: {len(retrieved_contexts)}")
        print(f"Answer: {data['answer'][:250]}")

        return {
            "id": case["id"],
            "question": question,
            "reference": case["reference_answer"],
            "response": data["answer"],
            "retrieved_contexts": retrieved_contexts,
            "sources": sources,
            "category": case.get("category", ""),
            "reference_verified": case.get("verified", False),
            "response_time_seconds": elapsed,
            "status": "success",
            "error": None
        }

    except (
        requests.RequestException,
        ValueError
    ) as error:
        elapsed = round(
            time.perf_counter() - start,
            3
        )

        print(f"Status: FAILED")
        print(f"Error: {error}")

        return {
            "id": case["id"],
            "question": question,
            "reference": case["reference_answer"],
            "response": "",
            "retrieved_contexts": [],
            "sources": [],
            "category": case.get("category", ""),
            "reference_verified": case.get("verified", False),
            "response_time_seconds": elapsed,
            "status": "failed",
            "error": str(error)
        }


def save_results(dataset, results):
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    successful = sum(
        result["status"] == "success"
        for result in results
    )

    output = {
        "evaluation_name": "Enterprise RAG Evaluation",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_name": dataset.get("dataset_name"),
        "api_url": ASK_URL,
        "top_k": TOP_K,
        "total_questions": len(results),
        "successful_questions": successful,
        "failed_questions": len(results) - successful,
        "results": results
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    return output


def main():
    print("=" * 60)
    print("ENTERPRISE AI - RAG ANSWER COLLECTION")
    print("=" * 60)

    dataset, cases = load_dataset()

    with requests.Session() as session:
        check_backend(session)

        results = []

        for case in cases:
            result = evaluate_question(session, case)
            results.append(result)

            # Save after every question so earlier answers
            # are preserved if the next request fails.
            save_results(dataset, results)

    output = save_results(dataset, results)

    print("\n" + "=" * 60)
    print("COLLECTION SUMMARY")
    print("=" * 60)

    print(f"Total questions: {output['total_questions']}")
    print(
        f"Successful: {output['successful_questions']}"
    )
    print(
        f"Failed: {output['failed_questions']}"
    )
    print(f"Results saved to: {OUTPUT_FILE}")

    if output["failed_questions"] == 0:
        print("\nANSWER COLLECTION SUCCESSFUL")
    else:
        print("\nSome requests failed. Check the results file.")


if __name__ == "__main__":
    main()