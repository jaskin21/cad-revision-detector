"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

type ChangeType = "added" | "removed" | "modified";

type Change = {
  type: ChangeType;
  entity: string;
  layer: string | null;
  location: { x: number; y: number } | null;
  location_label?: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
};

type Revision = {
  id: string;
  project_id: string;
  status: string;
  confidence: string | null;
  changes: Change[] | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};

const TYPE_STYLE: Record<ChangeType, { border: string; dot: string; text: string; label: string }> = {
  added: { border: "border-l-[#3f7d53]", dot: "bg-[#3f7d53]", text: "text-[#2f6b46]", label: "Added" },
  removed: { border: "border-l-[#b1493c]", dot: "bg-[#b1493c]", text: "text-[#8a3428]", label: "Removed" },
  modified: { border: "border-l-[#b4842a]", dot: "bg-[#b4842a]", text: "text-[#8a611f]", label: "Modified" },
};

const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  queued: { bg: "bg-[#eceae3]", text: "text-[#5b6159]", label: "Queued" },
  processing: { bg: "bg-[#e4edf1]", text: "text-[#2a5c7a]", label: "Processing" },
  completed: { bg: "bg-[#e9f3ec]", text: "text-[#2f6b46]", label: "Completed" },
  failed: { bg: "bg-[#fbf3f1]", text: "text-[#8a3428]", label: "Failed" },
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? { bg: "bg-[#eceae3]", text: "text-[#5b6159]", label: status };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

function RawDataToggle({ change }: { change: Change }) {
  const [showRaw, setShowRaw] = useState(false);
  return (
    <div className="col-span-full border-t border-[#d8dbd6] bg-white p-3">
      <button
        type="button"
        onClick={() => setShowRaw((v) => !v)}
        className="text-[11px] font-medium text-[#8a8f88] hover:text-[#5b6159]"
      >
        {showRaw ? "Hide" : "Show"} technical details
      </button>
      {showRaw && (
        <div className="mt-2 grid grid-cols-1 gap-px bg-[#d8dbd6] sm:grid-cols-2">
          <pre className="bg-[#fbf3f1] p-2 overflow-auto font-mono text-[10px] leading-relaxed text-[#1c2024]">
            {change.before ? JSON.stringify(change.before, null, 2) : "—"}
          </pre>
          <pre className="bg-[#eef6f0] p-2 overflow-auto font-mono text-[10px] leading-relaxed text-[#1c2024]">
            {change.after ? JSON.stringify(change.after, null, 2) : "—"}
          </pre>
        </div>
      )}
    </div>
  );
}

function ChangeCard({ change }: { change: Change }) {
  const [open, setOpen] = useState(false);
  const style = TYPE_STYLE[change.type];
  const hasRaw = change.before || change.after;
  const beforeCrop = (change.before as Record<string, unknown> | null)?.crop as string | undefined;
  const afterCrop = (change.after as Record<string, unknown> | null)?.crop as string | undefined;

  return (
    <li className={`rounded-sm border border-[#d8dbd6] border-l-4 ${style.border} bg-white`}>
      <div className="p-3.5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${style.dot}`} />
              <span className={`font-mono text-[11px] uppercase tracking-wide ${style.text}`}>{style.label}</span>
            </div>
            <p className="mt-1 truncate text-sm text-[#1c2024]" title={change.entity}>
              {change.entity}
            </p>
            {change.layer && (
              <p className="mt-0.5 font-mono text-[11px] text-[#8a8f88]">layer · {change.layer}</p>
            )}
            {change.location_label && (
              <p className="mt-0.5 text-[11px] text-[#5b6159]">📍 {change.location_label}</p>
            )}
          </div>
          {change.location && (
            <p className="shrink-0 font-mono text-[11px] text-[#8a8f88] tabular-nums">
              x {change.location.x.toFixed(2)}
              <br />
              y {change.location.y.toFixed(2)}
            </p>
          )}
        </div>

        {hasRaw && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="mt-2.5 flex items-center gap-1 text-[11px] font-medium text-[#5b6159] hover:text-[#1c2024]"
            aria-expanded={open}
          >
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              className={`transition-transform ${open ? "rotate-90" : ""}`}
            >
              <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Details
          </button>
        )}
      </div>

      {open && hasRaw && (
        <div className="grid grid-cols-1 gap-px border-t border-[#d8dbd6] bg-[#d8dbd6] sm:grid-cols-2">
          <div className="bg-[#fbf3f1] p-3">
            <p className="font-mono text-[10px] uppercase tracking-wide text-[#8a3428]">Before</p>
            {beforeCrop ? (
              <img
                src={beforeCrop}
                alt="Before"
                className="mt-2 w-full rounded-sm border border-[#e4c9c2]"
              />
            ) : (
              <p className="mt-2 text-xs text-[#8a8f88]">No image available</p>
            )}
          </div>
          <div className="bg-[#eef6f0] p-3">
            <p className="font-mono text-[10px] uppercase tracking-wide text-[#2f6b46]">After</p>
            {afterCrop ? (
              <img
                src={afterCrop}
                alt="After"
                className="mt-2 w-full rounded-sm border border-[#c9dfd0]"
              />
            ) : (
              <p className="mt-2 text-xs text-[#8a8f88]">No image available</p>
            )}
          </div>

          <RawDataToggle change={change} />
        </div>
      )}
    </li>
  );
}

