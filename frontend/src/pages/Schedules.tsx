import { FormEvent, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import {
  useCreateSchedule, useCreateTemplate, useDeleteSchedule, useSchedules, useTemplates, useTriggerSchedule,
} from "../api/queries";
import type { WorkflowType } from "../api/types";
import { getStoredUser } from "../lib/auth";

const WORKFLOWS: { value: WorkflowType; label: string; pathTemplate: string; waitSelector: string }[] = [
  { value: "hotel_pricing_watch", label: "Hotel Pricing Watch", pathTemplate: "/hotels/{entity}", waitSelector: ".hotel-card" },
  { value: "competitor_offer_tracking", label: "Competitor Offer Tracking", pathTemplate: "/competitor/{entity}", waitSelector: ".offer-card" },
  { value: "campaign_page_monitoring", label: "Campaign Page Monitoring", pathTemplate: "/campaign/{entity}", waitSelector: ".campaign-hero" },
  { value: "partner_update_review", label: "Partner Update Review", pathTemplate: "/partner/{entity}", waitSelector: ".update-item" },
  { value: "travel_trend_scanning", label: "Travel Trend Scanning", pathTemplate: "/trends", waitSelector: ".trend-item" },
];

const FREQUENCIES = ["hourly", "daily", "weekly", "one_time", "campaign_driven", "event_triggered"];
const MANAGE_ROLES = ["administrator", "operations_owner"];

export default function Schedules() {
  const { data: schedules } = useSchedules();
  const { data: templates } = useTemplates();
  const createTemplate = useCreateTemplate();
  const createSchedule = useCreateSchedule();
  const deleteSchedule = useDeleteSchedule();
  const triggerSchedule = useTriggerSchedule();

  const user = getStoredUser();
  const canManage = !!user && MANAGE_ROLES.includes(user.role);

  const [workflowType, setWorkflowType] = useState<WorkflowType>("hotel_pricing_watch");
  const [entityKey, setEntityKey] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!entityKey.trim()) {
      setError("Entity is required.");
      return;
    }
    try {
      const workflow = WORKFLOWS.find((w) => w.value === workflowType)!;
      let template = (templates ?? []).find((t) => t.workflow_type === workflowType);
      if (!template) {
        template = await createTemplate.mutateAsync({
          name: `${workflow.label} (auto)`,
          workflow_type: workflowType,
          path_template: workflow.pathTemplate,
          objective_template: `Track ${workflow.label.toLowerCase()} for {entity}`,
          wait_selector: workflow.waitSelector,
          default_frequency: frequency,
        });
      }
      await createSchedule.mutateAsync({
        template_id: template.id, workflow_type: workflowType, entity_key: entityKey.trim(), frequency,
      });
      setEntityKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create schedule.");
    }
  }

  return (
    <div className="mx-auto max-w-4xl p-10">
      <h1 className="text-3xl font-bold">Scheduling</h1>
      <p className="mt-2 text-base text-muted-foreground">
        Recurring workflows the scheduler triggers automatically, on the frequency you set below.
      </p>

      {canManage ? (
        <Card className="mt-6 shadow-sm">
          <CardHeader className="px-8 py-6"><CardTitle className="text-xl">New schedule</CardTitle></CardHeader>
          <CardContent className="px-8 py-6">
            <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-4">
              <select
                value={workflowType}
                onChange={(e) => setWorkflowType(e.target.value as WorkflowType)}
                className="rounded-lg border border-input bg-background px-3 py-2.5 text-base md:col-span-2"
              >
                {WORKFLOWS.map((w) => <option key={w.value} value={w.value}>{w.label}</option>)}
              </select>
              <input
                value={entityKey}
                onChange={(e) => setEntityKey(e.target.value)}
                placeholder="Entity, e.g. Goa"
                className="rounded-lg border border-input bg-background px-3 py-2.5 text-base"
              />
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="rounded-lg border border-input bg-background px-3 py-2.5 text-base"
              >
                {FREQUENCIES.map((f) => <option key={f} value={f}>{f.replace(/_/g, " ")}</option>)}
              </select>
              <Button type="submit" disabled={createSchedule.isPending} className="md:col-span-4">
                {createSchedule.isPending ? "Creating" : "Create schedule"}
              </Button>
              {error && <p className="text-base text-destructive md:col-span-4">{error}</p>}
            </form>
          </CardContent>
        </Card>
      ) : (
        <p className="mt-6 text-base text-muted-foreground">
          Only administrators or operations owners can create or change schedules.
        </p>
      )}

      <Card className="mt-6 shadow-sm">
        <CardContent className="p-0">
          <table className="w-full text-base">
            <thead>
              <tr className="border-b border-border text-left text-sm text-muted-foreground">
                <th className="px-5 py-3">Entity</th>
                <th className="px-3 py-3">Workflow</th>
                <th className="px-3 py-3">Frequency</th>
                <th className="px-3 py-3">Enabled</th>
                <th className="px-3 py-3">Last run</th>
                {canManage && <th className="px-5 py-3 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {(schedules ?? []).map((s) => (
                <tr key={s.id} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 font-medium">{s.entity_key}</td>
                  <td className="px-3 py-3 font-mono text-sm text-muted-foreground">{s.workflow_type}</td>
                  <td className="px-3 py-3">{s.frequency.replace(/_/g, " ")}</td>
                  <td className="px-3 py-3"><Badge variant={s.enabled ? "success" : "outline"}>{s.enabled ? "on" : "off"}</Badge></td>
                  <td className="px-3 py-3 text-sm text-muted-foreground">
                    {s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "never"}
                  </td>
                  {canManage && (
                    <td className="px-5 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => triggerSchedule.mutate(s.id)} disabled={triggerSchedule.isPending}>
                          Run now
                        </Button>
                        <Button variant="destructive" onClick={() => deleteSchedule.mutate(s.id)} disabled={deleteSchedule.isPending}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {(schedules ?? []).length === 0 && (
                <tr><td colSpan={canManage ? 6 : 5} className="px-5 py-8 text-center text-base text-muted-foreground">No schedules configured yet</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
