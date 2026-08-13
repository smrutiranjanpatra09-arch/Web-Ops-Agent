import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

// URLSearchParams stringifies `undefined` as the literal text "undefined"
// instead of omitting the key, so a filterless query still sends
// ?node=undefined&provider=undefined - drop empty values before building it.
function buildQueryString(params?: Record<string, string | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  return entries.length ? `?${new URLSearchParams(entries as [string, string][]).toString()}` : "";
}
import type {
  ChangeFeedItem, ChatMessageResponse, ChatTranscriptResponse, Evidence, Failure, HealthResponse, ModelInvocation,
  Plan, Run, RunResults, RunStep, Schedule,
  Signal, Source, Task, TaskTemplate, WorkflowType,
} from "./types";

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: () => api.get<HealthResponse>("/api/health"), refetchInterval: 10000 });
}

export function useLogin() {
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api.post<{ access_token: string; user_id: string; display_name: string; role: string }>("/api/auth/login", body),
  });
}

export function useTasks() {
  return useQuery({ queryKey: ["tasks"], queryFn: () => api.get<Task[]>("/api/tasks") });
}

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: ["tasks", taskId],
    queryFn: () => api.get<Task>(`/api/tasks/${taskId}`),
    enabled: !!taskId,
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      objective: string; workflow_type: WorkflowType; entity_key: string; target_url: string;
      owner?: string; risk_level?: string; review_required?: boolean;
    }) => api.post<Task>("/api/tasks", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useRuns() {
  return useQuery({ queryKey: ["runs"], queryFn: () => api.get<Run[]>("/api/runs"), refetchInterval: 5000 });
}

// backs the Run History page's filter bar + pager (Phase 37.1) - `offset`
// makes this a real "load more" rather than the previous unbounded
// single-fetch table capped by the backend's default limit.
export function useFilteredRuns(params: {
  state?: string; workflow_type?: string; since?: string; limit?: number; offset?: number;
  include_archived?: boolean;
}) {
  const query = buildQueryString({
    state: params.state, workflow_type: params.workflow_type, since: params.since,
    limit: params.limit !== undefined ? String(params.limit) : undefined,
    offset: params.offset !== undefined ? String(params.offset) : undefined,
    include_archived: params.include_archived ? "true" : undefined,
  });
  return useQuery({
    queryKey: ["runs", "filtered", params],
    queryFn: () => api.get<Run[]>(`/api/runs${query}`),
    refetchInterval: 5000,
  });
}

export function useArchiveRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.post(`/api/runs/${runId}/archive`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useBulkArchiveRuns() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { older_than_days: number; state?: string }) =>
      api.post<{ archived_run_ids: string[]; count: number }>("/api/runs/archive-bulk", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useHardDeleteRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, reason }: { runId: string; reason: string }) =>
      api.del(`/api/runs/${runId}`, { reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

// backs each journey-stage queue page (Phase 32) - one or more RunStates,
// polled frequently since these are meant to feel "live" (a run should
// disappear from Browser Monitor and appear in Extracted Data shortly after
// its real state transition, without a manual refresh).
export function useRunsByStates(states: string[]) {
  return useQuery({
    queryKey: ["runs", "by-states", states],
    queryFn: () => api.get<Run[]>(`/api/runs?states=${states.join(",")}`),
    refetchInterval: 3000,
  });
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["runs", runId],
    queryFn: () => api.get<Run>(`/api/runs/${runId}`),
    enabled: !!runId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      const terminal = ["COMPLETED", "FAILED", "CANCELLED", "AWAITING_APPROVAL", "REVIEW_REQUIRED"];
      return state && terminal.includes(state) ? false : 2000;
    },
  });
}

export function useRunSteps(runId: string | undefined) {
  return useQuery({
    queryKey: ["runs", runId, "steps"],
    queryFn: () => api.get<RunStep[]>(`/api/runs/${runId}/steps`),
    enabled: !!runId,
    refetchInterval: 3000,
  });
}

export function useRunEvidence(runId: string | undefined, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ["runs", runId, "evidence"],
    queryFn: () => api.get<Evidence[]>(`/api/runs/${runId}/evidence`),
    enabled: !!runId,
    refetchInterval: options?.refetchInterval,
  });
}

