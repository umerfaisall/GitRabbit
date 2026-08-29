import { useEffect, useState } from "react"
import { fetchPipeline, fetchPrs, fetchReport } from "./api"
import type { Pipeline, PrSummary, Report } from "./types"

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    done: "bg-green-100 text-green-700",
    running: "bg-amber-100 text-amber-700",
    pending: "bg-slate-100 text-slate-600",
    error: "bg-red-100 text-red-700",
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? styles.pending}`}>
      {status}
    </span>
  )
}

function RiskBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-slate-400">—</span>
  const color = score >= 70 ? "text-red-600" : score >= 40 ? "text-amber-600" : "text-green-600"
  return <span className={`text-sm font-semibold ${color}`}>{score}</span>
}

function ReportView({ report }: { report: Report }) {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Diff summary
        </h3>
        <p className="text-sm text-slate-700">
          {report.diff_summary.files_changed} files changed —{" "}
          {report.diff_summary.functions_changed.join(", ")}
        </p>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Blast radius
        </h3>
        <ul className="text-sm text-slate-700 space-y-1">
          {report.blast_radius.callers.map((c) => (
            <li key={c} className="flex items-center gap-2">
              <span>{c}</span>
              {report.blast_radius.uncovered_callers.includes(c) && (
                <span className="text-xs text-red-600 font-medium">no test coverage</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Risk score — {report.risk_score.value}
        </h3>
        <div className="flex gap-4 text-sm text-slate-700">
          {Object.entries(report.risk_score.breakdown).map(([k, v]) => (
            <span key={k}>
              {k}: <span className="font-medium">{v}</span>
            </span>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Suggestions
        </h3>
        <ul className="space-y-2">
          {report.suggestions.map((s, i) => (
            <li key={i} className="text-sm bg-slate-50 border border-slate-200 rounded p-3">
              <div className="font-medium text-slate-800">{s.file}</div>
              <div className="text-slate-600">{s.detail}</div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function PipelineView({ pipeline }: { pipeline: Pipeline }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
        Pipeline progress
      </h3>
      <ol className="space-y-2">
        {pipeline.nodes.map((n) => (
          <li key={n.name} className="flex items-center justify-between border border-slate-200 rounded px-3 py-2">
            <span className="text-sm text-slate-800">{n.name}</span>
            <StatusBadge status={n.status} />
          </li>
        ))}
      </ol>
    </div>
  )
}

function App() {
  const [prs, setPrs] = useState<PrSummary[]>([])
  const [selected, setSelected] = useState<PrSummary | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPrs()
      .then(setPrs)
      .catch(() => setError("Could not reach backend at localhost:8000 — is it running?"))
  }, [])

  useEffect(() => {
    if (!selected) return
    setReport(null)
    setPipeline(null)
    if (selected.status === "done") {
      fetchReport(selected.pr_id).then(setReport)
    } else {
      fetchPipeline(selected.pr_id).then(setPipeline)
    }
  }, [selected])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold">PR Review Orchestrator</h1>
        <p className="text-sm text-slate-500">mock dashboard — backend data is placeholder</p>
      </header>

      {error && (
        <div className="m-6 bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3">
          {error}
        </div>
      )}

      <div className="flex">
        <aside className="w-80 border-r border-slate-200 bg-white min-h-[calc(100vh-73px)]">
          {prs.map((pr) => (
            <button
              key={pr.pr_id}
              onClick={() => setSelected(pr)}
              className={`w-full text-left px-4 py-3 border-b border-slate-100 hover:bg-slate-50 ${
                selected?.pr_id === pr.pr_id ? "bg-slate-100" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">#{pr.pr_id}</span>
                <RiskBadge score={pr.risk_score} />
              </div>
              <div className="text-sm text-slate-700 truncate">{pr.title}</div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-slate-400">{pr.repo}</span>
                <StatusBadge status={pr.status} />
              </div>
            </button>
          ))}
        </aside>

        <main className="flex-1 p-6">
          {!selected && <p className="text-sm text-slate-400">Select a PR to view its report.</p>}
          {selected && report && <ReportView report={report} />}
          {selected && pipeline && <PipelineView pipeline={pipeline} />}
        </main>
      </div>
    </div>
  )
}

export default App
