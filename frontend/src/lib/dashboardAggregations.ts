// Pure, deterministic client-side aggregation helpers for the Operations
// Dashboard widgets. These are display-layer groupings only (counts/averages
// over data already fetched from the API) - no business logic, no
// calculations that belong server-side (percent diffs, significance, etc.
// are computed by the backend per the engineering guidelines' AI/deterministic boundary;
// this file only reshapes already-computed fields for charting).
import type { ModelInvocation, Run, RunState, Signal, WorkflowType } from "../api/types";

const DAY_MS = 24 * 60 * 60 * 1000;

export interface RunsPerDayBucket {
  date: string; // YYYY-MM-DD
  label: string; // short display label, e.g. "Aug 5"
  COMPLETED: number;
  FAILED: number;
  IN_PROGRESS: number;
  CANCELLED: number;
  total: number;
}

const TERMINAL_OK = new Set(["COMPLETED"]);
const TERMINAL_FAIL = new Set(["FAILED"]);
const TERMINAL_CANCELLED = new Set(["CANCELLED"]);

function bucketForState(state: RunState): keyof Omit<RunsPerDayBucket, "date" | "label" | "total"> {
  if (TERMINAL_OK.has(state)) return "COMPLETED";
  if (TERMINAL_FAIL.has(state)) return "FAILED";
  if (TERMINAL_CANCELLED.has(state)) return "CANCELLED";
  return "IN_PROGRESS";
}

// Groups runs by calendar day (based on created_at) for the last `days`
// days, bucketed by coarse state. Client-side grouping is reasonable here
// because this widget looks at a bounded recent window, not the full
// historical run list.
export function runsPerDay(runs: Run[], days = 14, now: Date = new Date()): RunsPerDayBucket[] {
  const buckets = new Map<string, RunsPerDayBucket>();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  start.setTime(start.getTime() - (days - 1) * DAY_MS);

  for (let i = 0; i < days; i++) {
    const d = new Date(start.getTime() + i * DAY_MS);
    const date = d.toISOString().slice(0, 10);
    buckets.set(date, {
      date,
      label: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      COMPLETED: 0,
      FAILED: 0,
      IN_PROGRESS: 0,
      CANCELLED: 0,
      total: 0,
    });
  }

  const windowStart = start.getTime();
  for (const run of runs) {
    const created = new Date(run.created_at).getTime();
    if (Number.isNaN(created) || created < windowStart) continue;
    const date = new Date(created).toISOString().slice(0, 10);
    const bucket = buckets.get(date);
    if (!bucket) continue;
    const key = bucketForState(run.state);
    bucket[key] += 1;
    bucket.total += 1;
  }

  return Array.from(buckets.values());
}

export interface SeverityCount {
  severity: Signal["severity"];
  count: number;
}

const SEVERITY_ORDER: Signal["severity"][] = ["low", "medium", "high", "critical"];

export function signalsBySeverity(signals: Signal[]): SeverityCount[] {
  const counts = new Map<Signal["severity"], number>(SEVERITY_ORDER.map((s) => [s, 0]));
  for (const s of signals) {
    counts.set(s.severity, (counts.get(s.severity) ?? 0) + 1);
  }
  return SEVERITY_ORDER.map((severity) => ({ severity, count: counts.get(severity) ?? 0 }));
}

export interface WorkflowCount {
  workflow_type: WorkflowType;
  label: string;
  count: number;
}

const WORKFLOW_LABELS: Record<WorkflowType, string> = {
  hotel_pricing_watch: "Hotel pricing",
  competitor_offer_tracking: "Competitor offers",
  campaign_page_monitoring: "Campaign pages",
  partner_update_review: "Partner updates",
  travel_trend_scanning: "Travel trends",
};

const WORKFLOW_ORDER: WorkflowType[] = [
  "hotel_pricing_watch",
  "competitor_offer_tracking",
  "campaign_page_monitoring",
  "partner_update_review",
  "travel_trend_scanning",
];

// Runs don't carry workflow_type directly (only task_id) - callers pass a
// task_id -> workflow_type lookup built from useTasks() so this stays a pure
// function over already-fetched data rather than a new endpoint.
export function workflowBreakdown(
  runs: Run[],
  taskWorkflowByTaskId: Map<string, WorkflowType>
): WorkflowCount[] {
  const counts = new Map<WorkflowType, number>(WORKFLOW_ORDER.map((w) => [w, 0]));
  for (const run of runs) {
    const workflow = taskWorkflowByTaskId.get(run.task_id);
    if (!workflow) continue;
    counts.set(workflow, (counts.get(workflow) ?? 0) + 1);
  }
  return WORKFLOW_ORDER.map((workflow_type) => ({
    workflow_type,
    label: WORKFLOW_LABELS[workflow_type],
    count: counts.get(workflow_type) ?? 0,
  }));
}

export interface AiActivitySummary {
  totalCalls: number;
  geminiCount: number;
  fallbackCount: number;
  geminiPct: number;
  avgLatencyMs: number | null;
}

export function summarizeAiActivity(calls: ModelInvocation[]): AiActivitySummary {
  const totalCalls = calls.length;
  const geminiCount = calls.filter((c) => c.success && c.provider === "gemini").length;
  const fallbackCount = calls.filter((c) => c.success && c.provider !== "gemini").length;
  const successCount = geminiCount + fallbackCount;
  const geminiPct = successCount > 0 ? Math.round((geminiCount / successCount) * 100) : 0;
  const latencies = calls.map((c) => c.latency_ms).filter((v): v is number => typeof v === "number");
  const avgLatencyMs = latencies.length > 0
    ? Math.round(latencies.reduce((sum, v) => sum + v, 0) / latencies.length)
    : null;
  return { totalCalls, geminiCount, fallbackCount, geminiPct, avgLatencyMs };
}
