import { useEffect, useState } from "react";
import client from "../api/client.js";

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const res = await client.get("/metrics");
      setMetrics(res.data);
    } catch (e) {
      setError("Failed to load metrics");
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (error) return <div className="text-red-500 text-sm">{error}</div>;
  if (!metrics) return <div className="text-sova-subtext text-sm">Loading metrics...</div>;

  return (
    <div className="max-w-4xl">
      <h1 className="text-xl font-semibold mb-6">System Metrics</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card text-center p-4">
          <div className="text-2xl font-bold font-mono">{metrics.total_tasks}</div>
          <div className="text-xs text-sova-subtext mt-1 uppercase tracking-wider">Total Tasks</div>
        </div>
        <div className="card text-center p-4">
          <div className="text-2xl font-bold font-mono text-emerald-400">
            {metrics.status_counts.DONE || 0}
          </div>
          <div className="text-xs text-sova-subtext mt-1 uppercase tracking-wider">Done</div>
        </div>
        <div className="card text-center p-4">
          <div className="text-2xl font-bold font-mono text-amber-400">
            {metrics.status_counts.PENDING || 0}
          </div>
          <div className="text-xs text-sova-subtext mt-1 uppercase tracking-wider">Pending</div>
        </div>
        <div className="card text-center p-4">
          <div className="text-2xl font-bold font-mono text-red-400">
            {metrics.status_counts.FAILED || 0}
          </div>
          <div className="text-xs text-sova-subtext mt-1 uppercase tracking-wider">Failed</div>
        </div>
      </div>

      <div className="card mb-6">
        <h2 className="text-sm font-medium mb-4 border-b border-sova-border pb-2">Task Approvals</h2>
        <div className="space-y-3">
          <div className="flex justify-between items-center bg-sova-panel2 p-2 rounded">
            <span className="text-sm">APPROVED</span>
            <span className="font-mono text-emerald-400">{metrics.approval_counts.APPROVED || 0}</span>
          </div>
          <div className="flex justify-between items-center bg-sova-panel2 p-2 rounded">
            <span className="text-sm">REJECTED</span>
            <span className="font-mono text-red-400">{metrics.approval_counts.REJECTED || 0}</span>
          </div>
          <div className="flex justify-between items-center bg-sova-panel2 p-2 rounded">
            <span className="text-sm">PENDING</span>
            <span className="font-mono text-amber-400">{metrics.approval_counts.PENDING || 0}</span>
          </div>
          <div className="flex justify-between items-center bg-sova-panel2 p-2 rounded text-sova-subtext">
            <span className="text-sm">NONE (Auto-passed)</span>
            <span className="font-mono">{metrics.approval_counts.NONE || 0}</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-sm font-medium mb-4 border-b border-sova-border pb-2">Performance</h2>
        <div className="flex justify-between items-center bg-sova-panel2 p-2 rounded">
          <span className="text-sm">Average Processing Time</span>
          <span className="font-mono text-blue-400">
            {metrics.avg_processing_time_seconds ? metrics.avg_processing_time_seconds.toFixed(2) : "0.00"} s
          </span>
        </div>
      </div>
    </div>
  );
}