export default function RevisionResultsPage() {
  const params = useParams();
  const id = params.id as string;

  const [revision, setRevision] = useState<Revision | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | ChangeType>("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/revisions/${id}`)
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled) {
          setRevision(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const counts = useMemo(() => {
    const base = { added: 0, removed: 0, modified: 0 };
    revision?.changes?.forEach((c) => {
      base[c.type] += 1;
    });
    return base;
  }, [revision]);

  const displayChanges = useMemo(() => {
    const all = revision?.changes ?? [];
    return all.filter((c) => {
      if (filter !== "all" && c.type !== filter) return false;
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        const hay = `${c.entity} ${c.layer ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [revision, filter, query]);

  if (loading) {
    return (
      <main className="min-h-screen bg-[#f6f5f1] px-4 py-10">
        <div className="mx-auto max-w-[720px]">
          <div className="animate-pulse space-y-3">
            <div className="h-6 w-48 rounded-sm bg-[#eceae3]" />
            <div className="h-4 w-72 rounded-sm bg-[#eceae3]" />
            <div className="mt-6 h-24 rounded-sm bg-[#eceae3]" />
            <div className="h-16 rounded-sm bg-[#eceae3]" />
            <div className="h-16 rounded-sm bg-[#eceae3]" />
          </div>
        </div>
      </main>
    );
  }

  if (!revision) {
    return (
      <main className="min-h-screen bg-[#f6f5f1] px-4 py-10">
        <div className="mx-auto max-w-[720px] rounded-sm border border-[#d8dbd6] bg-white p-6 text-center">
          <p className="text-sm text-[#5b6159]">No revision found for this ID.</p>
        </div>
      </main>
    );
  }

  const total = revision.changes?.length ?? 0;

  return (
    <main className="min-h-screen bg-[#f6f5f1] px-4 py-10 text-[#1c2024]">
      <div className="mx-auto w-full max-w-[720px]">
        {/* Header / title block */}
        <div className="rounded-sm border border-[#d8dbd6] bg-white p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-wide text-[#8a8f88]">Rev {revision.id}</p>
              <h1 className="mt-0.5 text-[22px] font-semibold tracking-tight">{revision.project_id}</h1>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={revision.status} />
              <Link
                href="/"
                className="rounded-full border border-[#d8dbd6] bg-white px-3 py-1 text-xs font-medium text-[#5b6159] hover:border-[#b8bcb4]"
              >
                + New comparison
              </Link>
            </div>
          </div>

          <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-[#eceae3] pt-4 sm:grid-cols-4">
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-wide text-[#8a8f88]">Confidence</dt>
              <dd className="mt-0.5 text-sm text-[#1c2024]">{revision.confidence ?? "—"}</dd>
            </div>
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-wide text-[#8a8f88]">Started</dt>
              <dd className="mt-0.5 text-sm text-[#1c2024]">{formatDate(revision.created_at)}</dd>
            </div>
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-wide text-[#8a8f88]">Completed</dt>
              <dd className="mt-0.5 text-sm text-[#1c2024]">{formatDate(revision.completed_at)}</dd>
            </div>
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-wide text-[#8a8f88]">Changes</dt>
              <dd className="mt-0.5 text-sm text-[#1c2024]">{total}</dd>
            </div>
          </dl>

          {revision.status === "failed" && revision.error && (
            <div className="mt-4 flex items-start gap-2.5 rounded-sm border border-[#e4c9c2] bg-[#fbf3f1] px-3 py-2.5">
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
                <p className="mt-0.5 text-sm text-[#8a3428]/80">{revision.error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Changes */}
        {revision.changes && (
          <div className="mt-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-[#1c2024]">Changes ({total})</h2>

              {total > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  {(["all", "added", "removed", "modified"] as const).map((key) => {
                    const active = filter === key;
                    const count = key === "all" ? total : counts[key];
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setFilter(key)}
                        className={[
                          "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                          active
                            ? "border-[#2a5c7a] bg-[#2a5c7a] text-white"
                            : "border-[#d8dbd6] bg-white text-[#5b6159] hover:border-[#b8bcb4]",
                        ].join(" ")}
                      >
                        {key === "all" ? "All" : TYPE_STYLE[key].label} · {count}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {total > 0 && (
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by entity or layer…"
                className="mt-3 w-full rounded-sm border border-[#d8dbd6] bg-white px-3 py-2 text-sm text-[#1c2024] placeholder:text-[#b8bcb4] outline-none focus:border-[#2a5c7a] focus:ring-1 focus:ring-[#2a5c7a]"
              />
            )}

            <div className="mt-4">
              {total === 0 ? (
                <div className="rounded-sm border border-dashed border-[#d8dbd6] bg-white p-8 text-center">
                  <p className="text-sm text-[#5b6159]">No changes detected between the two revisions.</p>
                </div>
              ) : displayChanges.length === 0 ? (
                <div className="rounded-sm border border-dashed border-[#d8dbd6] bg-white p-8 text-center">
                  <p className="text-sm text-[#5b6159]">No changes match this filter.</p>
                </div>
              ) : (
                <ul className="flex flex-col gap-2.5">
                  {displayChanges.map((change, i) => (
                    <ChangeCard key={i} change={change} />
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}