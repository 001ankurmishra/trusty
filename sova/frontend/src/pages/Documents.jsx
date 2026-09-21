import { useEffect, useRef, useState } from "react";
import { useApp } from "../store.js";
import client from "../api/client.js";

export default function Documents() {
  const { project } = useApp();
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
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

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); upload(Array.from(e.dataTransfer.files)); }}
        onClick={() => inputRef.current.click()}
        className={`card border-dashed border-2 text-center py-10 cursor-pointer mb-6 ${dragOver ? "border-sova-accent bg-sova-panel2" : "border-sova-border"}`}
      >
        <input ref={inputRef} type="file" multiple hidden onChange={(e) => upload(Array.from(e.target.files))} />
        <div className="text-sova-subtext text-sm">
          {uploading ? "Processing (OCR / parsing / embedding)…" : "Drag & drop files here, or click to browse"}
        </div>
        <div className="text-[11px] text-sova-subtext mt-1">PDF · DOCX · XLSX · PNG/JPG · TXT — max 50MB</div>
      </div>

      <div className="space-y-2">
        {docs.map((d) => (
          <div key={d.id} className="card flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{d.filename}</div>
              <div className="text-xs text-sova-subtext">{d.pages} page(s) · {d.confidentiality} · uploaded {new Date(d.uploaded_at).toLocaleString()}</div>
            </div>
            <span className={`badge ${d.status === "DONE" ? "badge-ok" : d.status === "FAILED" ? "badge-fail" : "badge-warn"}`}>{d.status}</span>
          </div>
        ))}
        {docs.length === 0 && <div className="text-sova-subtext text-sm">No documents uploaded yet.</div>}
      </div>
    </div>
  );
}
