import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useCreateTask, useStartRun } from "../api/queries";
import type { WorkflowType } from "../api/types";

// The entity list here matches the mock site's real seeded entities
// (mock_site/app.py) - picking one derives a known-good URL automatically.
// "Custom URL" stays available for any future approved source: the browser
// worker's domain allowlist (not this form) is what actually enforces
// access, so this never artificially caps what a task can target.
const WORKFLOWS: {
  value: WorkflowType;
  label: string;
  entities: string[];
  buildUrl: (entity: string) => string;
}[] = [
  {
    value: "hotel_pricing_watch",
    label: "Hotel Pricing Watch",
    entities: ["Goa", "Jaipur", "Manali", "Udaipur", "Rishikesh"],
    buildUrl: (entity) => `http://mock-site:5050/hotels/${entity}`,
  },
  {
    value: "competitor_offer_tracking",
    label: "Competitor Offer Tracking",
    entities: ["RivalTrip", "OtherBooking", "QuickStay"],
    buildUrl: (entity) => `http://mock-site:5050/competitor/${entity}`,
  },
  {
    value: "campaign_page_monitoring",
    label: "Campaign Page Monitoring",
    entities: ["monsoon-getaway", "festive-flight-deals", "republic-day-sale"],
    buildUrl: (entity) => `http://mock-site:5050/campaign/${entity}`,
  },
  {
    value: "partner_update_review",
    label: "Partner Update Review",
    entities: ["Coastal Resorts Group", "Rajasthan Heritage Hotels", "Himalayan Stays Co-op"],
    buildUrl: (entity) => `http://mock-site:5050/partner/${encodeURIComponent(entity)}`,
  },
  {
    value: "travel_trend_scanning",
    label: "Travel Trend Scanning",
    entities: ["All destinations"],
    buildUrl: () => `http://mock-site:5050/trends`,
  },
];

const CUSTOM_ENTITY = "__custom__";

export default function TaskIntake() {
  const navigate = useNavigate();
  const createTask = useCreateTask();
  const startRun = useStartRun();

  const [workflowType, setWorkflowType] = useState<WorkflowType>("hotel_pricing_watch");
  const workflow = WORKFLOWS.find((w) => w.value === workflowType)!;
  const [entityKey, setEntityKey] = useState(workflow.entities[0]);
  const [customEntity, setCustomEntity] = useState("");
  const [customUrl, setCustomUrl] = useState("");
  const [objective, setObjective] = useState("");
  const [reviewRequired, setReviewRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCustom = entityKey === CUSTOM_ENTITY;

  // reset the entity selection whenever the workflow changes, so it never
  // points at an entity that doesn't exist for the newly selected workflow
  useEffect(() => {
    setEntityKey(workflow.entities[0]);
  }, [workflowType]);

  const targetUrl = isCustom ? customUrl.trim() : workflow.buildUrl(entityKey);
  const effectiveEntity = isCustom ? customEntity.trim() : entityKey;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (isCustom && (!customEntity.trim() || !customUrl.trim())) {
      setError("Entity name and target URL are required for a custom source.");
      return;
    }
    try {
      const task = await createTask.mutateAsync({
        objective: objective.trim() || `Track ${workflow.label.toLowerCase()} for ${effectiveEntity}`,
        workflow_type: workflowType,
        entity_key: effectiveEntity,
        target_url: targetUrl,
        review_required: reviewRequired,
      });
      const run = await startRun.mutateAsync(task.id);
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task.");
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-6">
      <h1 className="text-2xl font-bold">New task</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Define what to monitor. The agent plans real browser steps, executes them, and reports back with evidence.
      </p>

      <Card className="mt-4 shadow-sm">
        <CardHeader className="px-6 py-3">
          <CardTitle>Task objective</CardTitle>
        </CardHeader>
        <CardContent className="px-6 py-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">Workflow type</label>
                <select
                  value={workflowType}
                  onChange={(e) => setWorkflowType(e.target.value as WorkflowType)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {WORKFLOWS.map((w) => (
                    <option key={w.value} value={w.value}>{w.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Entity</label>
                <select
                  value={entityKey}
                  onChange={(e) => setEntityKey(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {workflow.entities.map((entity) => (
                    <option key={entity} value={entity}>{entity}</option>
                  ))}
                  <option value={CUSTOM_ENTITY}>Custom source…</option>
                </select>
              </div>
            </div>

            {isCustom ? (
              <div className="grid gap-4 rounded-md border border-dashed border-input bg-muted/40 p-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">Custom entity name</label>
                  <input
                    value={customEntity}
                    onChange={(e) => setCustomEntity(e.target.value)}
                    placeholder="e.g. Manali"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Target URL</label>
                  <input
                    value={customUrl}
                    onChange={(e) => setCustomUrl(e.target.value)}
                    placeholder="https://approved-source.example/page"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs"
                  />
                </div>
                <p className="text-xs text-muted-foreground sm:col-span-2">
                  Only domains in the source policy allowlist are navigable. An
                  unapproved domain fails visibly as{" "}
                  <code className="font-mono">POLICY_RESTRICTED</code>.
                </p>
              </div>
            ) : (
              <div>
                <label className="mb-1 block text-sm font-medium">Target URL</label>
                <div className="w-full rounded-md border border-input bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
                  {targetUrl}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Derived automatically from the workflow and entity above.
                </p>
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium">Objective (optional)</label>
              <input
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Auto-filled if left blank"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>

            <div className="flex items-center justify-between gap-4 pt-1">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={reviewRequired}
                  onChange={(e) => setReviewRequired(e.target.checked)}
                  className="h-4 w-4"
                />
                Require approval before browsing
              </label>

              <Button
                type="submit"
                disabled={createTask.isPending || startRun.isPending}
                className="px-6"
              >
                {createTask.isPending || startRun.isPending ? "Creating" : "Create task and start run"}
              </Button>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
