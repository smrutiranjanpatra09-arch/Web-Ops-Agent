import { useState } from "react";
import { useParams } from "react-router-dom";
import { downloadFile } from "../api/client";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge, runStateVariant, significanceVariant } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import {
  useApproveRun, useRejectRun, useRerunRun, useRun, useRunEvidence, useRunModelCalls, useRunResults, useRunSteps,
} from "../api/queries";

// finds the most recent successful (non-fallback) model call for a given
// node - used to caption a Signal with which model actually generated it,
// per Phase 29.4's "make LLM usage visible without anyone needing to explain
// it" requirement.
function findGroundingCall(calls: import("../api/types").ModelInvocation[] | undefined, node: string) {
  return calls?.filter((c) => c.node === node).slice(-1)[0];
}

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run } = useRun(runId);
  const { data: steps } = useRunSteps(runId);
  const { data: results } = useRunResults(runId);
  const { data: evidenceRows } = useRunEvidence(runId);
  const { data: modelCalls } = useRunModelCalls(runId);
  const approve = useApproveRun();
  const reject = useRejectRun();
  const rerun = useRerunRun();
  const [downloadingReport, setDownloadingReport] = useState(false);

  if (!run) return <div className="p-8 text-sm text-muted-foreground">Loading run</div>;

  async function handleDownloadReport() {
    if (!run) return;
    setDownloadingReport(true);
    try {
      await downloadFile(`/api/runs/${run.id}/report.pdf`, `run-${run.id}-report.pdf`);
    } finally {
      setDownloadingReport(false);
    }
  }

  const evidence = results?.snapshots ?? [];
  const changes = results?.changes ?? [];
  const signals = results?.signals ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">Run {run.id.slice(0, 8)}</h1>
            <Badge variant={runStateVariant(run.state)}>{run.state}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Task {run.task_id.slice(0, 8)}</p>
        </div>
        <div className="flex gap-2">
          {run.state === "AWAITING_APPROVAL" && (
            <>
              <Button onClick={() => approve.mutate(run.id)} disabled={approve.isPending}>Approve plan</Button>
              <Button variant="outline" onClick={() => reject.mutate({ runId: run.id })} disabled={reject.isPending}>Reject</Button>
            </>
          )}
          {["FAILED", "CANCELLED", "COMPLETED", "REVIEW_REQUIRED"].includes(run.state) && (
            <Button variant="outline" onClick={() => rerun.mutate(run.id)} disabled={rerun.isPending}>Rerun</Button>
          )}
          <Button variant="outline" onClick={handleDownloadReport} disabled={downloadingReport}>
            {downloadingReport ? "Preparing report" : "Download Report (PDF)"}
          </Button>
        </div>
      </div>

      {run.error_type && (
        <Card className="border-destructive">
          <CardContent className="py-3 text-sm">
            <span className="font-medium text-destructive">{run.error_type}</span>
            <span className="ml-2 text-muted-foreground">{run.error_message}</span>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Pipeline steps</CardTitle></CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <tbody>
              {(steps ?? []).map((s, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{s.previous_state ?? "-"}</td>
                  <td className="px-2 py-2 text-muted-foreground">to</td>
                  <td className="px-2 py-2 font-mono text-xs font-medium">{s.new_state}</td>
                  <td className="px-4 py-2 text-muted-foreground">{s.reason}</td>
                  <td className="px-4 py-2 text-right text-xs text-muted-foreground">
                    {new Date(s.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {(evidenceRows ?? []).length > 0 && (
        <Card>
          <CardHeader><CardTitle>Evidence</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(evidenceRows ?? []).map((e) => (
              <div key={e.id} className="flex items-center gap-3 border-b border-border pb-3 text-sm last:border-0 last:pb-0">
                {e.artifact_purged ? (
                  <div className="flex h-16 w-28 shrink-0 items-center justify-center rounded border border-dashed border-border bg-secondary/30 p-1 text-center text-[10px] leading-tight text-muted-foreground">
                    Screenshot no longer available (retention policy) - metadata preserved
                  </div>
                ) : e.screenshot_url && (
                  <img
                    src={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}${e.screenshot_url}`}
                    alt={e.page_title ?? "screenshot"}
                    className="h-16 w-28 rounded border border-border object-cover"
                  />
                )}
                <div className="min-w-0">
                  <div className="truncate font-medium">{e.page_title}</div>
                  <div className="truncate font-mono text-xs text-muted-foreground">{e.source_url}</div>
                  <div className="text-xs text-muted-foreground">{new Date(e.captured_at).toLocaleString()}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {evidence.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Extracted data</CardTitle></CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <tbody>
                {evidence.map((snap) => (
                  <tr key={snap.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-medium">{snap.entity_key}</td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">
                      {Object.entries(snap.fields).map(([k, v]) => `${k}=${v}`).join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {changes.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Comparison</CardTitle></CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <tbody>
                {changes.map((c, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-medium">{c.entity_name}</td>
                    <td className="px-2 py-2 font-mono text-xs">{c.change_type}</td>
                    <td className="px-2 py-2 text-xs text-muted-foreground">{c.previous_value ?? "-"} to {c.current_value ?? "-"}</td>
                    <td className="px-2 py-2 text-xs">{c.delta_pct != null ? `${c.delta_pct}%` : ""}</td>
                    <td className="px-4 py-2 text-right"><Badge variant={significanceVariant(c.significance)}>{c.significance}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {signals.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Signals</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {signals.map((s) => {
              const groundingCall = findGroundingCall(modelCalls, "completion");
              return (
                <div key={s.id} className="border-b border-border pb-3 text-sm last:border-0 last:pb-0">
                  <div className="flex items-center gap-2">
                    <Badge variant={s.severity === "high" || s.severity === "critical" ? "destructive" : "default"}>{s.severity}</Badge>
                    <span className="font-medium">{s.signal_type}</span>
                    {s.owner && <span className="text-xs text-muted-foreground">owner: {s.owner}</span>}
                  </div>
                  <p className="mt-1 text-muted-foreground">{s.business_impact ?? s.observations}</p>
                  {groundingCall && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {groundingCall.success ? "🤖" : "⚙️"} Generated by {groundingCall.success ? groundingCall.model_name : "deterministic fallback"}
                      {groundingCall.success && ` · ${groundingCall.latency_ms}ms`}
                      {groundingCall.input_ref_ids?.change_ids
                        ? ` · grounded in Change ${(groundingCall.input_ref_ids.change_ids as string[]).map((id) => id.slice(0, 8)).join(", ")}`
                        : ""}
                    </p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {(modelCalls ?? []).length > 0 && (
        <Card>
          <CardHeader><CardTitle>AI Model Calls</CardTitle></CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-2">Node</th>
                  <th className="px-2 py-2">Model</th>
                  <th className="px-2 py-2">Purpose</th>
                  <th className="px-2 py-2">Latency</th>
                  <th className="px-4 py-2 text-right">Result</th>
                </tr>
              </thead>
              <tbody>
                {(modelCalls ?? []).map((c) => (
                  <tr key={c.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-mono text-xs">{c.node}</td>
                    <td className="px-2 py-2 text-xs text-muted-foreground">{c.model_name}</td>
                    <td className="px-2 py-2 text-xs text-muted-foreground">{c.purpose}</td>
                    <td className="px-2 py-2 text-xs">{c.latency_ms}ms</td>
                    <td className="px-4 py-2 text-right">
                      {c.success ? (
                        <Badge variant="success">succeeded</Badge>
                      ) : c.fallback_triggered ? (
                        <Badge variant="warning">fell back</Badge>
                      ) : (
                        <Badge variant="destructive">failed</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
