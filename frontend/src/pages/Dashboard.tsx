import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { useModelCalls, useReviews, useRuns, useSignals, useSources, useTasks } from "../api/queries";
import { runsPerDay, signalsBySeverity, summarizeAiActivity, workflowBreakdown } from "../lib/dashboardAggregations";
import { buildMonitoredDestinations, type DestinationSeverity } from "../lib/destinationSignals";
import type { WorkflowType } from "../api/types";

// Chart palette follows the dataviz skill's reference instance: fixed
// categorical hue order (never cycled/reassigned by filters) plus the
// reserved status palette for state-like encodings (run/signal severity).
const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#4a3aa7"];
const STATUS = { good: "#0ca30c", warning: "#fab219", serious: "#ec835a", critical: "#d03b3b" };
const RUN_STATE_COLORS: Record<string, string> = {
  COMPLETED: STATUS.good,
  FAILED: STATUS.critical,
  CANCELLED: "#898781",
  IN_PROGRESS: CATEGORICAL[0],
};
const SEVERITY_COLORS: Record<string, string> = {
  low: STATUS.good,
  medium: STATUS.warning,
  high: STATUS.serious,
  critical: STATUS.critical,
};
const PIN_COLORS: Record<DestinationSeverity, string> = {
  none: STATUS.good,
  notable: STATUS.warning,
  significant: STATUS.critical,
};

function pinIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:14px;height:14px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 0 0 1px rgba(0,0,0,0.25)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </CardContent>
    </Card>
  );
}

function StatLink({ label, value, to }: { label: string; value: number | string; to: string }) {
  return (
    <Link to={to}>
      <Card className="transition-colors hover:border-primary">
        <CardContent className="py-4">
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </CardContent>
      </Card>
    </Link>
  );
}

