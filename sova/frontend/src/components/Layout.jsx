import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useApp } from "../store.js";
import client from "../api/client.js";

const NAV_GROUPS = [
  { title: "Overview", items: [{ to: "/", label: "Dashboard", icon: "◧" }] },
  { title: "Workspace", items: [{ to: "/workbench", label: "Workbench", icon: "⌘" }, { to: "/documents", label: "Documents", icon: "▤" }, { to: "/rules", label: "Active Rules", icon: "⚑" }] },
  { title: "Intelligence", items: [{ to: "/models", label: "Model Router", icon: "◎" }] },
  { title: "Governance", items: [{ to: "/security", label: "Security", icon: "◈" }, { to: "/audit", label: "Audit Log", icon: "≡" }] },
];

export default function Layout({ children }) {
  const { user, project, logout } = useApp();
  const navigate = useNavigate();
  const [security, setSecurity] = useState(null);

  useEffect(() => {
    const poll = () => client.get("/security/status").then((r) => setSecurity(r.data)).catch(() => {});
    poll();
    const id = setInterval(poll, 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen flex bg-sova-bg">
      <aside className="w-60 border-r border-sova-border flex flex-col bg-sova-panel">
        <div className="p-5 border-b border-sova-border">
          <div className="font-mono text-sova-accent font-bold text-lg tracking-tight">TrustForge</div>
          <div className="text-[11px] text-sova-subtext leading-tight mt-1">
            Secure AI Workbench
          </div>
        </div>
        <nav className="flex-1 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="mb-4">
              <div className="px-5 mb-2 text-[10px] uppercase tracking-[0.18em] text-sova-subtext/70 font-mono">{group.title}</div>
              {group.items.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.to === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-5 py-2.5 text-sm mx-2 rounded-lg mb-1 transition-colors ${
                      isActive ? "bg-gradient-to-r from-emerald-500/15 to-cyan-400/10 text-emerald-300 border-l-2 border-emerald-400" : "text-sova-subtext hover:text-sova-text hover:bg-sova-panel2/50 border-l-2 border-transparent"
                    }`
                  }
                >
                  <span className="w-4 text-center">{n.icon}</span>
                  {n.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="p-4 border-t border-sova-border text-xs text-sova-subtext">
          <div className="flex items-center gap-2 mb-3 text-emerald-400"><span className="status-dot" /> Local environment secure</div>
          <div className="flex items-center justify-between mb-1">
            <span>Signed in</span>
            <span className="badge badge-neutral">{user?.role}</span>
          </div>
          <div className="font-mono text-sova-text mb-2">{user?.username}</div>
          {project && (
            <div className="mb-2">
              <div className="text-sova-subtext">Project</div>
              <div className="font-mono text-sova-text truncate">{project.name}</div>
            </div>
          )}
          <button onClick={() => { logout(); navigate("/login"); }} className="btn btn-secondary w-full text-xs py-1.5">
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-sova-border flex items-center justify-between px-6 bg-sova-panel/60 backdrop-blur">
          <div className="text-sova-subtext text-sm">
            {project ? `Project Room / ${project.name}` : "No project selected"}
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`badge ${security?.external_calls_succeeded ? "badge-fail" : "badge-ok"}`}
              title="External network calls that succeeded (should be 0)"
            >
              ● external calls: {security?.external_calls_succeeded ?? "…"}
            </span>
            <span className={`badge ${security?.air_gapped_mode ? "badge-ok" : "badge-warn"}`}>
              {security?.air_gapped_mode ? "air-gapped" : "network open"}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
