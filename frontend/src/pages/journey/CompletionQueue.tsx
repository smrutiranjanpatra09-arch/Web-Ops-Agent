import { CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { downloadFile } from "../../api/client";
import { Card, CardContent } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { useRunResults, useRunsByStates } from "../../api/queries";

function CompletionRow({ runId }: { runId: string }) {
  const { data: results } = useRunResults(runId);
  const [downloading, setDownloading] = useState(false);

  async function handleDownloadReport() {
    setDownloading(true);
    try {
      await downloadFile(`/api/runs/${runId}/report.pdf`, `run-${runId}-report.pdf`);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card>
      <CardContent className="py-3">
        <div className="flex items-center justify-between gap-2">
          <Link to={`/runs/${runId}`} className="font-mono text-sm text-primary">Run {runId.slice(0, 8)}</Link>
          <Button variant="outline" onClick={handleDownloadReport} disabled={downloading}>
            {downloading ? "Preparing report" : "Download Report (PDF)"}
          </Button>
        </div>
        {results?.summary && (
          <p className="mt-1 text-sm text-muted-foreground">{results.summary.headline}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function CompletionQueue() {
  const { data: runs } = useRunsByStates(["COMPLETED"]);

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">Completion</h1>
      <p className="mt-1 text-sm text-muted-foreground">Runs that finished the full pipeline, with their generated summary.</p>
      <div className="mt-4 space-y-3">
        {(runs ?? []).map((r) => <CompletionRow key={r.id} runId={r.id} />)}
        {(runs ?? []).length === 0 && (
          <EmptyState icon={CheckCircle2} title="No completed runs yet" description="Runs appear here once they finish the full pipeline end to end." />
        )}
      </div>
    </div>
  );
}
