from dataclasses import dataclass
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, EvaluationReason
from pydantic_evals.evaluators import LLMJudge
from fincen_chat.config import get_agent_config
from fincen_chat.models import (
    AgentOutput,
    FinCENResponse,
    ErrorResponse,
)


@dataclass
class IsValidOutputType(Evaluator):
    """Check the output is of the expected type."""

    def evaluate(self, ctx: EvaluatorContext[str, AgentOutput]) -> bool:
        return isinstance(ctx.output, (FinCENResponse, ErrorResponse))


@dataclass
class RefusalCheck(Evaluator):
    """Check the agent refuses to answer queries when appropriate.

    For classes tagged `category=refusal` in the metadata, the agent must refuse (and return
    an ErrorResponse).
    """

    def evaluate(self, ctx: EvaluatorContext[str, AgentOutput]) -> EvaluationReason:
        is_refusal_case = ctx.metadata.get("category") == "refusal"

        if not is_refusal_case:
            # Irrelevant to this evaluator, we'll just pass for now and will
            # add case-specific evaluation config later.
            return EvaluationReason(value=True, reason="Not a refusal case")

        if isinstance(ctx.output, ErrorResponse):
            return EvaluationReason(
                value=True,
                reason=f"Correctly refused: {ctx.output.reason}",
            )

        return EvaluationReason(
            value=False,
            reason="Agent answered question it should have refused",
        )


@dataclass
class HasEntitiesWhenDataFound(Evaluator):
    """If the agent claims `data_found=True`, it should mention at least one entity."""

    def evaluate(self, ctx: EvaluatorContext[str, AgentOutput]) -> EvaluationReason:
        if not isinstance(ctx.output, FinCENResponse):
            return EvaluationReason(value=True, reason="Not a FinCENResponse")

        if ctx.output.data_found and not ctx.output.entities_mentioned:
            return EvaluationReason(
                value=False, reason="`data_found=True` but no entities mentioned"
            )

        return EvaluationReason(
            value=True, reason="Entities present or `data_found=False`"
        )


@dataclass
class NonEmptyAnswer(Evaluator):
    """FinCENResponse answers must not be empty."""

    def evaluate(self, ctx: EvaluatorContext[str, AgentOutput]) -> bool:
        if isinstance(ctx.output, FinCENResponse):
            return bool(ctx.output.answer.strip())
        return True


@dataclass
class ConfidenceIsReasonalbe(Evaluator):
    """Check the confidence field is one of the expected literals."""

    def evaluate(self, ctx: EvaluatorContext[str, AgentOutput]) -> bool:
        if isinstance(ctx.output, FinCENResponse):
            return ctx.output.confidence in ("high", "medium", "low")
        return True


relevant_response_judge = LLMJudge(
    rubric=(
        "The response directly and relevantly answers the user's question about "
        "FinCEN data. It does not contain fabricated information. "
        "If the question is out of scope, the response clearly states this."
    ),
    include_input=True,
    model=get_agent_config().model,
)

groundedness_judge = LLMJudge(
    rubric=(
        "The response appears grounded in actual data rather than hallucinated. "
        "It references specific entities, amounts, or relationships that could "
        "plausibly come from a financial crimes database."
    ),
    include_input=True,
    model=get_agent_config().model,
)
