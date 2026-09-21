import { useEffect, useRef, useState } from "react";
import { useApp } from "../store.js";
import client from "../api/client.js";

export default function Documents() {
  const { project } = useApp();
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [docRole, setDocRole] = useState("OTHER");
  const [docVersion, setDocVersion] = useState("1.0");
  const [docStatus, setDocStatus] = useState("ACTIVE");
  const inputRef = useRef(null);

  const load = () => {
    if (!project) return;
    client.get(`/documents/project/${project.id}`).then((r) => setDocs(r.data));
  };
  useEffect(() => { load(); }, [project]);

  const upload = async (files) => {
    if (!project || !files.length) return;
    setUploading(true);
    for (const file of files) {
      const form = new FormData();
      form.append("project_id", project.id);
      form.append("confidentiality", "Internal");
      form.append("doc_role", docRole);
      form.append("version", docVersion);
      form.append("status", docStatus);
      form.append("file", file);
      try {
        await client.post("/documents/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      } catch (e) {
        console.error(e);
      }
    }
    setUploading(false);
    load();
  };

  if (!project) return <div className="text-sova-subtext text-sm">Select a project from the Dashboard first.</div>;

  return (
    <div className="max-w-4xl">
      <h1 className="text-xl font-semibold mb-1">Document Manager</h1>
      <p className="text-sova-subtext text-sm mb-6">Project: <span className="font-mono">{project.name}</span></p>

      <div className="card mb-6">
        <div className="flex gap-4 mb-4">
          <div>
            <label className="block text-[11px] uppercase tracking-wider text-sova-subtext mb-1">Document Role</label>
            <select className="bg-sova-panel2 border border-sova-border rounded px-2 py-1 text-sm outline-none" value={docRole} onChange={(e) => setDocRole(e.target.value)}>
              <option value="SOP">SOP (Rules / Procedures)</option>
              <option value="INSPECTION_REPORT">Inspection Report (Measurements)</option>
              <option value="OTHER">Other / Reference</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider text-sova-subtext mb-1">Status</label>
            <select className="bg-sova-panel2 border border-sova-border rounded px-2 py-1 text-sm outline-none" value={docStatus} onChange={(e) => setDocStatus(e.target.value)}>
              <option value="ACTIVE">Active</option>
              <option value="SUPERSEDED">Superseded</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider text-sova-subtext mb-1">Version</label>
            <input type="text" className="bg-sova-panel2 border border-sova-border rounded px-2 py-1 text-sm outline-none w-24" value={docVersion} onChange={(e) => setDocVersion(e.target.value)} />
          </div>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); upload(Array.from(e.dataTransfer.files)); }}
          onClick={() => inputRef.current.click()}
          className={`border-dashed border-2 rounded-lg text-center py-10 cursor-pointer ${dragOver ? "border-sova-accent bg-sova-panel2" : "border-sova-border"}`}
        >
          <input ref={inputRef} type="file" multiple hidden onChange={(e) => upload(Array.from(e.target.files))} />
          <div className="text-sova-subtext text-sm">
            {uploading ? "Processing (OCR / parsing / embedding)…" : "Drag & drop files here, or click to browse"}
          </div>
          <div className="text-[11px] text-sova-subtext mt-1">PDF · DOCX · XLSX · PNG/JPG · TXT — max 50MB</div>
        </div>
      </div>

      <div className="space-y-2">
        {docs.map((d) => (
          <div key={d.id} className="card flex items-center justify-between">
            <div>
              <div className="text-sm font-medium flex items-center gap-2">
                {d.filename}
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${d.doc_role === 'SOP' ? 'bg-blue-900 text-blue-200' : d.doc_role === 'INSPECTION_REPORT' ? 'bg-emerald-900 text-emerald-200' : 'bg-gray-800 text-gray-300'}`}>
                  {d.doc_role}
                </span>
              </div>
              <div className="text-xs text-sova-subtext mt-1">{d.pages} page(s) · {d.confidentiality} · {d.doc_status} v{d.version} · uploaded {new Date(d.uploaded_at).toLocaleString()}</div>
            </div>
            <span className={`badge ${d.status === "DONE" ? "badge-ok" : d.status === "FAILED" ? "badge-fail" : "badge-warn"}`}>{d.status}</span>
          </div>
        ))}
        {docs.length === 0 && <div className="text-sova-subtext text-sm">No documents uploaded yet.</div>}
      </div>
    </div>
  );
}
