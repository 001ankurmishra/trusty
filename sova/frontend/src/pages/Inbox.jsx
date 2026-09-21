import { useState, useEffect } from "react";
import client from "../api/client.js";
import { useApp } from "../store.js";
import { Link } from "react-router-dom";

export default function Inbox() {
  const { user } = useApp();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedTask, setExpandedTask] = useState(null);
  const [comment, setComment] = useState("");
  const [password, setPassword] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchInbox = async () => {
    try {
      const res = await client.get("/tasks/inbox");
      setTasks(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load inbox.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInbox();
  }, []);

  const handleAction = async (taskId, decision) => {
    if (!password.trim()) {
      alert("Password is required for e-signature.");
      return;
    }
    setActionLoading(true);
    try {
      await client.post(`/tasks/${taskId}/${decision}`, { comment, password });
      setComment("");
      setPassword("");
      setExpandedTask(null);
      fetchInbox(); // Refresh list
    } catch (e) {
      alert(e?.response?.data?.detail || "Action failed.");
    } finally {
      setActionLoading(false);
    }
  };

  if (user?.role !== "REVIEWER" && user?.role !== "ADMIN") {
    return (
      <div className="max-w-4xl text-center py-10 text-sova-subtext">
        <h1 className="text-xl font-semibold mb-2 text-sova-text">Inbox Access Denied</h1>
        <p>You must have the REVIEWER or ADMIN role to access the Inbox.</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <h1 className="text-xl font-semibold mb-1">Reviewer Inbox</h1>
      <p className="text-sova-subtext text-sm mb-4">
        Unified view of all tasks requiring human approval across your projects.
      </p>

      {error && <div className="text-red-400 text-sm mb-4">{error}</div>}

      {loading ? (
        <div className="text-sm text-sova-subtext">Loading...</div>
      ) : tasks.length === 0 ? (
        <div className="card text-center py-10 text-sova-subtext">
          <p>No tasks currently awaiting approval.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((t) => (
            <div key={t.id} className="card border-amber-500/30">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedTask(expandedTask === t.id ? null : t.id)}
              >
                <div>
                  <div className="font-medium text-sm text-sova-text line-clamp-1">{t.input_text}</div>
                  <div className="text-[11px] text-sova-subtext mt-1">
                    Task ID: <span className="font-mono text-sova-accent">{t.id}</span> • {new Date(t.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex gap-3 items-center">
                  <span className="badge badge-warn">AWAITING APPROVAL</span>
                  <span className="text-xs text-sova-accent hover:underline">
                    {expandedTask === t.id ? "Hide" : "Review"}
                  </span>
                </div>
              </div>

              {expandedTask === t.id && (
                <div className="mt-4 pt-4 border-t border-sova-border space-y-4">
                  {/* Results preview */}
                  <div>
                    <h3 className="text-xs font-semibold text-sova-subtext uppercase tracking-wider mb-2">Finding / Result</h3>
                    <div className="text-sm bg-sova-panel2 p-3 rounded text-sova-text whitespace-pre-wrap">{t.result_text}</div>
                  </div>
                  
                  {t.compliance_table && t.compliance_table.length > 0 && (
                    <div>
                      <h3 className="text-xs font-semibold text-sova-subtext uppercase tracking-wider mb-2">Compliance Table</h3>
                      <div className="overflow-x-auto rounded border border-sova-border">
                        <table className="w-full text-left text-sm whitespace-nowrap">
                          <thead className="bg-sova-panel2 text-sova-subtext text-xs uppercase">
                            <tr>
                              <th className="px-3 py-2 font-medium">Parameter</th>
                              <th className="px-3 py-2 font-medium">Measured</th>
                              <th className="px-3 py-2 font-medium">Limit</th>
                              <th className="px-3 py-2 font-medium">Status</th>
                              <th className="px-3 py-2 font-medium">Trace</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-sova-border">
                            {t.compliance_table.map((row, i) => (
                              <tr key={i} className="hover:bg-sova-panel2 transition-colors">
                                <td className="px-3 py-2 font-medium">{row.parameter}</td>
                                <td className="px-3 py-2 font-mono text-xs">{row.measured}</td>
                                <td className="px-3 py-2 font-mono text-xs text-sova-subtext">{row.limit}</td>
                                <td className="px-3 py-2">
                                  <span className={`badge ${row.status === "PASS" ? "badge-ok" : row.status === "FAIL" ? "badge-fail" : "badge-warn"}`}>
                                    {row.status}
                                  </span>
                                </td>
                                <td className="px-3 py-2">
                                  <Link to="/rules" className="text-xs text-sova-accent hover:underline font-mono truncate max-w-[150px] inline-block" title={row.source_page || "View Rules"}>
                                    {row.source_page || "Trace"}
                                  </Link>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* E-Signature Box */}
                  <div className="bg-sova-panel2 p-4 rounded-lg border border-sova-border">
                    <h3 className="text-sm font-medium mb-3">E-Signature Approval</h3>
                    <div className="space-y-3">
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        rows={2}
                        placeholder="Optional review comment (findings, exceptions, overrides)..."
                        className="w-full bg-sova-bg border border-sova-border rounded px-3 py-2 text-sm outline-none focus:border-sova-accent resize-none"
                      />
                      <div className="flex gap-2 items-center">
                        <input
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Enter your password to sign"
                          className="bg-sova-bg border border-sova-border rounded px-3 py-2 text-sm outline-none focus:border-sova-accent flex-1"
                        />
                        <button 
                          onClick={() => handleAction(t.id, "approve")} 
                          disabled={actionLoading || !password} 
                          className="btn btn-primary whitespace-nowrap"
                        >
                          {actionLoading ? "Signing..." : "Approve & Sign"}
                        </button>
                        <button 
                          onClick={() => handleAction(t.id, "reject")} 
                          disabled={actionLoading || !password} 
                          className="btn btn-secondary whitespace-nowrap"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
