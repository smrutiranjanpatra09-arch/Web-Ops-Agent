import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/Card";
import { Badge, runStateVariant } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useArchiveRun, useFilteredRuns } from "../api/queries";
import { getStoredUser } from "../lib/auth";
import type { RunState } from "../api/types";

const RUN_STATES: RunState[] = [
  "CREATED", "VALIDATING", "PLANNING", "PLAN_READY", "AWAITING_APPROVAL", "APPROVED", "QUEUED",
  "BROWSER_STARTING", "BROWSING", "EXTRACTION", "VALIDATING_DATA", "SNAPSHOTTING", "COMPARING",
  "REASONING", "REVIEW_REQUIRED", "COMPLETING", "COMPLETED",
  "RECOVERY", "RERUN_REQUESTED", "FAILED", "CANCELLED",
];

const WORKFLOW_TYPES = [
  "hotel_pricing_watch", "competitor_offer_tracking", "campaign_page_monitoring",
  "partner_update_review", "travel_trend_scanning",
];

const PAGE_SIZE = 25;
const ARCHIVE_ROLES = ["operations_owner", "administrator"];

export default function Runs() {
  const [state, setState] = useState("");
  const [workflowType, setWorkflowType] = useState("");
  const [since, setSince] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [page, setPage] = useState(0);

  const user = getStoredUser();
  const canArchive = !!user && ARCHIVE_ROLES.includes(user.role);

  const { data: runs, isFetching } = useFilteredRuns({
    state: state || undefined,
    workflow_type: workflowType || undefined,
    since: since ? new Date(since).toISOString() : undefined,
    include_archived: includeArchived,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });
  const archive = useArchiveRun();

  function resetAndFilter(fn: () => void) {
    setPage(0);
    fn();
  }

  return (
    <div className="mx-auto max-w-5xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Run History</h1>
      </div>

      <Card className="mt-4">
        <CardContent className="flex flex-wrap items-end gap-3 py-4">
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            State
            <select
              className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm"
              value={state}
              onChange={(e) => resetAndFilter(() => setState(e.target.value))}
            >
              <option value="">All states</option>
              {RUN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Workflow type
            <select
              className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm"
              value={workflowType}
              onChange={(e) => resetAndFilter(() => setWorkflowType(e.target.value))}
            >
              <option value="">All workflows</option>
              {WORKFLOW_TYPES.map((w) => <option key={w} value={w}>{w}</option>)}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Since
            <input
              type="date"
              className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm"
              value={since}
              onChange={(e) => resetAndFilter(() => setSince(e.target.value))}
            />
          </label>

          <label className="flex items-center gap-2 pb-1.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => resetAndFilter(() => setIncludeArchived(e.target.checked))}
            />
            Include archived
          </label>

          {(state || workflowType || since || includeArchived) && (
            <Button
              variant="outline"
              className="mb-0"
              onClick={() => resetAndFilter(() => {
                setState(""); setWorkflowType(""); setSince(""); setIncludeArchived(false);
              })}
            >
              Clear filters
            </Button>
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-2">Run</th>
                <th className="px-2 py-2">Task</th>
                <th className="px-2 py-2">State</th>
                <th className="px-4 py-2 text-right">Updated</th>
                {canArchive && <th className="px-4 py-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {(runs ?? []).map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0 hover:bg-secondary/50">
                  <td className="px-4 py-2">
                    <Link to={`/runs/${r.id}`} className="font-mono text-xs text-primary">{r.id.slice(0, 8)}</Link>
                  </td>
                  <td className="px-2 py-2 font-mono text-xs text-muted-foreground">{r.task_id.slice(0, 8)}</td>
                  <td className="px-2 py-2">
                    <Badge variant={runStateVariant(r.state)}>{r.state}</Badge>
                    {r.archived && <Badge variant="outline" className="ml-2">archived</Badge>}
                  </td>
                  <td className="px-4 py-2 text-right text-xs text-muted-foreground">
                    {new Date(r.updated_at).toLocaleString()}
                  </td>
                  {canArchive && (
                    <td className="px-4 py-2 text-right">
                      {!r.archived && (
                        <Button
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          disabled={archive.isPending}
                          onClick={() => archive.mutate(r.id)}
                        >
                          Archive
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {(runs ?? []).length === 0 && (
                <tr>
                  <td colSpan={canArchive ? 5 : 4} className="px-4 py-6 text-center text-sm text-muted-foreground">
                    No runs match these filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="mt-4 flex items-center justify-between">
        <Button variant="outline" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
          Previous
        </Button>
        <span className="text-xs text-muted-foreground">Page {page + 1}</span>
        <Button
          variant="outline"
          disabled={isFetching || (runs ?? []).length < PAGE_SIZE}
          onClick={() => setPage((p) => p + 1)}
        >
          Load more
        </Button>
      </div>
    </div>
  );
}
