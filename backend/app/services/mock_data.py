from app.models.pr import Pipeline, PrSummary, Report

# Placeholder data standing in for real reads from Postgres (reports, job
# status) and Redis (live pipeline state). Replace call sites in
# app/api/prs.py with real service calls as each backend phase in
# TASKS.md lands — the function signatures below are the contract to keep.

_PRS: list[PrSummary] = [
    PrSummary(
        pr_id=101,
        repo="acme/widgets",
        title="Refactor payment retry logic",
        commit_sha="a1b2c3d",
        status="done",
        risk_score=78,
    ),
    PrSummary(
        pr_id=102,
        repo="acme/widgets",
        title="Add bulk export endpoint",
        commit_sha="e4f5g6h",
        status="running",
        risk_score=None,
    ),
]

_REPORTS: dict[int, Report] = {
    101: Report(
        pr_id=101,
        commit_sha="a1b2c3d",
        diff_summary={
            "files_changed": 4,
            "functions_changed": ["retry_payment", "_backoff_delay"],
        },
        blast_radius={
            "callers": ["process_order", "handle_webhook_event"],
            "uncovered_callers": ["handle_webhook_event"],
        },
        risk_score={
            "value": 78,
            "breakdown": {"blast_radius": 40, "coverage_gap": 25, "churn": 13},
        },
        suggestions=[
            {
                "file": "tests/test_payments.py",
                "kind": "missing_test",
                "detail": "No test covers handle_webhook_event after retry_payment change.",
            }
        ],
    )
}

_PIPELINES: dict[int, Pipeline] = {
    102: Pipeline(
        pr_id=102,
        commit_sha="e4f5g6h",
        nodes=[
            {"name": "diff-parser", "status": "done"},
            {"name": "impact-analyzer", "status": "running"},
            {"name": "risk-scorer", "status": "running"},
            {"name": "suggestion-agent", "status": "pending"},
            {"name": "report-composer", "status": "pending"},
        ],
    )
}


def list_prs() -> list[PrSummary]:
    return _PRS


def get_report(pr_id: int) -> Report | None:
    return _REPORTS.get(pr_id)


def get_pipeline(pr_id: int) -> Pipeline | None:
    return _PIPELINES.get(pr_id)
