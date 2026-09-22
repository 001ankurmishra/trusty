import { useEffect, useRef, useState } from "react";
import { useApp } from "../store.js";
import client from "../api/client.js";

export default function Documents() {
  const { project } = useApp();
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [pendingFiles, setPendingFiles] = useState([]);

  const handleFilesSelected = (files) => {
    if (!files.length) return;
    const pending = files.map(f => {
      const name = f.name.toLowerCase();
      let suggestedRole = "OTHER";
      if (name.includes("sop") || name.includes("rule") || name.includes("procedure")) {
        suggestedRole = "SOP";
      } else if (name.includes("inspect") || name.includes("report") || name.includes("measurement")) {
        suggestedRole = "INSPECTION_REPORT";
      }
      return { file: f, role: suggestedRole, version: "1.0", status: "ACTIVE" };
    });
    setPendingFiles(pending);
  };

  const confirmUpload = async () => {
    if (!project || !pendingFiles.length) return;
    setUploading(true);
    for (const pf of pendingFiles) {
      const form = new FormData();
      form.append("project_id", project.id);
      form.append("confidentiality", "Internal");
      form.append("doc_role", pf.role);
      form.append("version", pf.version);
      form.append("status", pf.status);
      form.append("file", pf.file);
      try {
        await client.post("/documents/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      } catch (e) {
        console.error(e);
      }
    }
    setUploading(false);
    setPendingFiles([]);
    load();
  };

  const inputRef = useRef(null);

  const load = async () => {
    if (!project) return;
    try {
      const res = await client.get(`/documents/project/${project.id}`);
      setDocs(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, [project]);

  const handleEdit = async (docId, newRole, newVersion, newStatus) => {
    try {
      await client.put(`/documents/${docId}`, {
        doc_role: newRole,
        version: newVersion,
        status: newStatus
      });
      load();
    } catch (e) {
      console.error(e);
    }
  };

  if (!project) return <div className="text-sova-subtext text-sm">Select a project from the Dashboard first.</div>;

  return (
    <div className="max-w-4xl">
      <h1 className="text-xl font-semibold mb-1">Document Manager</h1>
      <p className="text-sova-subtext text-sm mb-6">Project: <span className="font-mono">{project.name}</span></p>

      {pendingFiles.length > 0 ? (
        <div className="card mb-6 border-sova-accent/50">
          <div className="text-sm font-medium mb-3">Confirm Document Roles</div>
          <div className="space-y-3 mb-4">
            {pendingFiles.map((pf, i) => (
              <div key={i} className="flex items-center gap-3 bg-sova-panel2 p-2 rounded">
                <div className="text-sm flex-1 truncate">{pf.file.name}</div>
                <select 
                  className="bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none"
                  value={pf.role}
                  onChange={(e) => {
                    const newPending = [...pendingFiles];
                    newPending[i].role = e.target.value;
                    setPendingFiles(newPending);
                  }}
                >
                  <option value="SOP">SOP</option>
                  <option value="INSPECTION_REPORT">Inspection Report</option>
                  <option value="OTHER">Other / Reference</option>
                </select>
                <input 
                  type="text" 
                  className="bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none w-16" 
                  value={pf.version} 
                  onChange={(e) => {
                    const newPending = [...pendingFiles];
                    newPending[i].version = e.target.value;
                    setPendingFiles(newPending);
                  }}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <button className="btn btn-secondary text-xs" onClick={() => setPendingFiles([])}>Cancel</button>
            <button className="btn btn-primary text-xs" onClick={confirmUpload} disabled={uploading}>
              {uploading ? "Uploading..." : "Confirm & Upload"}
            </button>
          </div>
        </div>
      ) : (
        <div className="card mb-6">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFilesSelected(Array.from(e.dataTransfer.files)); }}
            onClick={() => inputRef.current.click()}
            className={`border-dashed border-2 rounded-lg text-center py-10 cursor-pointer ${dragOver ? "border-sova-accent bg-sova-panel2" : "border-sova-border"}`}
          >
            <input ref={inputRef} type="file" multiple hidden onChange={(e) => handleFilesSelected(Array.from(e.target.files))} />
            <div className="text-sova-subtext text-sm">
              Drag & drop files here, or click to browse
            </div>
            <div className="text-[11px] text-sova-subtext mt-1">PDF · DOCX · XLSX · PNG/JPG · TXT — max 50MB</div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {docs.map((d) => (
          <DocRow key={d.id} doc={d} onUpdate={(role, version, status) => handleEdit(d.id, role, version, status)} />
        ))}
        {docs.length === 0 && <div className="text-sova-subtext text-sm">No documents uploaded yet.</div>}
      </div>
    </div>
  );
}

function DocRow({ doc, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState(doc.doc_role);
  const [version, setVersion] = useState(doc.version);
  const [status, setStatus] = useState(doc.doc_status);

  if (editing) {
    return (
      <div className="card flex items-center justify-between bg-sova-panel2 p-3 rounded">
        <div className="flex-1 flex flex-col gap-2">
          <div className="text-sm font-medium">{doc.filename}</div>
          <div className="flex gap-2">
            <select className="bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none" value={role} onChange={e => setRole(e.target.value)}>
              <option value="SOP">SOP</option>
              <option value="INSPECTION_REPORT">Inspection Report</option>
              <option value="OTHER">Other / Reference</option>
            </select>
            <input type="text" className="bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none w-20" value={version} onChange={e => setVersion(e.target.value)} />
            <select className="bg-sova-bg border border-sova-border rounded px-2 py-1 text-xs outline-none" value={status} onChange={e => setStatus(e.target.value)}>
              <option value="ACTIVE">ACTIVE</option>
              <option value="SUPERSEDED">SUPERSEDED</option>
            </select>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary text-xs" onClick={() => setEditing(false)}>Cancel</button>
          <button className="btn btn-primary text-xs" onClick={() => { onUpdate(role, version, status); setEditing(false); }}>Save</button>
        </div>
      </div>
    );
  }

  return (
    <div className="card flex items-center justify-between p-3 rounded">
      <div>
        <div className="text-sm font-medium flex items-center gap-2">
          {doc.filename}
          <span className={`text-[10px] px-1.5 py-0.5 rounded cursor-pointer hover:opacity-80 ${doc.doc_role === 'SOP' ? 'bg-blue-900 text-blue-200' : doc.doc_role === 'INSPECTION_REPORT' ? 'bg-emerald-900 text-emerald-200' : 'bg-gray-800 text-gray-300'}`} onClick={() => setEditing(true)} title="Click to edit">
            {doc.doc_role} ✎
          </span>
        </div>
        <div className="text-xs text-sova-subtext mt-1">{doc.pages} page(s) · {doc.confidentiality} · {doc.doc_status} v{doc.version} · uploaded {new Date(doc.uploaded_at).toLocaleString()}</div>
      </div>
      <span className={`badge ${doc.status === "DONE" ? "badge-ok" : doc.status === "FAILED" ? "badge-fail" : "badge-warn"}`}>{doc.status}</span>
    </div>
  );
}
