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
  const [rowComments, setRowComments] = useState({});
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
      await client.post(`/tasks/${taskId}/${decision}`, { comment, password, row_comments: rowComments[taskId] || {} });
      setComment("");
      setPassword("");
      setRowComments(prev => ({ ...prev, [taskId]: {} }));
      setExpandedTask(null);
      fetchInbox(); // Refresh list
    } catch (e) {
      alert(e?.response?.data?.detail || "Action failed.");
    } finally {
      setActionLoading(false);
    }
  };

  if (user?.role !== "REVIEWER" && user?.role !== "ADMIN") {
    return <div className="p-8 text-center text-sova-subtext">Only Reviewers and Admins can access the Inbox.</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Reviewer Inbox</h1>
        <button onClick={fetchInbox} className="text-xs text-sova-subtext hover:text-sova-text">Refresh</button>
      </div>

      {loading ? (
        <div className="animate-pulse flex space-x-4"><div className="flex-1 space-y-4 py-1"><div className="h-4 bg-sova-panel2 rounded w-3/4"></div></div></div>
      ) : error ? (
        <div className="text-red-400 text-sm bg-red-400/10 p-3 rounded">{error}</div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 text-sova-subtext border border-dashed border-sova-border rounded-lg bg-sova-panel2/30">
          No pending tasks require your approval.
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map(t => (
            <div key={t.id} className="card">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="font-medium text-lg">Task: {t.input_text.substring(0, 100)}...</h2>
                  <div className="text-xs text-sova-subtext mt-1">
                    Project ID: <span className="font-mono text-sova-accent">{t.project_id}</span> • 
                    Requested By: <span className="font-mono">{t.user_id}</span>
                  </div>
                </div>
                <button 
                  onClick={() => setExpandedTask(expandedTask === t.id ? null : t.id)}
                  className="text-xs text-sova-accent hover:underline"
                >
                  {expandedTask === t.id ? "Collapse" : "Review details"}
                </button>
              </div>

              {expandedTask === t.id && (
                <div className="mt-4 pt-4 border-t border-sova-border space-y-4">
                  <div>
                    <h3 className="text-sm font-medium mb-1">Agent Findings</h3>
                    <div className="bg-sova-bg p-3 rounded text-sm whitespace-pre-wrap font-mono border border-sova-border">
                      {t.result_text || "No summary provided."}
                    </div>
                  </div>

                  {t.compliance_table && t.compliance_table.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium mb-2">Compliance Review</h3>
                      <div className="overflow-x-auto rounded border border-sova-border">
                        <table className="w-full text-left text-sm whitespace-nowrap">
                          <thead className="bg-sova-panel2 text-sova-subtext text-xs uppercase">
                            <tr>
                              <th className="px-3 py-2 font-medium">Parameter</th>
                              <th className="px-3 py-2 font-medium">Measured</th>
                              <th className="px-3 py-2 font-medium">Limit</th>
                              <th className="px-3 py-2 font-medium">Status</th>
                              <th className="px-3 py-2 font-medium">Source</th>
                              <th className="px-3 py-2 font-medium">Reviewer Comment</th>
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
                                <td className="px-3 py-2 min-w-[200px]">
                                  <input
                                    type="text"
                                    value={rowComments[t.id]?.[i] || ""}
                                    onChange={(e) => setRowComments(prev => ({ ...prev, [t.id]: { ...(prev[t.id] || {}), [i]: e.target.value } }))}
                                    placeholder="Add note..."
                                    className="w-full bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none focus:border-sova-accent"
                                  />
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
