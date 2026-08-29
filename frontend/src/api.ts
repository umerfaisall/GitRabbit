import type { Pipeline, PrSummary, Report } from "./types"

const BASE_URL = "http://localhost:8000"

export async function fetchPrs(): Promise<PrSummary[]> {
  const res = await fetch(`${BASE_URL}/api/prs`)
  return res.json()
}

export async function fetchReport(prId: number): Promise<Report> {
  const res = await fetch(`${BASE_URL}/api/prs/${prId}/report`)
  return res.json()
}

export async function fetchPipeline(prId: number): Promise<Pipeline> {
  const res = await fetch(`${BASE_URL}/api/prs/${prId}/pipeline`)
  return res.json()
}