export function useRunResults(runId: string | undefined) {
  return useQuery({
    queryKey: ["runs", runId, "results"],
    queryFn: () => api.get<RunResults>(`/api/runs/${runId}/results`),
    enabled: !!runId,
  });
}

export function useStartRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (task_id: string) => api.post<Run>("/api/runs", { task_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useApproveRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.post<Run>(`/api/runs/${runId}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useRejectRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, reason }: { runId: string; reason?: string }) =>
      api.post<Run>(`/api/runs/${runId}/reject`, { reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useRerunRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.post<Run>(`/api/runs/${runId}/rerun`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useReviews(status?: string) {
  return useQuery({
    queryKey: ["reviews", status],
    queryFn: () => api.get<import("./types").Review[]>(`/api/reviews${status ? `?status=${status}` : ""}`),
    refetchInterval: 5000,
  });
}

export function useDecideReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, action, reason, correctedValue }: {
      reviewId: string; action: string; reason?: string; correctedValue?: string;
    }) => api.post(`/api/reviews/${reviewId}/decision`, { action, reason, corrected_value: correctedValue }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews"] });
      qc.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

export function useSignals(params?: { severity?: string; owner?: string; run_id?: string }) {
  return useQuery({
    queryKey: ["signals", params],
    queryFn: () => api.get<Signal[]>(`/api/signals${buildQueryString(params)}`),
    refetchInterval: 10000,
  });
}

export function useTemplates() {
  return useQuery({ queryKey: ["templates"], queryFn: () => api.get<TaskTemplate[]>("/api/templates") });
}

export function useCreateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string; workflow_type: WorkflowType; path_template: string;
      objective_template: string; wait_selector: string; default_frequency?: string;
    }) => api.post<TaskTemplate>("/api/templates", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useSchedules() {
  return useQuery({ queryKey: ["schedules"], queryFn: () => api.get<Schedule[]>("/api/schedules"), refetchInterval: 10000 });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      template_id: string; workflow_type: WorkflowType; entity_key: string; frequency: string;
    }) => api.post<Schedule>("/api/schedules", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scheduleId: string) => api.del(`/api/schedules/${scheduleId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function useTriggerSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scheduleId: string) => api.post(`/api/schedules/${scheduleId}/trigger`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function useSources() {
  return useQuery({ queryKey: ["sources"], queryFn: () => api.get<Source[]>("/api/sources"), refetchInterval: 10000 });
}

export function useFailures() {
  return useQuery({ queryKey: ["failures"], queryFn: () => api.get<Failure[]>("/api/failures"), refetchInterval: 10000 });
}

export function useRunModelCalls(runId: string | undefined) {
  return useQuery({
    queryKey: ["runs", runId, "model-calls"],
    queryFn: () => api.get<ModelInvocation[]>(`/api/runs/${runId}/model-calls`),
    enabled: !!runId,
  });
}

export function useModelCalls(params?: { node?: string; provider?: string; since?: string }) {
  return useQuery({
    queryKey: ["model-calls", params],
    queryFn: () => api.get<ModelInvocation[]>(`/api/model-calls${buildQueryString(params)}`),
    refetchInterval: 10000,
  });
}

export function usePlan(planId: string | null | undefined) {
  return useQuery({
    queryKey: ["plans", planId],
    queryFn: () => api.get<Plan>(`/api/plans/${planId}`),
    enabled: !!planId,
  });
}

export function useChangeFeed(params?: { workflow_type?: string; significance?: string }) {
  return useQuery({
    queryKey: ["changes", params],
    queryFn: () => api.get<ChangeFeedItem[]>(`/api/changes${buildQueryString(params)}`),
    refetchInterval: 5000,
  });
}

export function useSendChatMessage() {
  return useMutation({
    mutationFn: (body: { session_id?: string; message: string }) =>
      api.post<ChatMessageResponse>("/api/chat/message", body),
  });
}

export function useChatTranscript(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-transcript", sessionId],
    queryFn: () => api.get<ChatTranscriptResponse>(`/api/chat/sessions/${sessionId}/messages`),
    enabled: !!sessionId,
  });
}
