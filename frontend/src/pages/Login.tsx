import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { useLogin } from "../api/queries";
import { setSession } from "../lib/auth";

const DEMO_ACCOUNTS = [
  { email: "ops@makemytrip.demo", role: "Operations User" },
  { email: "growth@makemytrip.demo", role: "Growth User" },
  { email: "reviewer@makemytrip.demo", role: "Reviewer" },
  { email: "owner@makemytrip.demo", role: "Operations Owner" },
  { email: "admin@makemytrip.demo", role: "Administrator" },
];

const DEMO_PASSWORD = "#demoday26";

export default function Login() {
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showDemo, setShowDemo] = useState(false);

  function fillDemo(loginEmail: string) {
    setError(null);
    setEmail(loginEmail);
    setPassword(DEMO_PASSWORD);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await login.mutateAsync({ email: email.trim(), password });
      setSession(res.access_token, { user_id: res.user_id, display_name: res.display_name, role: res.role });
      navigate("/tasks/new");
    } catch {
      setError("Invalid email or password.");
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-3/5 flex-col justify-center overflow-hidden bg-mmt-blue px-16 text-white lg:flex">
        <svg
          className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 opacity-20"
          viewBox="0 0 200 200"
          fill="none"
        >
          <path
            d="M20 110 L80 90 L100 20 L110 90 L180 100 L110 115 L100 180 L88 115 Z"
            fill="white"
          />
        </svg>
        <svg
          className="pointer-events-none absolute -bottom-16 -left-10 h-72 w-72 opacity-10"
          viewBox="0 0 100 100"
          fill="none"
        >
          <circle cx="50" cy="50" r="45" stroke="white" strokeWidth="2" />
          <circle cx="50" cy="50" r="30" stroke="white" strokeWidth="2" />
        </svg>

        <div className="relative max-w-xl">
          <h1 className="text-4xl font-bold leading-tight">MakeMyTrip Web Operations Agent</h1>
          <p className="mt-4 text-lg text-white/80">
            Autonomous monitoring for hotel pricing, competitor offers, campaigns and partner updates.
            Every signal is backed by real browser evidence.
          </p>
          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/70">
            <span>Playwright verified</span>
            <span className="text-white/30">&middot;</span>
            <span>Evidence backed</span>
            <span className="text-white/30">&middot;</span>
            <span>Human governed</span>
            <span className="text-white/30">&middot;</span>
            <span>Self healing</span>
          </div>
        </div>
      </div>

      <div className="flex w-full flex-col items-center justify-center bg-background px-6 py-16 lg:w-2/5">
        <div className="w-full max-w-[380px] rounded-xl border border-border bg-card p-8 shadow-sm">
          <h2 className="text-2xl font-semibold">Sign in</h2>
          <p className="mt-1 text-sm text-muted-foreground">Access the operations console.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-mmt-blueLight"
                autoFocus
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-mmt-blueLight"
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button
              type="submit"
              disabled={login.isPending}
              className="w-full bg-mmt-blue text-white hover:bg-mmt-blueLight"
            >
              {login.isPending ? "Signing in" : "Sign in"}
            </Button>
          </form>

          <button
            type="button"
            onClick={() => setShowDemo((v) => !v)}
            className="mt-4 text-xs font-medium text-mmt-red hover:underline"
          >
            {showDemo ? "Hide demo accounts" : "Use a demo account"}
          </button>

          {showDemo && (
            <div className="mt-3">
              <p className="mb-2 text-xs text-muted-foreground">
                Click a role to autofill credentials, then sign in.
              </p>
              <div className="flex flex-wrap gap-2">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.email}
                    type="button"
                    disabled={login.isPending}
                    onClick={() => fillDemo(acc.email)}
                    className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-mmt-blueLight hover:text-mmt-blueLight"
                  >
                    {acc.role}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
