// the pipeline stages a task/run actually moves through, in order - this is
// the backbone of the journey-based layout (task -> plan -> run -> data ->
// insight -> action) so every surface visually shows where it sits in the
// flow instead of feeling like an independent page.
export interface JourneyStage {
  key: string;
  label: string;
  path: string;
  runStates: string[];
}

export const JOURNEY_STAGES: JourneyStage[] = [
  { key: "intake", label: "Task Intake", path: "/tasks/new", runStates: ["CREATED", "VALIDATING"] },
  { key: "plan", label: "Plan Review", path: "/journey/plan", runStates: ["PLANNING", "PLAN_READY", "AWAITING_APPROVAL", "APPROVED"] },
  { key: "browse", label: "Browser Monitor", path: "/journey/browse", runStates: ["QUEUED", "BROWSER_STARTING", "BROWSING", "RECOVERY"] },
  { key: "data", label: "Extracted Data", path: "/journey/data", runStates: ["EXTRACTION", "VALIDATING_DATA", "SNAPSHOTTING"] },
  { key: "compare", label: "Comparison", path: "/journey/compare", runStates: ["COMPARING"] },
  { key: "insight", label: "Insights & Signals", path: "/signals", runStates: ["REASONING"] },
  { key: "review", label: "Human Review", path: "/reviews", runStates: ["REVIEW_REQUIRED"] },
  { key: "complete", label: "Completion", path: "/journey/complete", runStates: ["COMPLETING", "COMPLETED"] },
];

export function stageForRunState(state: string | undefined): JourneyStage | undefined {
  if (!state) return undefined;
  return JOURNEY_STAGES.find((s) => s.runStates.includes(state));
}

export function stageIndex(stageKey: string | undefined): number {
  if (!stageKey) return -1;
  return JOURNEY_STAGES.findIndex((s) => s.key === stageKey);
}
