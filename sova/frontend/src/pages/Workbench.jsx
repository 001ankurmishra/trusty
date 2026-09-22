import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../store.js";
import client from "../api/client.js";

const STEP_ICON = { DONE: "✓", FAILED: "✕", WAITING: "!", RUNNING: "…" };
const STEP_CLASS = { DONE: "badge-ok", FAILED: "badge-fail", WAITING: "badge-warn", RUNNING: "badge-neutral" };

function getTrustScore(task) {
  const checks = [];
  let score = 100;
  const verification = task.verification || {};

  if (task.sources?.length) {
    checks.push({ label: `${task.sources.length} source chunks retrieved`, status: "PASS" });
  } else {
    score -= 20;
    checks.push({ label: "No project evidence retrieved", status: "WARN" });
  }

  if (verification.source_verification === "PASS") {
    checks.push({ label: "Source verification passed", status: "PASS" });
  } else if (verification.source_verification === "INSUFFICIENT_EVIDENCE") {
    score -= 20;
    checks.push({ label: "Insufficient evidence from documents", status: "WARN" });
  } else {
    score -= 15;
    checks.push({ label: "Source verification needs review", status: "WARN" });
  }

  if (verification.low_confidence_sources_flagged) {
    score -= 10;
    checks.push({ label: "Low-confidence OCR evidence flagged", status: "WARN" });
  } else {
    checks.push({ label: "No low-confidence OCR evidence", status: "PASS" });
  }

  if (verification.calculation_verified === false || verification.code_execution_verified === false) {
    score -= 15;
    checks.push({ label: "Tool verification failed", status: "FAIL" });
  } else if (verification.calculation_verified || verification.code_execution_verified) {
    checks.push({ label: "Tool execution verified", status: "PASS" });
  }

  if (verification.output_truncated) {
    score -= 5;
    checks.push({ label: "Output was truncated (token limit)", status: "WARN" });
  }

  if (verification.deliverable_quality_check === "PASS") {
    checks.push({ label: "Deliverable quality check passed", status: "PASS" });
  } else if (verification.deliverable_quality_check === "FAIL") {
    score -= 15;
    checks.push({ label: "Deliverable quality check failed", status: "FAIL" });
  }

  if (task.approval_status === "APPROVED") {
    checks.push({ label: "Human review approved", status: "PASS" });
  } else if (task.approval_status === "PENDING") {
    score -= 10;
    checks.push({ label: "Human review pending", status: "WARN" });
  } else if (task.approval_status === "REJECTED") {
    score -= 30;
    checks.push({ label: "Human review rejected", status: "FAIL" });
  }

  return { score: Math.max(0, score), checks };
}

