from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field
from ..models import FinCENEntity


class InvestigationWorkflowState(StrEnum):
    PLANNING = "planning"
    RESEARCHING = "researching"
    SYNTHESISING = "synthesising"
    COMPLETE = "complete"
    FAILED = "failed"


class SubQuery(BaseModel):
    query: str = Field(description="A single planned subquery")
    rationale: str = Field(description="The rationale for the query")


class ResearchPlan(BaseModel):
    objective: str = Field(description="The top-level objective of the research plan")
    sub_queries: list[SubQuery] = Field(
        description="The subqueries needed to deliver the plan objective"
    )


class SubQueryResult(BaseModel):
    query: str
    findings: str
    entities_found: list[FinCENEntity]
    data_found: bool


class InvestigationReport(BaseModel):
    title: str
    executive_summary: str
    detailed_findings: str
    entities_involved: list[FinCENEntity]
    risk_indicators: list[str]
    confidence: Literal["High", "Medium", "Low"]
    recommendations: list[str]


class InvestigationInput(BaseModel):
    query: str


class InvestigationStatus(BaseModel):
    status: InvestigationWorkflowState
    progress: int
    total_steps: int


class InvestigationResponse(BaseModel):
    """API response for POST."""

    investigation_id: str
    status: str
