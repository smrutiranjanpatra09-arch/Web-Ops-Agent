import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useModelCalls } from "../api/queries";

const NODES = ["planner", "completion", "recovery", "chat", "extraction_fallback"];
const PROVIDERS = ["gemini", "ollama"];

export default function AiActivity() {
  const [node, setNode] = useState<string>("");
  const [provider, setProvider] = useState<string>("");
  const { data: calls } = useModelCalls({ node: node || undefined, provider: provider || undefined });

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">AI Activity</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Every LLM call made by this platform, automatically logged - which node called it, what model,
        whether it succeeded or fell back to deterministic logic, and what it was grounded in.
      </p>

      <div className="mt-4 flex gap-2">
        <select
          value={node}
          onChange={(e) => setNode(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
        >
          <option value="">All nodes</option>
          {NODES.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
        >
          <option value="">All providers</option>
          {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      <div className="mt-4 space-y-2">
        {(calls ?? []).map((c) => (
          <Card key={c.id}>
            <CardContent className="py-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-medium">{c.node}</span>
                <span className="text-xs text-muted-foreground">{c.model_name}</span>
                {c.success ? (
                  <Badge variant="success">succeeded</Badge>
                ) : c.fallback_triggered ? (
                  <Badge variant="warning">fell back</Badge>
                ) : (
                  <Badge variant="destructive">failed</Badge>
                )}
                <span className="text-xs text-muted-foreground">{c.latency_ms}ms</span>
                {c.run_id && (
                  <Link to={`/runs/${c.run_id}`} className="ml-auto font-mono text-xs text-primary">
                    Run {c.run_id.slice(0, 8)}
                  </Link>
                )}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{c.purpose}</p>
              {c.output_summary && <p className="mt-1 truncate text-xs text-muted-foreground">{c.output_summary}</p>}
              {c.error_message && <p className="mt-1 truncate text-xs text-destructive">{c.error_message}</p>}
            </CardContent>
          </Card>
        ))}
        {(calls ?? []).length === 0 && (
          <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">No AI model calls yet</CardContent></Card>
        )}
      </div>
    </div>
  );
}
