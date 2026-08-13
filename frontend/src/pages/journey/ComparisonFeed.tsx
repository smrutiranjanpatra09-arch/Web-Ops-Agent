import { useState } from "react";
import { GitCompare } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../../components/ui/Card";
import { Badge, significanceVariant } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { useChangeFeed } from "../../api/queries";

const WORKFLOWS = ["hotel_pricing_watch", "campaign_page_monitoring", "competitor_offer_tracking", "partner_update_review", "travel_trend_scanning"];
const SIGNIFICANCE = ["insignificant", "minor", "notable", "significant"];

export default function ComparisonFeed() {
  const [workflow, setWorkflow] = useState("");
  const [significance, setSignificance] = useState("");
  const { data: changes } = useChangeFeed({
    workflow_type: workflow || undefined,
    significance: significance || undefined,
  });

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Comparison</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        A live feed of detected changes across every run - deterministic diffs, never LLM-computed.
      </p>

      <div className="mt-4 flex gap-2">
        <select value={workflow} onChange={(e) => setWorkflow(e.target.value)} className="rounded-md border border-border bg-background px-3 py-1.5 text-sm">
          <option value="">All workflows</option>
          {WORKFLOWS.map((w) => <option key={w} value={w}>{w}</option>)}
        </select>
        <select value={significance} onChange={(e) => setSignificance(e.target.value)} className="rounded-md border border-border bg-background px-3 py-1.5 text-sm">
          <option value="">All significance</option>
          {SIGNIFICANCE.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="mt-4 space-y-2">
        {(changes ?? []).map((c) => (
          <Card key={c.id}>
            <CardContent className="py-3">
              <div className="flex items-center gap-2">
                <span className="font-medium">{c.entity_name}</span>
                <span className="font-mono text-xs text-muted-foreground">{c.change_type}</span>
                <Badge variant={significanceVariant(c.significance)}>{c.significance}</Badge>
                <Link to={`/runs/${c.run_id}`} className="ml-auto font-mono text-xs text-primary">
                  Run {c.run_id.slice(0, 8)}
                </Link>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {c.previous_value ?? "-"} to {c.current_value ?? "-"}
                {c.delta_pct != null ? ` (${c.delta_pct}%)` : ""}
              </p>
            </CardContent>
          </Card>
        ))}
        {(changes ?? []).length === 0 && (
          <EmptyState
            icon={GitCompare}
            title="No comparisons yet"
            description="Changes appear here once a run has both a current and a prior snapshot to diff against."
          />
        )}
      </div>
    </div>
  );
}
