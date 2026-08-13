import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useDecideReview, useReviews } from "../api/queries";
import { getStoredUser } from "../lib/auth";

const ACTIONS = ["approve", "reject", "correct", "rerun", "request_schema_change"];
const REVIEWER_ROLES = ["reviewer", "operations_owner", "administrator"];

export default function Reviews() {
  const { data: reviews } = useReviews("pending");
  const decide = useDecideReview();
  const [reasonById, setReasonById] = useState<Record<string, string>>({});
  const user = getStoredUser();
  const canDecide = !!user && REVIEWER_ROLES.includes(user.role);

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Human review</h1>
      <div className="mt-4 space-y-3">
        {(reviews ?? []).map((r) => (
          <Card key={r.id}>
            <CardContent className="space-y-3 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <Link to={`/runs/${r.run_id}`} className="font-mono text-xs text-primary">
                    Run {r.run_id.slice(0, 8)}
                  </Link>
                  <Badge variant="warning" className="ml-2">{r.trigger_reason}</Badge>
                </div>
              </div>
              {canDecide ? (
                <>
                  <input
                    value={reasonById[r.id] ?? ""}
                    onChange={(e) => setReasonById((prev) => ({ ...prev, [r.id]: e.target.value }))}
                    placeholder="Reason (optional)"
                    className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  />
                  <div className="flex gap-2">
                    {ACTIONS.map((action) => (
                      <Button
                        key={action}
                        variant={action === "approve" ? "default" : action === "reject" ? "destructive" : "outline"}
                        disabled={decide.isPending}
                        onClick={() => decide.mutate({ reviewId: r.id, action, reason: reasonById[r.id] })}
                      >
                        {action.replace(/_/g, " ")}
                      </Button>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Only reviewers, operations owners, or administrators can decide reviews.
                </p>
              )}
            </CardContent>
          </Card>
        ))}
        {(reviews ?? []).length === 0 && (
          <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">No pending reviews</CardContent></Card>
        )}
      </div>
    </div>
  );
}
