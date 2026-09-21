import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../store.js";
import client from "../api/client.js";

const PROJECT_HINTS = ["Refinery Inspection Q1", "SOP Knowledge Base", "Operations Research"];
const SPARK_VALUES = [32, 46, 38, 62, 54, 78, 68, 92, 84];

function Sparkline({ pulse = false }) {
  return <div className={`sparkline ${pulse ? "pulse-line" : ""}`} aria-hidden="true">{SPARK_VALUES.map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}</div>;
}

function projectInitials(name) {
  return name.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
}

function projectKind(project) {
  const text = `${project.name} ${project.description || ""}`.toLowerCase();
  if (text.includes("inspection") || text.includes("refinery")) return "Industrial operations";
  if (text.includes("sop") || text.includes("manual")) return "Document intelligence";
  return "General AI workspace";
}

function relativeTime(value) {
  if (!value) return "No activity yet";
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.floor(hours / 24)} days ago`;
}

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [projectMeta, setProjectMeta] = useState({});
  const [models, setModels] = useState(null);
  const [security, setSecurity] = useState(null);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const { selectProject } = useApp();
  const navigate = useNavigate();

  const load = async () => {
    try {
      const [projectsResponse, modelsResponse, securityResponse] = await Promise.all([
        client.get("/projects"),
        client.get("/models"),
        client.get("/security/status"),
      ]);
      const nextProjects = projectsResponse.data;
      setProjects(nextProjects);
      setModels(modelsResponse.data);
      setSecurity(securityResponse.data);
      const metadata = await Promise.all(nextProjects.map(async (project) => {
        const [documentsResponse, tasksResponse] = await Promise.all([
          client.get(`/documents/project/${project.id}`),
          client.get(`/tasks/project/${project.id}`),
        ]);
        return [project.id, { documents: documentsResponse.data, tasks: tasksResponse.data }];
      }));
      setProjectMeta(Object.fromEntries(metadata));
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Could not load command center data.");
    }
  };

  useEffect(() => { load(); }, []);

  const create = async (event) => {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      await client.post("/projects", { name: name.trim(), description: desc.trim() });
      setName("");
      setDesc("");
      setShowCreate(false);
      await load();
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Could not create project.");
    } finally {
      setCreating(false);
    }
  };

  const openProject = (project) => {
    selectProject(project);
    navigate("/workbench");
  };

  const filteredProjects = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return projects;
    return projects.filter((project) => `${project.name} ${project.description || ""}`.toLowerCase().includes(query));
  }, [projects, search]);

  const documentCount = Object.values(projectMeta).reduce((total, meta) => total + meta.documents.length, 0);
  const indexedCount = Object.values(projectMeta).reduce((total, meta) => total + meta.documents.filter((doc) => doc.status === "DONE").length, 0);
  const onlineModels = models?.installed_locally?.length || models?.registry?.length || 0;
  const localOnly = security?.external_calls_succeeded === 0;
  const recentActivity = Object.entries(projectMeta)
    .flatMap(([projectId, meta]) => (meta.tasks || []).slice(0, 3).map((task) => ({ ...task, project: projects.find((item) => item.id === projectId)?.name || "Project room" })))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 4);

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <section className="flex flex-col lg:flex-row lg:items-end justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-sova-subtext font-mono mb-3"><span className="text-sova-accent">Command Center</span><span>/</span><span>Project Rooms</span></div>
          <h1 className="display-title text-4xl font-semibold tracking-tight">Project Command Center</h1>
          <p className="text-sova-subtext mt-2 max-w-xl">Secure AI workspaces for confidential enterprise operations.</p>
        </div>
        <div className="flex items-center gap-3"><button onClick={() => navigate("/audit")} className="btn btn-secondary">View activity</button><button onClick={() => setShowCreate(true)} className="btn btn-primary">+ New project</button></div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="metric-card"><div className="flex items-start justify-between"><div className="metric-label">Active projects</div><Sparkline /></div><div className="metric-value">{projects.length}</div><div className="metric-note text-emerald-400">Tracking live project rooms</div></div>
          <div className="metric-card"><div className="flex items-start justify-between"><div className="metric-label">Documents indexed</div><Sparkline pulse /></div><div className="metric-value">{documentCount}</div><div className="metric-note">{indexedCount} knowledge-ready</div></div>
          <div className="metric-card"><div className="metric-label">Local models</div><div className="metric-value">{onlineModels}</div><div className="metric-note text-emerald-400">{onlineModels ? "All detected locally" : "Checking runtime"}</div></div>
          <div className="metric-card"><div className="metric-label">Security status</div><div className={`metric-value text-lg ${localOnly ? "text-emerald-400" : "text-amber-400"}`}>{localOnly ? "PROTECTED" : "MONITOR"}</div><div className="metric-note">{security?.external_calls_succeeded ?? "…"} external calls</div></div>
        </div>
        <div className="security-strip"><div className="flex items-start justify-between"><div><div className="eyebrow">TrustForge security posture</div><div className="text-xl font-semibold mt-1">On-premise mode</div><div className="text-xs text-sova-subtext mt-2">Network egress is monitored at the runtime boundary.</div></div><span className="shield-mark">◈</span></div><div className="security-line"><span className="status-dot" />External API calls <strong>BLOCKED</strong></div><div className="security-line"><span className="status-dot" />Data residency <strong>LOCAL</strong></div><div className="security-line"><span className="status-dot" />Project isolation <strong>ENABLED</strong></div></div>
      </section>

      <section>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-4"><div><h2 className="section-title">Project Rooms</h2><p className="section-subtitle">Documents, models, and retrieval contexts are isolated per project.</p></div><div className="flex items-center gap-2"><label className="search-box"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search projects" /></label><button onClick={() => setShowCreate(true)} className="btn btn-secondary whitespace-nowrap">+ New project</button></div></div>
        {error && <div className="mb-4 text-sm text-red-400">{error}</div>}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {filteredProjects.map((project) => {
            const meta = projectMeta[project.id] || { documents: [], tasks: [] };
            const ready = meta.documents.filter((doc) => doc.status === "DONE").length;
            const processing = meta.documents.some((doc) => doc.status === "PROCESSING");
            const lastTask = meta.tasks[0];
            return <article key={project.id} className="project-card" onClick={() => openProject(project)}><div className="flex items-start justify-between gap-4"><div className="flex items-center gap-3 min-w-0"><div className="project-avatar">{projectInitials(project.name)}</div><div className="min-w-0"><h3 className="font-semibold truncate">{project.name}</h3><p className="text-xs text-sova-subtext mt-1 truncate">{project.description || projectKind(project)}</p></div></div><span className={`badge ${processing ? "badge-warn" : ready ? "badge-ok" : "badge-neutral"}`}>{processing ? "PROCESSING" : ready ? "ACTIVE" : "IDLE"}</span></div><div className="flex items-center gap-2 mt-5 text-[11px] text-sova-subtext"><span className="text-emerald-400">●</span> LOCAL ONLY <span className="mx-1 text-sova-border">|</span>{projectKind(project)}</div><div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-sova-border/70"><div><div className="meta-label">Documents</div><div className="meta-value">{meta.documents.length}</div></div><div><div className="meta-label">Knowledge base</div><div className="meta-value">{ready ? "Indexed" : "Empty"}</div></div><div><div className="meta-label">Last activity</div><div className="meta-value">{relativeTime(lastTask?.created_at)}</div></div></div><div className="flex items-center justify-between mt-5"><span className="text-xs text-sova-subtext">{lastTask ? "Agent activity recorded" : "Agent ready"}</span><span className="text-sm text-sova-accent font-medium">Open Workbench <span className="ml-1">→</span></span></div></article>;
          })}
          {!filteredProjects.length && <div className="empty-state col-span-full"><div className="project-avatar mx-auto mb-3">⌕</div><div className="font-medium">No project rooms match</div><div className="text-sm text-sova-subtext mt-1">Create a workspace or adjust your search.</div></div>}
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-4"><div className="card activity-live"><div className="flex items-center justify-between mb-4"><div><h2 className="section-title">Live agent activity</h2><p className="section-subtitle">Recent execution signals from local workspaces.</p></div><span className="badge badge-ok"><span className="status-dot mr-1" />LIVE</span></div>{recentActivity.length ? recentActivity.map((activity) => <div key={activity.id} className="activity-row"><span className="activity-icon">↗</span><div><div className="text-sm">Agent completed task</div><div className="text-xs text-sova-subtext mt-1 truncate max-w-[440px]">{activity.project} · {activity.input_text}</div></div><span className="activity-time">{relativeTime(activity.created_at)}</span></div>) : <div className="activity-row"><span className="activity-icon">◈</span><div><div className="text-sm">Agent runtime ready</div><div className="text-xs text-sova-subtext mt-1">Run a task to see local execution activity here.</div></div><span className="activity-time">Live</span></div>}</div><div className="card"><div className="flex items-center justify-between mb-4"><div><h2 className="section-title">AI infrastructure</h2><p className="section-subtitle">Local runtime readiness.</p></div><span className="status-dot" /></div><div className="infra-row"><span>Model router</span><span className="text-emerald-400">ONLINE</span></div><div className="infra-row"><span>Ollama runtime</span><span className="text-emerald-400">LOCAL</span></div><div className="infra-row"><span>Vector store</span><span className="text-emerald-400">CONNECTED</span></div><div className="infra-row"><span>Agent tools</span><span className="text-emerald-400">READY</span></div></div></section>

      {showCreate && <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setShowCreate(false)}><form className="modal-panel" onSubmit={create}><div className="flex items-start justify-between"><div><div className="eyebrow">New workspace</div><h2 className="text-xl font-semibold mt-1">Create project room</h2><p className="text-sm text-sova-subtext mt-1">A private context for documents, models, and agent work.</p></div><button type="button" onClick={() => setShowCreate(false)} className="icon-button" aria-label="Close">×</button></div><label className="field-label">Project name<input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder={PROJECT_HINTS[projects.length % PROJECT_HINTS.length]} /></label><label className="field-label">Description<input value={desc} onChange={(event) => setDesc(event.target.value)} placeholder="What will this workspace be used for?" /></label><div className="local-callout"><span className="text-emerald-400">●</span><div><div className="text-sm font-medium">Local-only workspace</div><div className="text-xs text-sova-subtext mt-1">Documents and retrieval stay isolated to this project room.</div></div></div><div className="flex justify-end gap-2 mt-6"><button type="button" onClick={() => setShowCreate(false)} className="btn btn-secondary">Cancel</button><button disabled={creating || !name.trim()} className="btn btn-primary">{creating ? "Creating…" : "Create project"}</button></div></form></div>}
    </div>
  );
}