export default function Workbench() {
  const { project, user } = useApp();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [task, setTask] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [comment, setComment] = useState("");
  const [password, setPassword] = useState("");
  const [rowComments, setRowComments] = useState({});
  const [projectDocs, setProjectDocs] = useState([]);
  const pollRef = useRef(null);

  // Fetch docs for warnings
  useEffect(() => {
    if (!project) return;
    client.get(`/documents/project/${project.id}`)
      .then(res => setProjectDocs(res.data))
      .catch(console.error);
  }, [project]);

  // Live polling: poll task status every 1s until final
  useEffect(() => {
    if (!task || !["RUNNING", "RECEIVED"].includes(task.status)) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const res = await client.get(`/tasks/${task.id}`);
        setTask(res.data);
        if (!["RUNNING", "RECEIVED"].includes(res.data.status)) {
          clearInterval(pollRef.current);
          setLoading(false);
        }
      } catch {
        // ignore polling errors
      }
    }, 1000);
    return () => clearInterval(pollRef.current);
  }, [task?.id, task?.status]);

  const run = async () => {
    if (!project || !input.trim()) return;
    setLoading(true);
    setError("");
    setTask(null);
    setRowComments({});
    try {
      const res = await client.post("/tasks", { project_id: project.id, input_text: input });
      setTask(res.data);
      // polling will start via useEffect
    } catch (e) {
      setError(e?.response?.data?.detail || "Task failed. Check backend / Ollama status.");
      setLoading(false);
    }
  };

  const approve = async (decision) => {
    if (!password.trim()) {
      setError("Password is required for e-signature.");
      return;
    }
    setApprovalLoading(true);
    setError("");
    try {
      const res = await client.post(`/tasks/${task.id}/${decision}`, { comment, password, row_comments: rowComments });
      setTask(res.data);
      setComment("");
      setPassword("");
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not update the approval decision.");
    } finally {
      setApprovalLoading(false);
    }
  };

  const downloadArtifact = async () => {
    if (!task?.artifact_id) return;
    setDownloading(true);
    setError("");
    try {
      const response = await client.get(`/tasks/artifact/${task.artifact_id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Inspection_Approval_Note.docx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      const detail = e?.response?.status === 403
        ? "Download blocked: task requires approval first."
        : (e?.response?.data?.detail || "Could not download the inspection note.");
      setError(detail);
    } finally {
      setDownloading(false);
    }
  };

  const examples = [
    "Analyze this pressure vessel inspection report, compare with our internal SOP, and prepare an approval note.",
    "Summarize the safety findings from the uploaded documents in this project.",
    "Write a Python function to calculate the maximum allowable working pressure and run it.",
    "Calculate 245 * 3.7 and explain the result.",
  ];

  const isRunning = task && ["RUNNING", "RECEIVED"].includes(task.status);

  return (
    <div className="max-w-5xl">
      <h1 className="text-xl font-semibold mb-1">Workbench</h1>
      <p className="text-sova-subtext text-sm mb-4">
        Task runs through: classify → route → retrieve → tool use → verify → (approval) → deliverable — entirely on local models.
      </p>

      {projectDocs.length > 0 && (
        <div className="mb-4 space-y-2">
          {!projectDocs.some(d => d.doc_role === "SOP") && (
            <div className="text-amber-400 bg-amber-400/10 border border-amber-400/30 px-3 py-2 rounded text-sm">
              <strong>Warning:</strong> No SOP found in this project. Compliance tasks will likely fail to find rules.
            </div>
          )}
          {!projectDocs.some(d => d.doc_role === "INSPECTION_REPORT") && (
            <div className="text-amber-400 bg-amber-400/10 border border-amber-400/30 px-3 py-2 rounded text-sm">
              <strong>Warning:</strong> No Inspection Report found. The agent may not have data to verify compliance against.
            </div>
          )}
        </div>
      )}

      <div className="card mb-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={3}
          placeholder="Describe the task... e.g. 'Analyze this inspection report and prepare an approval note.'"
          className="w-full bg-sova-panel2 border border-sova-border rounded-lg px-3 py-2 text-sm outline-none focus:border-sova-accent resize-none"
        />
        <div className="flex items-center justify-between mt-3">
          <div className="flex gap-2 flex-wrap">
            {examples.map((ex) => (
              <button key={ex} onClick={() => setInput(ex)} className="text-[11px] text-sova-subtext hover:text-sova-accent border border-sova-border rounded-full px-2 py-1">
                {ex.slice(0, 34)}…
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3 ml-3 shrink-0">
            {isRunning && (
              <button 
                onClick={async () => {
                  try {
                    await client.post(`/tasks/${task.id}/cancel`);
                  } catch(e) {
                    setError("Failed to cancel task.");
                  }
                }}
                className="btn border border-red-500/30 text-red-400 hover:bg-red-500/10 text-xs py-1"
              >
                Cancel
              </button>
            )}
            <button onClick={run} disabled={loading} className="btn btn-primary">
              {loading ? (isRunning ? "Agent working…" : "Starting…") : "Run Task"}
            </button>
          </div>
        </div>
      </div>
      
      {task?.status === "RECEIVED" && (
        <div className="text-amber-400 text-sm mb-4 bg-amber-400/10 border border-amber-400/30 px-3 py-2 rounded">
          <strong>Task Queued:</strong> You are currently at position {task.queue_position || 1} in the queue.
        </div>
      )}
      
      {error && <div className="text-red-400 text-sm mb-4">{error}</div>}

      {task && (
        <div className="grid grid-cols-3 gap-4 mt-6">
          {/* Execution timeline */}
          <div className="col-span-2 space-y-4">
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-medium">Agent Execution Timeline</div>
                {isRunning && <span className="badge badge-warn">● LIVE</span>}
              </div>
              <div className="space-y-2">
                {task.steps.map((s, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className={`badge ${STEP_CLASS[s.status] || "badge-neutral"} shrink-0`}>{STEP_ICON[s.status] || "•"}</span>
                    <div className="min-w-0">
                      <div className="text-sm">{s.step}</div>
                      <div className="text-xs text-sova-subtext break-words">{s.detail}</div>
                    </div>
                  </div>
                ))}
                {isRunning && (
                  <div className="flex items-start gap-3">
                    <span className="badge badge-neutral shrink-0">…</span>
                    <div className="text-sm text-sova-subtext animate-pulse">Processing…</div>
                  </div>
                )}
              </div>
            </div>

            {!isRunning && task.result_text && (
              <div className="card border-sova-accent/20">
                <div className="text-sm font-medium mb-2">Result</div>
                <div className="text-sm text-sova-text whitespace-pre-wrap leading-relaxed">{task.result_text}</div>
              </div>
            )}

            {!isRunning && task.compliance_table && task.compliance_table.length > 0 && (
              <div className="card border-sova-accent/20">
                <div className="text-sm font-medium mb-3">Compliance Comparison</div>
                <div className="overflow-x-auto rounded border border-sova-border">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-sova-panel2 text-sova-subtext text-xs uppercase">
                      <tr>
                        <th className="px-3 py-2 font-medium">Parameter</th>
                        <th className="px-3 py-2 font-medium">Measured</th>
                        <th className="px-3 py-2 font-medium">Limit (SOP)</th>
                        <th className="px-3 py-2 font-medium">Status</th>
                        <th className="px-3 py-2 font-medium">Source</th>
                        <th className="px-3 py-2 font-medium">Reviewer Comment</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-sova-border">
                      {task.compliance_table.map((row, i) => (
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
                            {task.approval_status === "PENDING" && (user?.role === "REVIEWER" || user?.role === "ADMIN") ? (
                              <input
                                type="text"
                                value={rowComments[i] || ""}
                                onChange={(e) => setRowComments(prev => ({ ...prev, [i]: e.target.value }))}
                                placeholder="Add note..."
                                className="w-full bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none focus:border-sova-accent"
                              />
                            ) : (
                              <span className="text-xs text-sova-subtext">{row.reviewer_comment || "-"}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {task.requires_approval && (
              <div className="card border-amber-500/40">
                <div className={`text-sm font-medium mb-2 ${task.approval_status === "APPROVED" ? "text-emerald-400" : task.approval_status === "REJECTED" ? "text-red-400" : "text-amber-400"}`}>
                  {task.approval_status === "APPROVED" ? "Human Review Approved" : task.approval_status === "REJECTED" ? "Human Review Rejected" : "Human-in-the-Loop Approval Required"}
                </div>
                <div className="text-xs text-sova-subtext mb-3">
                  Status: <span className={`font-mono ${task.approval_status === "APPROVED" ? "text-emerald-400" : task.approval_status === "REJECTED" ? "text-red-400" : "text-amber-400"}`}>{task.approval_status}</span>
                  {user?.role !== "REVIEWER" && user?.role !== "ADMIN" && " — sign in as a REVIEWER/ADMIN to approve."}
                </div>
                {(user?.role === "REVIEWER" || user?.role === "ADMIN") && task.approval_status === "PENDING" && (
                  <div className="space-y-3">
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      rows={2}
                      placeholder="Optional review comment…"
                      className="w-full bg-sova-panel2 border border-sova-border rounded-lg px-3 py-2 text-sm outline-none focus:border-sova-accent resize-none"
                    />
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="E-signature password"
                        className="bg-sova-panel2 border border-sova-border rounded-lg px-3 py-1 text-sm outline-none focus:border-sova-accent flex-1"
                      />
                      <button onClick={() => approve("approve")} disabled={approvalLoading || !password} className="btn btn-primary shrink-0">{approvalLoading ? "Updating…" : "Approve"}</button>
                      <button onClick={() => approve("reject")} disabled={approvalLoading || !password} className="btn btn-secondary shrink-0">Reject</button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!isRunning && task.verification?.warnings?.length > 0 && (
              <div className="card border-amber-500/40 bg-amber-900/10">
                <div className="text-sm font-medium text-amber-400 mb-2">Warnings</div>
                <ul className="list-disc list-inside text-xs text-amber-200/80 space-y-1">
                  {task.verification.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {task.artifact_id && !isRunning && (
              <div className="card">
                <div className="text-sm font-medium mb-2">Deliverable</div>
                <button onClick={downloadArtifact} disabled={downloading} className="btn btn-primary">
                  {downloading ? "Downloading…" : "Download Inspection_Approval_Note.docx"}
                </button>
                {task.requires_approval && task.approval_status === "PENDING" && (
                  <div className="text-xs text-amber-400 mt-2">⚠ Download blocked until approved by a reviewer.</div>
                )}
                <div className="text-xs text-sova-subtext mt-2">
                  Quality check: <span className={`badge ${task.verification.deliverable_quality_check === "PASS" ? "badge-ok" : "badge-fail"}`}>
                    {task.verification.deliverable_quality_check || "N/A"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Side panels: trust score, model router, sources, verification */}
          <div className="space-y-4">
            {!isRunning && (() => {
              const trust = getTrustScore(task);
              const scoreClass = trust.score >= 80 ? "text-emerald-400" : trust.score >= 60 ? "text-amber-400" : "text-red-400";
              return (
                <div className="card border-sova-accent/40">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="text-sm font-medium">Trust Score</div>
                      <div className="text-[11px] text-sova-subtext mt-1">Evidence, verification, and human review</div>
                    </div>
                    <div className={`text-3xl font-mono font-bold ${scoreClass}`}>{trust.score}<span className="text-sm">/100</span></div>
                  </div>
                  <div className="h-2 bg-sova-panel2 rounded-full overflow-hidden mb-3">
                    <div className={`h-full ${trust.score >= 80 ? "bg-emerald-400" : trust.score >= 60 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: `${trust.score}%` }} />
                  </div>
                  <div className="space-y-1.5">
                    {trust.checks.map((check) => (
                      <div key={check.label} className="flex items-center gap-2 text-[11px]">
                        <span className={check.status === "PASS" ? "text-emerald-400" : check.status === "WARN" ? "text-amber-400" : "text-red-400"}>
                          {check.status === "PASS" ? "✓" : check.status === "WARN" ? "!" : "✕"}
                        </span>
                        <span className="text-sova-subtext">{check.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            <div className="card">
              <div className="text-sm font-medium mb-2">Model Router</div>
              <div className="text-xs space-y-1">
                <div><span className="text-sova-subtext">Selected:</span> <span className="font-mono text-sova-accent">{task.selected_model || "…"}</span></div>
                <div className="text-sova-subtext">{task.model_reason}</div>
                {task.steps.some((step) => step.step === "Model fallback") && (
                  <div className="badge badge-warn inline-block mt-2">Fallback model used</div>
                )}
              </div>
            </div>

            {!isRunning && (
              <>
                <div className="card">
                  <div className="text-sm font-medium mb-2">Sources / Evidence</div>
                  {task.sources.length === 0 && <div className="text-xs text-sova-subtext">No sources retrieved for this task.</div>}
                  <div className="space-y-2">
                    {task.sources.map((s, i) => (
                      <div key={i} className="text-xs border border-sova-border rounded-lg p-2">
                        <div className="flex justify-between">
                          <span className="font-mono text-sova-text truncate">{s.filename}</span>
                          <span className="text-sova-subtext">p.{s.page}</span>
                        </div>
                        {s.low_confidence && <span className="badge badge-warn mt-1 inline-block">low OCR confidence</span>}
                        {s.distance != null && <div className="text-sova-subtext mt-1">distance: {s.distance.toFixed(3)}</div>}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <div className="text-sm font-medium mb-2">Verification</div>
                  <div className="text-xs space-y-1">
                    {Object.entries(task.verification).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="text-sova-subtext">{k}</span>
                        <span className="font-mono">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
