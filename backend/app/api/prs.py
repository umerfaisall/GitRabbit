from fastapi import APIRouter, HTTPException

from app.models.pr import Pipeline, PrSummary, Report
from app.services import mock_data

router = APIRouter(prefix="/api/prs", tags=["prs"])


@router.get("", response_model=list[PrSummary])
def list_prs():
    return mock_data.list_prs()


@router.get("/{pr_id}/report", response_model=Report)
def get_report(pr_id: int):
    report = mock_data.get_report(pr_id)
    if report is None:
        raise HTTPException(status_code=404, detail="no report yet")
    return report


@router.get("/{pr_id}/pipeline", response_model=Pipeline)
def get_pipeline(pr_id: int):
    pipeline = mock_data.get_pipeline(pr_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="no pipeline state")
    return pipeline
