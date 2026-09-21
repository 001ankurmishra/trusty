import { useEffect, useState } from "react";
import { useApp } from "../store.js";
import client from "../api/client.js";

export default function Rules() {
  const { project } = useApp();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (!project) return;
    setLoading(true);
    try {
      const res = await client.get(`/project/${project.id}/rules`);
      setRules(res.data.rules || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [project]);

  if (!project) return <div className="text-sova-subtext text-sm">Select a project from the Dashboard first.</div>;

  return (
    <div className="max-w-4xl">
      <h1 className="text-xl font-semibold mb-1">Active Rules</h1>
      <p className="text-sova-subtext text-sm mb-6">Project: <span className="font-mono">{project.name}</span></p>

      {loading ? (
        <div className="text-sm text-sova-subtext">Loading rules...</div>
      ) : rules.length === 0 ? (
        <div className="text-sm text-sova-subtext">No rules extracted from SOPs yet.</div>
      ) : (
        <div className="space-y-3">
          {rules.map((r, i) => (
            <div key={i} className="card">
              <div className="flex justify-between items-start mb-2">
                <div className="text-sm font-medium">{r.parameter}</div>
                <div className="text-[10px] bg-sova-panel2 px-2 py-1 rounded text-sova-subtext font-mono border border-sova-border">
                  {r.source_page}
                </div>
              </div>
              <div className="text-xs space-y-1 text-sova-text">
                <div><span className="text-sova-subtext">Limit:</span> {r.limit}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
