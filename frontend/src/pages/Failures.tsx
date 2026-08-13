import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useFailures } from "../api/queries";

export default function Failures() {
  const { data: failures } = useFailures();

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Failures and recovery</h1>
      <div className="mt-4 space-y-3">
        {(failures ?? []).map((f) => (
          <Card key={f.id}>
            <CardContent className="py-4">
              <div className="flex items-center gap-2">
                <Badge variant="destructive">{f.error_type}</Badge>
                <Badge variant={f.recovery_state === "recovered" ? "success" : "outline"}>{f.recovery_state}</Badge>
                <Link to={`/runs/${f.run_id}`} className="ml-auto font-mono text-xs text-primary">
                  Run {f.run_id.slice(0, 8)}
                </Link>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{f.message}</p>
              {f.recovery_attempts.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-border pt-2 text-xs">
                  {f.recovery_attempts.map((a, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="font-mono">{a.candidate_selector}</span>
                      <Badge variant={a.result === "validated" ? "success" : "outline"}>{a.result}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {(failures ?? []).length === 0 && (
          <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">No failures recorded</CardContent></Card>
        )}
      </div>
    </div>
  );
}
