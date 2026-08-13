import { Link, useSearchParams } from "react-router-dom";
import { useMemo } from "react";
import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useRuns, useSignals, useTasks } from "../api/queries";

export default function Signals() {
  const { data: signals } = useSignals();
  const { data: runs } = useRuns();
  const { data: tasks } = useTasks();
  const [searchParams, setSearchParams] = useSearchParams();
  const destinationFilter = searchParams.get("destination");

  // Maps a signal back to its run's task entity_key so the "Monitored
  // Destinations" map on the dashboard can deep-link into this feed
  // filtered to a single destination (signals don't carry entity_key
  // directly - they're joined through run_id -> task_id -> entity_key).
  const entityByRunId = useMemo(() => {
    const taskEntityById = new Map((tasks ?? []).map((t) => [t.id, t.entity_key]));
    const map = new Map<string, string>();
    for (const r of runs ?? []) {
      const entity = taskEntityById.get(r.task_id);
      if (entity) map.set(r.id, entity);
    }
    return map;
  }, [runs, tasks]);

  const visibleSignals = (signals ?? []).filter((s) => {
    if (!destinationFilter) return true;
    const entity = entityByRunId.get(s.run_id);
    return entity?.toLowerCase().includes(destinationFilter.toLowerCase());
  });

  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">Signals</h1>
        {destinationFilter && (
          <button
            onClick={() => setSearchParams({})}
            className="rounded-full bg-secondary px-2.5 py-1 text-xs text-secondary-foreground hover:bg-secondary/70"
          >
            Destination: {destinationFilter} &times;
          </button>
        )}
      </div>
      <div className="mt-4 space-y-3">
        {visibleSignals.map((s) => (
          <Card key={s.id}>
            <CardContent className="py-4">
              <div className="flex items-center gap-2">
                <Badge variant={s.severity === "high" || s.severity === "critical" ? "destructive" : "default"}>
                  {s.severity}
                </Badge>
                <span className="font-medium">{s.signal_type}</span>
                {s.owner && <span className="text-xs text-muted-foreground">{s.owner}</span>}
                <Link to={`/runs/${s.run_id}`} className="ml-auto font-mono text-xs text-primary">
                  Run {s.run_id.slice(0, 8)}
                </Link>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{s.business_impact ?? s.observations}</p>
            </CardContent>
          </Card>
        ))}
        {visibleSignals.length === 0 && (
          <Card>
            <CardContent className="py-6 text-center text-sm text-muted-foreground">
              {destinationFilter ? `No signals for ${destinationFilter}` : "No signals yet"}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
