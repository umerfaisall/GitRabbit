from typing import Literal

from pydantic import BaseModel

# Mirrors frontend/src/types.ts. Not final — see TASKS.md Phase 7 for the
# Postgres schema this will eventually be backed by.

PrStatus = Literal["pending", "running", "done", "error"]


class PrSummary(BaseModel):
    pr_id: int
    repo: str
    title: str
    commit_sha: str
    status: PrStatus
    risk_score: int | None


class DiffSummary(BaseModel):
    files_changed: int
    functions_changed: list[str]


class BlastRadius(BaseModel):
    callers: list[str]
    uncovered_callers: list[str]


class RiskScore(BaseModel):
    value: int
    breakdown: dict[str, int]


class Suggestion(BaseModel):
    file: str
    kind: str
    detail: str


class Report(BaseModel):
    pr_id: int
    commit_sha: str
    diff_summary: DiffSummary
    blast_radius: BlastRadius
    risk_score: RiskScore
    suggestions: list[Suggestion]


class PipelineNode(BaseModel):
    name: str
    status: PrStatus


class Pipeline(BaseModel):
    pr_id: int
    commit_sha: str
    nodes: list[PipelineNode]
