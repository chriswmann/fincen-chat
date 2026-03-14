from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from temporalio.client import Client
from ..config import get_temporal_config
from .models import (
    InvestigationInput,
    InvestigationReport,
    InvestigationResponse,
    InvestigationStatus,
    InvestigationWorkflowState,
)
from .workflows import InvestigationWorkflow

router = APIRouter(prefix="/investigations")


async def get_temporal_client(request: Request) -> Client:
    """Dependency that returns a temporal client."""
    return request.app.state.temporal_client


@router.post("", response_model=InvestigationResponse)
async def start_investigation(
    body: InvestigationInput,
    client: Client = Depends(get_temporal_client),
) -> InvestigationResponse:
    """Start a new investigation workflow and return its ID."""
    investigation_id = str(uuid4())
    await client.start_workflow(
        InvestigationWorkflow.run,
        InvestigationInput(query=body.query),
        id=investigation_id,
        task_queue=get_temporal_config().temporal_task_queue,
    )
    return InvestigationResponse(
        investigation_id=investigation_id,
        status=InvestigationWorkflowState.PLANNING,
    )


@router.get("/{investigation_id}/status", response_model=InvestigationStatus)
async def get_investigation_status(
    investigation_id: str,
    client: Client = Depends(get_temporal_client),
) -> InvestigationStatus:
    """Pull the current status of a running investigation."""
    handle = client.get_workflow_handle(investigation_id)
    return await handle.query(InvestigationWorkflow.get_status)


@router.get("/{investigation_id}/result", response_model=InvestigationReport)
async def get_investigation_result(
    investigation_id: str,
    client: Client = Depends(get_temporal_client),
) -> InvestigationReport:
    """Fetch the completed report. Returns 409 if not yet completed."""
    handle = client.get_workflow_handle(investigation_id)
    status: InvestigationStatus = await handle.query(InvestigationWorkflow.get_status)
    if status.status != InvestigationWorkflowState.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"Investigation {investigation_id} is not yet complete (status: {status.status})",
        )
    return await handle.result()
