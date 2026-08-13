export type WorkflowType =
  | "hotel_pricing_watch"
  | "competitor_offer_tracking"
  | "campaign_page_monitoring"
  | "partner_update_review"
  | "travel_trend_scanning";

export interface Task {
  id: string;
  objective: string;
  workflow_type: WorkflowType;
  entity_key: string;
  owner: string | null;
  risk_level: string;
  review_required: boolean;
  created_at: string;
}

export type RunState =
  | "CREATED" | "VALIDATING" | "PLANNING" | "PLAN_READY" | "AWAITING_APPROVAL" | "APPROVED" | "QUEUED"
  | "BROWSER_STARTING" | "BROWSING" | "EXTRACTION" | "VALIDATING_DATA" | "SNAPSHOTTING" | "COMPARING"
  | "REASONING" | "REVIEW_REQUIRED" | "COMPLETING" | "COMPLETED"
  | "RECOVERY" | "RERUN_REQUESTED" | "FAILED" | "CANCELLED";

export interface Run {
  id: string;
  task_id: string;
  plan_id: string | null;
  state: RunState;
  created_at: string;
  updated_at: string;
  error_type: string | null;
  error_message: string | null;
  archived: boolean;
  archived_at: string | null;
  archived_by: string | null;
}

export interface RunStep {
  step_order: number;
  previous_state: string | null;
  new_state: string;
  actor: string;
  reason: string | null;
  created_at: string;
}

export interface Evidence {
  id: string;
  source_url: string;
  page_title: string | null;
  captured_at: string;
  screenshot_object_key: string | null;
  html_object_key: string | null;
  screenshot_url: string | null;
  confidence: number | null;
  validation_status: string;
  artifact_purged: boolean;
}

export interface Change {
  entity_name: string;
  change_type: string;
  previous_value: string | null;
  current_value: string | null;
  abs_diff: number | null;
  delta_pct: number | null;
  significance: "insignificant" | "minor" | "notable" | "significant";
  business_relevant: boolean;
  is_noise: boolean;
}

export interface Signal {
  id: string;
  run_id: string;
  change_id: string | null;
  signal_type: string;
  severity: "low" | "medium" | "high" | "critical";
  observations: string;
  business_impact: string | null;
  confidence: number;
  recommendation: string | null;
  owner: string | null;
  requires_human_review: boolean;
  created_at: string;
}

export interface Review {
  id: string;
  run_id: string;
  trigger_reason: string;
  status: "pending" | "approved" | "rejected" | "corrected";
  reviewer_id: string | null;
  action: string | null;
  reason: string | null;
  original_value: string | null;
  corrected_value: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface RunSummary {
  headline: string;
  key_changes: string[];
  recommended_owner: string | null;
  confidence_note: string | null;
  requires_human_review: boolean;
  generated_by: string;
}

export interface RunResults {
  run: Run;
  summary: RunSummary | null;
  snapshots: { id: string; entity_key: string; captured_at: string; fields: Record<string, string> }[];
  changes: Change[];
  signals: Signal[];
  reviews: { id: string; trigger_reason: string; status: string; action: string | null }[];
}

export interface TaskTemplate {
  id: string;
  name: string;
  workflow_type: WorkflowType;
  description: string | null;
  path_template: string;
  objective_template: string;
  wait_selector: string;
  default_frequency: string;
  owner_team: string | null;
  requires_approval: boolean;
}

export interface Schedule {
  id: string;
  template_id: string;
  workflow_type: WorkflowType;
  entity_key: string;
  frequency: string;
  enabled: boolean;
  owner_team: string | null;
  last_run_id: string | null;
  last_run_at: string | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  services: Record<string, string>;
}

export interface Source {
  id: string;
  domain: string;
  category: string;
  owner: string;
  health_state: "HEALTHY" | "DEGRADED" | "UNSTABLE" | "FAILED" | "REVIEW_REQUIRED";
  consecutive_failures: number;
  total_runs: number;
  total_failures: number;
}

export interface RecoveryAttempt {
  candidate_selector: string | null;
  result: string;
  confidence: number | null;
  recovery_strategy: string | null;
}

export interface PlanStep {
  step_order: number;
  action: string;
  target: string;
  notes: string | null;
}

export interface Plan {
  id: string;
  task_id: string;
  objective: string;
  status: string;
  risk_notes: string | null;
  stop_conditions: string[];
  rejection_reason: string | null;
  steps: PlanStep[];
}

export interface ChangeFeedItem {
  id: string;
  run_id: string;
  entity_name: string;
  entity_key: string;
  change_type: string;
  previous_value: string | null;
  current_value: string | null;
  abs_diff: number | null;
  delta_pct: number | null;
  significance: "insignificant" | "minor" | "notable" | "significant";
  business_relevant: boolean;
  is_noise: boolean;
  created_at: string;
}

export interface ModelInvocation {
  id: string;
  run_id: string | null;
  chat_session_id: string | null;
  node: string;
  provider: string;
  model_name: string;
  purpose: string;
  prompt_summary: string | null;
  input_ref_ids: Record<string, unknown> | null;
  output_summary: string | null;
  tokens_prompt: number | null;
  tokens_completion: number | null;
  latency_ms: number;
  fallback_triggered: boolean;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export interface Failure {
  id: string;
  run_id: string;
  error_type: string;
  message: string;
  retryable: boolean;
  retry_count: number;
  recovery_state: string;
  created_at: string;
  recovery_attempts: RecoveryAttempt[];
}

export interface ChatMessageResponse {
  session_id: string;
  reply: string;
  grounded: boolean;
  source_type: "internal_data" | "general_knowledge";
  evidence_refs: string[];
}

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  grounded: boolean;
  source_type: "internal_data" | "general_knowledge" | null;
  evidence_refs: string[];
  created_at: string;
}

export interface ChatTranscriptResponse {
  session_id: string;
  messages: ChatMessageItem[];
}
