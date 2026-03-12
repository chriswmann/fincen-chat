from pathlib import Path
from pydantic_evals import Dataset

from fincen_chat.models import AgentOutput
from evals.evaluators import (
    IsValidOutputType,
    RefusalCheck,
    HasEntitiesWhenDataFound,
    NonEmptyAnswer,
    ConfidenceIsReasonalbe,
    relevant_response_judge,
    groundedness_judge,
)
from evals.task import run_agent

DATASET_PATH = Path(__file__).parent / "datasets" / "fincen_cases.yaml"


def build_dataset() -> Dataset[str, AgentOutput]:
    """Load Cases from yaml and attach evaluators to them."""

    dataset = Dataset[str, AgentOutput].from_file(DATASET_PATH)

    dataset.add_evaluator(IsValidOutputType())
    dataset.add_evaluator(RefusalCheck())
    dataset.add_evaluator(HasEntitiesWhenDataFound())
    dataset.add_evaluator(NonEmptyAnswer())
    dataset.add_evaluator(ConfidenceIsReasonalbe())

    dataset.add_evaluator(relevant_response_judge)
    dataset.add_evaluator(groundedness_judge)

    return dataset


if __name__ == "__main__":
    dataset = build_dataset()
    report = dataset.evaluate_sync(run_agent)
    report.print(include_input=True, include_output=True, include_analyses=True)
