import { useEffect, useState } from "react";
import client from "../api/client.js";

export default function ModelRouterPage() {
  const [data, setData] = useState(null);

  useEffect(() => { client.get("/models").then((r) => setData(r.data)); }, []);
  if (!data) return null;

  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-semibold mb-1">Model Registry & Router</h1>
      <p className="text-sova-subtext text-sm mb-6">
        Available RAM: <span className="font-mono text-sova-accent">{data.available_ram_gb} GB</span> ·
        New models can be added via config without redesigning the app.
      </p>

      <div className="space-y-3">
        {data.registry.map((m) => {
          const installed = data.installed_locally.some((n) => n.startsWith(m.name.split(":")[0]));
          return (
            <div key={m.name} className="card flex items-center justify-between">
              <div>
                <div className="font-mono text-sm">{m.name}</div>
                <div className="text-xs text-sova-subtext mt-1">
                  type: {m.type} · capabilities: {m.capabilities.join(", ")} · ~{m.ram_gb_required}GB RAM
                </div>
              </div>
              <span className={`badge ${installed ? "badge-ok" : "badge-warn"}`}>
                {installed ? "installed" : "not pulled yet"}
              </span>
            </div>
          );
        })}
      </div>

      {data.installed_locally.length === 0 && (
        <div className="card mt-6 border-amber-500/40 text-sm text-amber-400">
          No local models detected via Ollama. Run <span className="font-mono">ollama pull &lt;model&gt;</span> for each model above (see README).
        </div>
      )}
    </div>
  );
}
