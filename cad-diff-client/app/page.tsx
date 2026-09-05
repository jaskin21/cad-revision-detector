"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Status = "idle" | "uploading" | "queued" | "processing" | "completed" | "failed";

const STEPS: { key: Status; label: string }[] = [
  { key: "uploading", label: "Upload" },
  { key: "queued", label: "Queue" },
  { key: "processing", label: "Compare" },
  { key: "completed", label: "Done" },
];

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extOf(name: string) {
  const parts = name.split(".");
  return parts.length > 1 ? parts.pop()!.toUpperCase() : "";
}

function DropSlot({
  label,
  hint,
  file,
  onFile,
  onClear,
  tone,
}: {
  label: string;
  hint: string;
  file: File | null;
  onFile: (f: File) => void;
  onClear: () => void;
  tone: "old" | "new";
}) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accentBorder = tone === "old" ? "border-l-[#8a8f88]" : "border-l-[#2a5c7a]";
  const accentText = tone === "old" ? "text-[#5b6159]" : "text-[#2a5c7a]";

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files?.[0];
      if (f) onFile(f);
    },
    [onFile]
  );

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${label}, ${file ? file.name : "no file selected"}`}
      onClick={() => !file && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !file) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={[
        "relative flex flex-col justify-between rounded-sm border border-[#d8dbd6] bg-white p-4 min-h-[168px]",
        "border-l-4",
        accentBorder,
        dragOver ? "ring-2 ring-[#2a5c7a] ring-offset-1" : "",
        file ? "cursor-default" : "cursor-pointer hover:border-[#b8bcb4]",
        "transition-shadow outline-none focus-visible:ring-2 focus-visible:ring-[#2a5c7a] focus-visible:ring-offset-1",
      ].join(" ")}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.dxf"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />

      <div className="flex items-start justify-between">
        <div>
          <p className={`font-mono text-[11px] tracking-wide uppercase ${accentText}`}>{label}</p>
          <p className="mt-0.5 text-xs text-[#8a8f88]">{hint}</p>
        </div>
        {file && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            aria-label={`Remove ${label} file`}
            className="text-[#8a8f88] hover:text-[#1c2024] text-xs font-mono leading-none px-1"
          >
            ✕
          </button>
        )}
      </div>

      {file ? (
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-[#f0efe9] font-mono text-[9px] font-semibold text-[#5b6159]">
              {extOf(file.name)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm text-[#1c2024]" title={file.name}>
                {file.name}
              </p>
              <p className="font-mono text-[11px] text-[#8a8f88]">{formatBytes(file.size)}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex items-center gap-2 text-[#b8bcb4]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 16V4M12 4L7 9M12 4l5 5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-xs">Drop file or click to browse</span>
        </div>
      )}
    </div>
  );
}

export default function UploadPage() {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [revisionId, setRevisionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const canSubmit = !!fileA && !!fileB && projectId.trim().length > 0 && status !== "uploading" && status !== "processing" && status !== "queued";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fileA || !fileB || !projectId) return;

    setError(null);
    setRevisionId(null);
    setStatus("uploading");

    try {
      const formData = new FormData();
      formData.append("fileA", fileA);
      formData.append("fileB", fileB);
      formData.append("projectId", projectId);

      const res = await fetch("/api/upload", { method: "POST", body: formData });
      let data;
      try {
        data = await res.json();
      } catch {
        data = { error: "Unexpected server response" };
      }

      if (!res.ok) {
        setStatus("failed");
        setError(data.error || "Upload failed. Check both files and try again.");
        return;
      }

      setRevisionId(data.revisionId);
      setStatus("queued");
      pollStatus(data.revisionId);
    } catch {
      setStatus("failed");
      setError("Couldn't reach the server. Check your connection and try again.");
    }
  }

  function pollStatus(id: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/revisions/${id}`);
        const data = await res.json();
        if (data.status === "processing") setStatus("processing");
        if (data.status === "completed" || data.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          setStatus(data.status);
          if (data.status === "failed") setError(data.error || "Comparison failed.");
        }
      } catch {
        // transient network hiccup — keep polling
      }
    }, 2000);
  }

  const activeStepIndex = STEPS.findIndex((s) => s.key === status);
  const isRunning = status === "uploading" || status === "queued" || status === "processing";

  return (
    <main className="min-h-screen bg-[#f6f5f1] px-4 py-10 text-[#1c2024] [font-feature-settings:'ss01']">
      <div
        className="mx-auto w-full max-w-[640px] bg-white border border-[#d8dbd6] shadow-[0_1px_0_#d8dbd6]"
        style={{
          backgroundImage:
            "linear-gradient(#eceae3 1px, transparent 1px), linear-gradient(90deg, #eceae3 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          backgroundPosition: "-1px -1px",
          backgroundAttachment: "local",
        }}
      >
        <div className="bg-white/[0.94] p-6 sm:p-8">
          {/* Header */}
          <div className="flex items-baseline justify-between border-b border-[#d8dbd6] pb-4">
            <div>
              <h1 className="text-[22px] font-semibold tracking-tight text-[#1c2024]">Revision comparison</h1>
              <p className="mt-1 text-sm text-[#5b6159]">Upload two drawing revisions to detect what changed.</p>
            </div>
            <span className="hidden sm:block font-mono text-[11px] text-[#b8bcb4]">PDF · DXF</span>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-6">
            {/* Project ID — title-block style field */}
            <div>
              <label htmlFor="projectId" className="font-mono text-[11px] uppercase tracking-wide text-[#5b6159]">
                Project ID
              </label>
              <input
                id="projectId"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="e.g. PRJ-10432"
                required
                disabled={isRunning}
                className="mt-1.5 w-full rounded-sm border border-[#d8dbd6] bg-white px-3 py-2 text-sm text-[#1c2024] placeholder:text-[#b8bcb4] outline-none focus:border-[#2a5c7a] focus:ring-1 focus:ring-[#2a5c7a] disabled:bg-[#f6f5f1] disabled:text-[#8a8f88]"
              />
            </div>

            {/* File slots with a compare arrow between them */}
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] items-center gap-3">
              <DropSlot
                label="Revision A"
                hint="Previous version"
                file={fileA}
                onFile={setFileA}
                onClear={() => setFileA(null)}
                tone="old"
              />

              <div className="flex items-center justify-center text-[#b8bcb4] sm:rotate-0 rotate-90 py-1">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M4 12h14M12 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>

              <DropSlot
                label="Revision B"
                hint="New version"
                file={fileB}
                onFile={setFileB}
                onClear={() => setFileB(null)}
                tone="new"
              />
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full rounded-sm bg-[#2a5c7a] py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#234a63] disabled:cursor-not-allowed disabled:bg-[#d8dbd6] disabled:text-[#8a8f88]"
            >
              {isRunning ? "Comparing…" : "Compare revisions"}
            </button>
          </form>

          {/* Status stepper */}
          {status !== "idle" && (
            <div className="mt-7 border-t border-[#d8dbd6] pt-5">
              {status !== "failed" ? (
                <div className="flex items-center">
                  {STEPS.map((step, i) => {
                    const done = i < activeStepIndex || status === "completed";
                    const active = i === activeStepIndex && status !== "completed";
                    return (
                      <div key={step.key} className="flex flex-1 items-center last:flex-none">
                        <div className="flex flex-col items-center gap-1.5">
                          <div
                            className={[
                              "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-mono",
                              done ? "bg-[#3f7d53] text-white" : active ? "bg-[#2a5c7a] text-white" : "bg-[#eceae3] text-[#b8bcb4]",
                            ].join(" ")}
                          >
                            {done ? "✓" : i + 1}
                          </div>
                          <span className={`text-[11px] ${active || done ? "text-[#1c2024]" : "text-[#b8bcb4]"}`}>
                            {step.label}
                          </span>
                        </div>
                        {i < STEPS.length - 1 && (
                          <div className={`mx-2 h-px flex-1 ${done ? "bg-[#3f7d53]" : "bg-[#eceae3]"}`} />
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-start gap-2.5 rounded-sm border border-[#e4c9c2] bg-[#fbf3f1] px-3 py-2.5">
                  <svg
                    className="mt-0.5 shrink-0 text-[#b1493c]"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 8v5M12 16h.01" strokeLinecap="round" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-[#8a3428]">Comparison failed</p>
                    {error && <p className="mt-0.5 text-sm text-[#8a3428]/80">{error}</p>}
                  </div>
                </div>
              )}

              {status === "completed" && revisionId && (
                <div className="mt-4 flex items-center justify-between rounded-sm bg-[#f0f5f2] border border-[#c9dfd0] px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-[#2f6b46]">Comparison ready</p>
                    <p className="font-mono text-[11px] text-[#5b6159] mt-0.5">REV {revisionId}</p>
                  </div>
                  <button
                    type="button"
                    className="text-sm font-medium text-[#2a5c7a] hover:underline"
                    onClick={() => {
                      window.location.href = `/revisions/${revisionId}`;
                    }}
                  >
                    View results →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}