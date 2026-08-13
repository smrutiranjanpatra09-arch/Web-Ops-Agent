import { useState } from "react";
import { ClipboardList } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { useApproveRun, usePlan, useRejectRun, useRunsByStates } from "../../api/queries";

function PlanRow({ runId, planId }: { runId: string; planId: string | null }) {
  const [expanded, setExpanded] = useState(false);
  const { data: plan } = usePlan(expanded ? planId : null);
  const approve = useApproveRun();
  const reject = useRejectRun();

  return (
    <Card>
      <CardContent className="py-3">
        <div className="flex items-center gap-2">
          <Link to={`/runs/${runId}`} className="font-mono text-sm text-primary">Run {runId.slice(0, 8)}</Link>
          <Button variant="outline" className="ml-auto h-7 px-2 text-xs" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Hide plan" : "View plan"}
          </Button>
          <Button className="h-7 px-2 text-xs" onClick={() => approve.mutate(runId)} disabled={approve.isPending}>
            Approve
          </Button>
          <Button
            variant="destructive"
            className="h-7 px-2 text-xs"
            onClick={() => reject.mutate({ runId })}
            disabled={reject.isPending}
          >
            Reject
          </Button>
        </div>
        {expanded && plan && (
          <div className="mt-3 space-y-2 border-t border-border pt-3 text-sm">
            <p><span className="font-medium">Objective:</span> {plan.objective}</p>
            {plan.risk_notes && <p className="text-muted-foreground"><span className="font-medium text-foreground">Risk notes:</span> {plan.risk_notes}</p>}
            <div>
              <p className="font-medium">Steps</p>
              <ol className="ml-4 list-decimal text-muted-foreground">
                {plan.steps.map((s) => (
                  <li key={s.step_order}>{s.action} - {s.target}{s.notes ? ` (${s.notes})` : ""}</li>
                ))}
              </ol>
            </div>
            {plan.stop_conditions.length > 0 && (
              <div>
                <p className="font-medium">Stop conditions</p>
                <ul className="ml-4 list-disc text-muted-foreground">
                  {plan.stop_conditions.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function PlanReviewQueue() {
  const { data: runs } = useRunsByStates(["AWAITING_APPROVAL"]);

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Plan Review</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Runs waiting for a plan to be approved before browsing starts.
      </p>
      <div className="mt-4 space-y-3">
        {(runs ?? []).map((r) => <PlanRow key={r.id} runId={r.id} planId={r.plan_id} />)}
        {(runs ?? []).length === 0 && (
          <EmptyState
            icon={ClipboardList}
            title="No plans currently awaiting review"
            description="Runs land here only when their task requires approval before browsing. Start a new task from Task Intake to see one move through the pipeline."
            action={<Link to="/tasks/new"><Button variant="outline">Go to Task Intake</Button></Link>}
          />
        )}
      </div>
    </div>
  );
}
