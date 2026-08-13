import { useState } from "react";
import { Database } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { useRunResults, useRunsByStates } from "../../api/queries";

export default function ExtractedDataQueue() {
  const { data: activeRuns } = useRunsByStates(["EXTRACTION", "VALIDATING_DATA", "SNAPSHOTTING"]);
  const { data: recentCompleted } = useRunsByStates(["COMPLETED", "REVIEW_REQUIRED"]);
  const candidates = [...(activeRuns ?? []), ...(recentCompleted ?? [])];
  const [selectedRunId, setSelectedRunId] = useState<string>("");

  const currentRunId = selectedRunId || candidates[0]?.id;
  const { data: results } = useRunResults(currentRunId);

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Extracted Data</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Fields pulled from the most recent extraction, with confidence and validation flags.
      </p>

      {candidates.length > 0 && (
        <select
          value={currentRunId}
          onChange={(e) => setSelectedRunId(e.target.value)}
          className="mt-4 rounded-md border border-border bg-background px-3 py-1.5 text-sm"
        >
          {candidates.map((r) => (
            <option key={r.id} value={r.id}>Run {r.id.slice(0, 8)} - {r.state}</option>
          ))}
        </select>
      )}

      <div className="mt-4">
        {candidates.length === 0 && (
          <EmptyState
            icon={Database}
            title="No extracted data yet"
            description="This view shows the fields a run pulled from the target page once it reaches extraction. Nothing has extracted anything yet in this session."
          />
        )}
        {candidates.length > 0 && (results?.snapshots.length ?? 0) === 0 && (
          <EmptyState icon={Database} title="No fields extracted for this run" description="Extraction may still be in progress." />
        )}
        {(results?.snapshots ?? []).length > 0 && (
          <Card>
            <CardHeader><CardTitle>Fields <Link to={`/runs/${currentRunId}`} className="ml-2 font-mono text-xs text-primary">Run {currentRunId?.slice(0, 8)}</Link></CardTitle></CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <tbody>
                  {(results?.snapshots ?? []).map((snap) => (
                    <tr key={snap.id} className="border-b border-border last:border-0">
                      <td className="px-4 py-2 font-medium">{snap.entity_key}</td>
                      <td className="px-4 py-2 text-xs text-muted-foreground">
                        {Object.entries(snap.fields).map(([k, v]) => `${k}=${v}`).join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