function RunsPerDayChart({ data }: { data: ReturnType<typeof runsPerDay> }) {
  return (
    <Card>
      <CardHeader><CardTitle>Runs per day (last 14 days)</CardTitle></CardHeader>
      <CardContent>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barSize={14}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={1} stroke="hsl(var(--muted-foreground))" />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" width={28} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 6 }}
                formatter={(value, name) => [value, String(name).replace("_", " ")]}
              />
              <Bar dataKey="COMPLETED" stackId="s" fill={RUN_STATE_COLORS.COMPLETED} radius={[0, 0, 0, 0]} />
              <Bar dataKey="IN_PROGRESS" stackId="s" fill={RUN_STATE_COLORS.IN_PROGRESS} />
              <Bar dataKey="FAILED" stackId="s" fill={RUN_STATE_COLORS.FAILED} />
              <Bar dataKey="CANCELLED" stackId="s" fill={RUN_STATE_COLORS.CANCELLED} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {Object.entries(RUN_STATE_COLORS).map(([state, color]) => (
            <span key={state} className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: color }} />
              {state.replace("_", " ")}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SignalsBySeverityChart({ data }: { data: ReturnType<typeof signalsBySeverity> }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  return (
    <Card>
      <CardHeader><CardTitle>Signals by severity</CardTitle></CardHeader>
      <CardContent>
        {total === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">No signals yet</div>
        ) : (
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="count" nameKey="severity" innerRadius={36} outerRadius={56} paddingAngle={2}>
                  {data.map((d) => (
                    <Cell key={d.severity} fill={SEVERITY_COLORS[d.severity]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {data.map((d) => (
            <span key={d.severity} className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: SEVERITY_COLORS[d.severity] }} />
              {d.severity} ({d.count})
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function WorkflowBreakdownChart({ data }: { data: ReturnType<typeof workflowBreakdown> }) {
  return (
    <Card>
      <CardHeader><CardTitle>Workflow breakdown</CardTitle></CardHeader>
      <CardContent>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis type="category" dataKey="label" width={110} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {data.map((d, i) => (
                  <Cell key={d.workflow_type} fill={CATEGORICAL[i % CATEGORICAL.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function AiActivityCard({ summary }: { summary: ReturnType<typeof summarizeAiActivity> }) {
  return (
    <Card>
      <CardHeader><CardTitle>AI activity today</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-2xl font-bold">{summary.totalCalls}</div>
            <div className="text-xs text-muted-foreground">Calls made</div>
          </div>
          <div>
            <div className="text-2xl font-bold">{summary.avgLatencyMs != null ? `${summary.avgLatencyMs}ms` : "—"}</div>
            <div className="text-xs text-muted-foreground">Avg latency</div>
          </div>
        </div>
        <div className="mt-4">
          <div className="flex h-2 overflow-hidden rounded-full bg-secondary">
            <div style={{ width: `${summary.geminiPct}%`, background: CATEGORICAL[0] }} />
            <div style={{ width: `${100 - summary.geminiPct}%`, background: CATEGORICAL[1] }} />
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: CATEGORICAL[0] }} />
              Gemini {summary.geminiPct}%
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: CATEGORICAL[1] }} />
              Fallback {100 - summary.geminiPct}%
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MonitoredDestinationsMap({
  destinations,
  onSelect,
}: {
  destinations: ReturnType<typeof buildMonitoredDestinations>;
  onSelect: (name: string) => void;
}) {
  if (destinations.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Monitored destinations</CardTitle></CardHeader>
        <CardContent className="flex h-64 items-center justify-center text-sm text-muted-foreground">
          No monitored destinations resolved yet
        </CardContent>
      </Card>
    );
  }

  const center: [number, number] = [destinations[0].coords.lat, destinations[0].coords.lng];

  return (
    <Card>
      <CardHeader><CardTitle>Monitored destinations</CardTitle></CardHeader>
      <CardContent>
        <div className="h-72 overflow-hidden rounded-md">
          <MapContainer center={center} zoom={5} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {destinations.map((d) => (
              <Marker
                key={d.name}
                position={[d.coords.lat, d.coords.lng]}
                icon={pinIcon(PIN_COLORS[d.severity])}
                eventHandlers={{ click: () => onSelect(d.name) }}
              >
                <Popup>
                  <div className="text-sm font-medium">{d.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {d.severity === "none" ? "No open signals" : `${d.openSignalCount} open signal(s) - ${d.severity}`}
                  </div>
                  <Link to={`/signals?destination=${encodeURIComponent(d.name)}`} className="text-xs text-primary underline">
                    View signals &rarr;
                  </Link>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: PIN_COLORS.none }} />No open signals</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: PIN_COLORS.notable }} />Notable</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: PIN_COLORS.significant }} />Significant</span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: runs } = useRuns();
  const { data: reviews } = useReviews("pending");
  const { data: signals } = useSignals();
  const { data: sources } = useSources();
  const { data: tasks } = useTasks();
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);
  const { data: modelCalls } = useModelCalls({ since: today.toISOString() });
  const navigate = useNavigate();
  const goToDestinationSignals = (name: string) => navigate(`/signals?destination=${encodeURIComponent(name)}`);

  const completed = (runs ?? []).filter((r) => r.state === "COMPLETED").length;
  const failed = (runs ?? []).filter((r) => r.state === "FAILED").length;
  const inProgress = (runs ?? []).filter((r) => !["COMPLETED", "FAILED", "CANCELLED"].includes(r.state)).length;
  const totalSources = (sources ?? []).length;
  const unhealthySources = (sources ?? []).filter((s) => s.health_state !== "HEALTHY").length;

  const runsPerDayData = useMemo(() => runsPerDay(runs ?? []), [runs]);
  const severityData = useMemo(() => signalsBySeverity(signals ?? []), [signals]);
  const taskWorkflowByTaskId = useMemo(() => {
    const map = new Map<string, WorkflowType>();
    for (const t of tasks ?? []) map.set(t.id, t.workflow_type);
    return map;
  }, [tasks]);
  const workflowData = useMemo(() => workflowBreakdown(runs ?? [], taskWorkflowByTaskId), [runs, taskWorkflowByTaskId]);
  const aiSummary = useMemo(() => summarizeAiActivity(modelCalls ?? []), [modelCalls]);
  const monitoredDestinations = useMemo(
    () => buildMonitoredDestinations(tasks ?? [], runs ?? [], signals ?? []),
    [tasks, runs, signals]
  );

  return (
    <div className="mx-auto max-w-5xl p-8">
      <h1 className="text-xl font-bold">Operations dashboard</h1>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Runs in progress" value={inProgress} />
        <Stat label="Completed" value={completed} />
        <Stat label="Failed" value={failed} />
        <StatLink label="Pending reviews" value={(reviews ?? []).length} to="/reviews" />
        <Stat label="Signals" value={(signals ?? []).length} />
        <StatLink label="Unhealthy / total sources" value={`${unhealthySources} / ${totalSources}`} to="/sources" />
      </div>
      <div className="mt-2 text-right">
        <Link to="/system" className="text-xs text-muted-foreground underline hover:text-foreground">
          View infrastructure health &rarr;
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RunsPerDayChart data={runsPerDayData} />
        <SignalsBySeverityChart data={severityData} />
        <WorkflowBreakdownChart data={workflowData} />
        <AiActivityCard summary={aiSummary} />
      </div>

      <div className="mt-4">
        <MonitoredDestinationsMap destinations={monitoredDestinations} onSelect={goToDestinationSignals} />
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle>Recent runs</CardTitle></CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <tbody>
              {(runs ?? []).slice(0, 8).map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 font-mono text-xs">{r.id.slice(0, 8)}</td>
                  <td className="px-2 py-2 text-xs text-muted-foreground">{r.state}</td>
                  <td className="px-4 py-2 text-right text-xs text-muted-foreground">
                    {new Date(r.updated_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
