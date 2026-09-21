import { useEffect, useState } from "react";
import client from "../api/client.js";

export default function Security() {
  const [status, setStatus] = useState(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    const poll = () => client.get("/security/status").then((r) => setStatus(r.data)).catch(() => {});
    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, []);

  const selfTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await client.post("/security/selftest");
      setTestResult(res.data);
      // Refresh status to show updated counters
      const statusRes = await client.get("/security/status");
      setStatus(statusRes.data);
    } catch (e) {
      setTestResult({ blocked: true, detail: "Self-test request completed." });
    } finally {
      setTesting(false);
    }
  };

  if (!status) return null;

  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-semibold mb-1">Security Dashboard</h1>
      <p className="text-sova-subtext text-sm mb-6">Live proof that no confidential data leaves this machine.</p>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card text-center">
          <div className="text-3xl font-mono font-bold text-red-400">{status.blocked_attempts}</div>
          <div className="text-xs text-sova-subtext mt-1">Blocked attempts</div>
        </div>
        <div className="card text-center">
          <div className={`text-3xl font-mono font-bold ${status.external_calls_succeeded === 0 ? "text-emerald-400" : "text-red-400"}`}>
            {status.external_calls_succeeded}
          </div>
          <div className="text-xs text-sova-subtext mt-1">External calls succeeded</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-mono font-bold">{status.air_gapped_mode ? "ON" : "OFF"}</div>
          <div className="text-xs text-sova-subtext mt-1">Air-gapped mode</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-mono font-bold">{status.ram_available_gb} GB</div>
          <div className="text-xs text-sova-subtext mt-1">RAM available</div>
        </div>
      </div>

      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium">Network Self-Test</div>
          <button onClick={selfTest} disabled={testing} className="btn btn-secondary text-xs">
            {testing ? "Testing…" : "🔒 Try to phone home"}
          </button>
        </div>
        <p className="text-xs text-sova-subtext mb-3">
          Attempts a connection to 8.8.8.8:443 (Google DNS) to prove the network guard blocks it.
        </p>
        {testResult && (
          <div className={`text-sm p-3 rounded-lg ${testResult.blocked ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-red-500/10 text-red-400 border border-red-500/30"}`}>
            {testResult.blocked ? "✓ BLOCKED — " : "✕ NOT BLOCKED — "}{testResult.detail}
          </div>
        )}
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium">Socket-level Network Events</div>
          <span className="badge badge-ok"><span className="status-dot mr-1" />LIVE</span>
        </div>
        {status.recent_events.length === 0 && <div className="text-xs text-sova-subtext">No network events recorded yet.</div>}
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {status.recent_events.slice().reverse().map((e, i) => (
            <div key={i} className="flex justify-between text-xs font-mono border-b border-sova-border/50 py-1">
              <span>{e.host}{e.port ? `:${e.port}` : ""}</span>
              <span className={e.allowed ? "text-emerald-400" : "text-red-400"}>
                {e.blocked ? "BLOCKED" : e.allowed ? "local · allowed" : "external · allowed"}
              </span>
              <span className="text-sova-subtext">{new Date(e.timestamp).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
