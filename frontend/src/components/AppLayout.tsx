import { NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, Bot, Calendar, Compass, Database, History, LayoutGrid, LogOut, MessageCircle, Radio, ShieldAlert } from "lucide-react";
import { cn } from "../lib/utils";
import { JOURNEY_STAGES, stageForRunState } from "../lib/journey";
import { useHealth, useModelCalls, useRun } from "../api/queries";
import { clearSession, getStoredUser } from "../lib/auth";
import AssistantWidget from "./AssistantWidget";

// primary journey stepper: task -> plan -> run -> data -> insight -> action.
// Highlights the stage that matches the run currently being viewed (by its
// real backend state), not just by URL path - several stages share the
// /runs/:id path, so path-matching alone would light up all of them at once.
function JourneyRail() {
  const location = useLocation();
  const { runId } = useParams<{ runId: string }>();
  const { data: run } = useRun(runId);

  const stageByPath = JOURNEY_STAGES.find((s) => s.path === location.pathname)?.key;
  const activeStageKey = stageByPath ?? (runId ? stageForRunState(run?.state)?.key : undefined);

  return (
    <div className="space-y-0.5">
      <div className="px-3 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        Operations Journey
      </div>
      {JOURNEY_STAGES.map((stage, i) => {
        const active = stage.key === activeStageKey;
        return (
          <NavLink
            key={stage.key}
            to={stage.path}
            className={cn(
              "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              active ? "bg-primary text-primary-foreground" : "text-foreground/80 hover:bg-secondary"
            )}
          >
            <span
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                active ? "bg-primary-foreground text-primary" : "bg-muted text-muted-foreground"
              )}
            >
              {i + 1}
            </span>
            <span className="truncate">{stage.label}</span>
          </NavLink>
        );
      })}
    </div>
  );
}

const OPS_LINKS = [
  { to: "/dashboard", label: "Operations Dashboard", icon: LayoutGrid },
  { to: "/ai-activity", label: "AI Activity", icon: Bot },
  { to: "/assistant", label: "Ask MMT Assistant", icon: MessageCircle },
  { to: "/sources", label: "Source Health", icon: Radio },
  { to: "/schedules", label: "Scheduling", icon: Calendar },
  { to: "/failures", label: "Failures & Recovery", icon: AlertTriangle },
  { to: "/runs/history", label: "Run History", icon: History },
  { to: "/system", label: "System Health", icon: ShieldAlert },
];

const ADMIN_LINKS = [
  { to: "/data-management", label: "Data Management", icon: Database },
];

// small always-visible counter so LLM usage is obvious without opening a
// dedicated page - Phase 29's fix for "IDK WHERE LLM IS GETTING USED".
function AiActivityCounter() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const { data: calls } = useModelCalls({ since: today.toISOString() });

  if (!calls || calls.length === 0) return null;
  const geminiCount = calls.filter((c) => c.success && c.provider === "gemini").length;
  const geminiPct = Math.round((geminiCount / calls.length) * 100);

  return (
    <NavLink
      to="/ai-activity"
      className="mx-2 mb-1 flex items-center gap-2 rounded-md bg-secondary/50 px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary"
    >
      <Bot className="h-3.5 w-3.5" />
      <span>AI Calls Today: {calls.length} ({geminiPct}% Gemini / {100 - geminiPct}% fallback)</span>
    </NavLink>
  );
}

function OpsRail() {
  const user = getStoredUser();
  const isAdmin = user?.role === "administrator";
  const links = isAdmin ? [...OPS_LINKS, ...ADMIN_LINKS] : OPS_LINKS;

  return (
    <div className="space-y-0.5">
      <div className="px-3 pb-2 pt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        Operations
      </div>
      <AiActivityCounter />
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              isActive ? "bg-secondary text-secondary-foreground font-medium" : "text-foreground/70 hover:bg-secondary"
            )
          }
        >
          <Icon className="h-4 w-4" />
          <span className="truncate">{label}</span>
        </NavLink>
      ))}
    </div>
  );
}

function HealthBadge() {
  const { data, isError } = useHealth();
  const ok = data?.status === "ok";
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-xs">
      <span className={cn("h-2 w-2 rounded-full", ok ? "bg-success" : "bg-destructive")} />
      <span className="text-muted-foreground">
        {isError ? "Unreachable" : ok ? "All systems healthy" : "Degraded"}
      </span>
    </div>
  );
}

function UserBadge() {
  const navigate = useNavigate();
  const user = getStoredUser();

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  if (!user) return null;

  return (
    <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-2 text-xs">
      <div className="truncate">
        <div className="truncate font-medium">{user.display_name}</div>
        <div className="truncate text-muted-foreground">{user.role.replace(/_/g, " ")}</div>
      </div>
      <button
        onClick={handleLogout}
        className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
      >
        <LogOut className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-card">
        <div className="flex items-center gap-2 border-b border-border px-4 py-4">
          <Compass className="h-5 w-5 text-primary" />
          <div className="text-sm font-bold leading-tight">
            MakeMyTrip
            <div className="text-[11px] font-normal text-muted-foreground">Web Operations Agent</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <JourneyRail />
          <OpsRail />
        </nav>
        <div className="border-t border-border">
          <HealthBadge />
          <UserBadge />
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-background">
        <Outlet />
      </main>
      <AssistantWidget />
    </div>
  );
}
