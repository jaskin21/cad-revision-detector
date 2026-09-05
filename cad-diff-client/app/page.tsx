"use client";

import { useState } from "react";

export default function UploadPage() {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [revisionId, setRevisionId] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fileA || !fileB || !projectId) return;

    setStatus("uploading...");

    const formData = new FormData();
    formData.append("fileA", fileA);
    formData.append("fileB", fileB);
    formData.append("projectId", projectId);

    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      setStatus(`Error: ${data.error || "upload failed"}`);
      return;
    }

    setRevisionId(data.revisionId);
    setStatus("queued — processing...");
    pollStatus(data.revisionId);
  }

  async function pollStatus(id: string) {
    const interval = setInterval(async () => {
      const res = await fetch(`/api/revisions/${id}`);
      const data = await res.json();

      if (data.status === "completed" || data.status === "failed") {
        clearInterval(interval);
        setStatus(data.status);
      }
    }, 2000);
  }

  return (
    <main style={{ maxWidth: 480, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>CAD Revision Detector</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label>
          Project ID
          <input value={projectId} onChange={(e) => setProjectId(e.target.value)} required />
        </label>
        <label>
          Revision A (old)
          <input type="file" accept=".pdf,.dxf" onChange={(e) => setFileA(e.target.files?.[0] || null)} required />
        </label>
        <label>
          Revision B (new)
          <input type="file" accept=".pdf,.dxf" onChange={(e) => setFileB(e.target.files?.[0] || null)} required />
        </label>
        <button type="submit">Upload & Compare</button>
      </form>

      {status && <p>Status: {status}</p>}
      {revisionId && <p>Revision ID: {revisionId}</p>}
    </main>
  );
}