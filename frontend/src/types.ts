// Mirrors the mock shapes returned by the FastAPI backend (backend/app/main.py).
// Not final — see project.md's open decision on the Postgres/report schema.

export type PrStatus = "pending" | "running" | "done" | "error"

export interface PrSummary {
  pr_id: number
  repo: string
  title: string
  commit_sha: string
  status: PrStatus
  risk_score: number | null
}

export interface Report {
  pr_id: number
  commit_sha: string
  diff_summary: {
    files_changed: number
    functions_changed: string[]
  }
  blast_radius: {
    callers: string[]
    uncovered_callers: string[]
  }
  risk_score: {
    value: number
    breakdown: Record<string, number>
  }
  suggestions: Array<{
    file: string
    kind: string
    detail: string
  }>
}

export interface PipelineNode {
  name: string
  status: PrStatus
}

export interface Pipeline {
  pr_id: number
  commit_sha: string
  nodes: PipelineNode[]
}
