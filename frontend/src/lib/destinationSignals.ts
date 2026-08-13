import type { Run, Signal, Task } from "../api/types";
import { resolveDestinationCoords, type DestinationCoords } from "./destinations";

export type DestinationSeverity = "none" | "notable" | "significant";

export interface MonitoredDestination {
  name: string;
  coords: DestinationCoords;
  severity: DestinationSeverity;
  openSignalCount: number;
}

// A signal's severity ("low"|"medium"|"high"|"critical") is a run-level
// classification; we roll it up to the coarse pin-color scale the map uses.
function pinSeverity(severity: Signal["severity"]): DestinationSeverity {
  if (severity === "critical" || severity === "high") return "significant";
  if (severity === "medium") return "notable";
  return "none";
}

const SEVERITY_RANK: Record<DestinationSeverity, number> = { none: 0, notable: 1, significant: 2 };

// Joins tasks -> runs -> signals (all already fetched via existing hooks) to
// find, for each monitored destination, the most severe open signal. Only
// destinations resolvable to known demo coordinates are included, since
// there is nowhere to plot the rest without inventing coordinates.
export function buildMonitoredDestinations(
  tasks: Task[],
  runs: Run[],
  signals: Signal[]
): MonitoredDestination[] {
  const taskEntityById = new Map(tasks.map((t) => [t.id, t.entity_key]));
  const entityByRunId = new Map<string, string>();
  for (const run of runs) {
    const entity = taskEntityById.get(run.task_id);
    if (entity) entityByRunId.set(run.id, entity);
  }

  const byDestination = new Map<string, MonitoredDestination>();

  // seed every destination that has at least one task targeting it, even
  // with zero signals, so "monitored but currently clean" still shows green.
  for (const task of tasks) {
    const coords = resolveDestinationCoords(task.entity_key);
    if (!coords) continue;
    const name = destinationNameFor(task.entity_key);
    if (!byDestination.has(name)) {
      byDestination.set(name, { name, coords, severity: "none", openSignalCount: 0 });
    }
  }

  for (const signal of signals) {
    const entity = entityByRunId.get(signal.run_id);
    if (!entity) continue;
    const coords = resolveDestinationCoords(entity);
    if (!coords) continue;
    const name = destinationNameFor(entity);
    const existing = byDestination.get(name) ?? { name, coords, severity: "none", openSignalCount: 0 };
    const severity = pinSeverity(signal.severity);
    if (SEVERITY_RANK[severity] > SEVERITY_RANK[existing.severity]) existing.severity = severity;
    if (signal.requires_human_review || severity !== "none") existing.openSignalCount += 1;
    byDestination.set(name, existing);
  }

  return Array.from(byDestination.values());
}

function destinationNameFor(entityKey: string): string {
  const lower = entityKey.toLowerCase();
  const known = ["Goa", "Jaipur", "Manali", "Udaipur", "Rishikesh"];
  return known.find((n) => lower.includes(n.toLowerCase())) ?? entityKey;
}
