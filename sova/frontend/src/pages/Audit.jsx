import { useEffect, useState } from "react";
import { useApp } from "../store.js";
import client from "../api/client.js";

export default function Audit() {
  const { project } = useApp();
  const [logs, setLogs] = useState([]);
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (project) client.get(`/audit/project/${project.id}`).then((r) => setLogs(r.data));
  }, [project]);

  const verifyChain = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await client.get("/audit/verify");
      setVerifyResult(res.data);
    } catch (e) {
      setVerifyResult({ status: "ERROR", detail: "Could not verify audit chain." });
    } finally {
      setVerifying(false);
    }
  };

  if (!project) return <div className="text-sova-subtext text-sm">Select a project from the Dashboard first.</div>;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-xl font-semibold">Audit Log</h1>
        <button onClick={verifyChain} disabled={verifying} className="btn btn-secondary text-xs">
          {verifying ? "Verifying…" : "🔗 Verify integrity"}
        </button>
      </div>
      <p className="text-sova-subtext text-sm mb-4">Project: <span className="font-mono">{project.name}</span></p>

      {verifyResult && (
        <div className={`card mb-4 ${verifyResult.status === "OK" ? "border-emerald-500/40" : "border-red-500/40"}`}>
          <div className={`text-sm font-medium ${verifyResult.status === "OK" ? "text-emerald-400" : "text-red-400"}`}>
            {verifyResult.status === "OK" ? "✓ Chain Integrity Verified" : `✕ ${verifyResult.status}`}
          </div>
          <div className="text-xs text-sova-subtext mt-1">{verifyResult.detail}</div>
        </div>
      )}

      <div className="card">
        <div className="space-y-1">
          {logs.map((l) => (
            <div key={l.id} className="flex justify-between text-xs font-mono border-b border-sova-border/50 py-1.5">
              <span className="text-sova-accent">{l.action}</span>
              <span className="text-sova-text truncate flex-1 mx-3">{l.detail}</span>
              <span className="text-sova-subtext shrink-0">{new Date(l.timestamp).toLocaleString()}</span>
            </div>
          ))}
          {logs.length === 0 && <div className="text-xs text-sova-subtext">No audit events yet.</div>}
        </div>
      </div>
    </div>
  );
}
