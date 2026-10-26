import json
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "datasets"
OUTPUT_FILE = DATASET_DIR / "rag_evaluation.json"


def build_dataset():
    """
    Create reference evaluation cases for the RAG assistant.

    Reference answers are based on the research excerpts
    previously examined. Verify against the original PDF
    before using them for formal benchmarking.
    """

    return [
        {
            "id": "Q001",
            "question": (
                "What factors are investigated as drivers "
                "of impulsive buying on mobile apps?"
            ),
            "reference_answer": (
                "The study investigates physical environment, "
                "social environment, time perspective, "
                "hedonic browsing, and utilitarian browsing "
                "as situational factors associated with "
                "impulsive buying on mobile apps."
            ),
            "category": "research_variables",
            "source_document": "IB PAPER.pdf",
            "verified": False
        },
        {
            "id": "Q002",
            "question": (
                "How many respondents participated "
                "in the research?"
            ),
            "reference_answer": (
                "The dataset contains responses "
                "from 628 respondents."
            ),
            "category": "dataset",
            "source_document": "IB PAPER.pdf",
            "verified": False
        },
        {
            "id": "Q003",
            "question": (
                "What method was used to collect "
                "the research data?"
            ),
            "reference_answer": (
                "Data were collected using an online "
                "questionnaire administered to mobile "
                "device users who had made online "
                "purchases during the previous six months."
            ),
            "category": "methodology",
            "source_document": "IB PAPER.pdf",
            "verified": False
        },
        {
            "id": "Q004",
            "question": (
                "Which statistical modelling approach "
                "was used in the study?"
            ),
            "reference_answer": (
                "The study used Structural Equation "
                "Modelling (SEM) to evaluate "
                "the empirical model."
            ),
            "category": "methodology",
            "source_document": "IB PAPER.pdf",
            "verified": False
        },
        {
            "id": "Q005",
            "question": (
                "Does the article establish that "
                "the situational factors cause "
                "impulsive buying?"
            ),
            "reference_answer": (
                "The shared excerpts describe an "
                "empirical model and dataset but do not "
                "establish definitive causal effects. "
                "The proposed relationships should not "
                "be presented as proven causation."
            ),
            "category": "evidence_limitations",
            "source_document": "IB PAPER.pdf",
            "verified": False
        }
    ]


def main():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    cases = build_dataset()

    dataset = {
        "dataset_name": "Enterprise RAG Evaluation",
        "version": "1.0",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_document": "IB PAPER.pdf",
        "review_status": "pending_manual_verification",
        "total_questions": len(cases),
        "evaluation_cases": cases
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            dataset,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("=" * 50)
    print("RAG EVALUATION DATASET CREATED")
    print("=" * 50)

    print(f"File: {OUTPUT_FILE}")
    print(f"Total questions: {len(cases)}")

    for case in cases:
        print(f"\n{case['id']}: {case['question']}")
        print(f"Category: {case['category']}")

    print("\nDataset creation successful.")


if __name__ == "__main__":
    main()