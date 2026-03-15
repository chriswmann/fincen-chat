from temporalio import workflow
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow

with workflow.unsafe.imports_passed_through():
    from .agents import temporal_planner, temporal_researcher, temporal_sythesiser
from .models import (
    InvestigationInput,
    InvestigationReport,
    InvestigationStatus,
    InvestigationWorkflowState,
    ResearchPlan,
    SubQueryResult,
)


@workflow.defn
class InvestigationWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [
        temporal_planner,
        temporal_researcher,
        temporal_sythesiser,
    ]

    def __init__(self) -> None:
        self._status: InvestigationWorkflowState = InvestigationWorkflowState.PLANNING
        self._progress = 0
        self._total_steps = 0

    @workflow.run
    async def run(self, input: InvestigationInput) -> InvestigationReport:
        # Plan
        plan_result = await temporal_planner.run(input.query)
        plan = plan_result.output
        self._total_steps = len(plan.sub_queries)

        # Research sub_queries
        self._status = InvestigationWorkflowState.RESEARCHING
        findings: list[SubQueryResult] = []
        for subquery in plan.sub_queries:
            self._progress += 1
            result = await temporal_researcher.run(subquery.query)
            findings.append(result.output)

        self._status = InvestigationWorkflowState.SYNTHESISING
        synthesis_prompt = _format_synthesis_prompt(input.query, plan, findings)
        report_result = await temporal_sythesiser.run(synthesis_prompt)
        self._status = InvestigationWorkflowState.COMPLETE

        return report_result.output

    @workflow.query
    def get_status(self) -> InvestigationStatus:
        return InvestigationStatus(
            status=self._status,
            progress=self._progress,
            total_steps=self._total_steps,
        )


def _format_synthesis_prompt(
    query: str, plan: ResearchPlan, findings: list[SubQueryResult]
) -> str:
    sub_queries = "\n".join(
        f"  {i}. {sq.query} \u2014 {sq.rationale}"
        for i, sq in enumerate(plan.sub_queries, 1)
    )

    sections: list[str] = []
    for i, finding in enumerate(findings, 1):
        entities = (
            ", ".join(
                f"{e.name} ({e.entity_type or 'unknown type'})"
                for e in finding.entities_found
            )
            or "None identified"
        )

        sections.append(
            f"### Sub-query {i}: {finding.query}\n"
            f"Data found: {'Yes' if finding.data_found else 'No'}\n"
            f"Findings:\n{finding.findings}\n"
            f"Entities: {entities}"
        )

    return (
        "Synthesise a comprehensive investigation report from the research below.\n\n"
        f"## Original Query\n{query}\n\n"
        f"## Research Plan\n"
        f"Objective: {plan.objective}\n"
        f"Sub-queries:\n{sub_queries}\n\n"
        f"## Research Findings\n\n" + "\n\n".join(sections)
    )
