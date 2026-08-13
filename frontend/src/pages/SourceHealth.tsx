import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useSources } from "../api/queries";

const HEALTH_VARIANT = {
  HEALTHY: "success",
  DEGRADED: "warning",
  UNSTABLE: "warning",
  FAILED: "destructive",
  REVIEW_REQUIRED: "destructive",
} as const;

export default function SourceHealth() {
  const { data: sources } = useSources();

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Source health</h1>
      <Card className="mt-4">
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-2">Domain</th>
                <th className="px-2 py-2">Category</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2 text-right">Runs</th>
                <th className="px-2 py-2 text-right">Failures</th>
                <th className="px-4 py-2 text-right">Consecutive</th>
              </tr>
            </thead>
            <tbody>
              {(sources ?? []).map((s) => (
                <tr key={s.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 font-mono text-xs">{s.domain}</td>
                  <td className="px-2 py-2 text-xs text-muted-foreground">{s.category}</td>
                  <td className="px-2 py-2"><Badge variant={HEALTH_VARIANT[s.health_state]}>{s.health_state}</Badge></td>
                  <td className="px-2 py-2 text-right">{s.total_runs}</td>
                  <td className="px-2 py-2 text-right">{s.total_failures}</td>
                  <td className="px-4 py-2 text-right">{s.consecutive_failures}</td>
                </tr>
              ))}
              {(sources ?? []).length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-sm text-muted-foreground">No sources registered</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
