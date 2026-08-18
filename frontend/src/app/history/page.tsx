"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { scoreColor, formatDate, fmtPct } from "@/lib/utils";
import type { MatchResponse } from "@/types/api";
import { Match } from "@/components/Match";
import { ScoreCard } from "@/components/ScoreCard";
import { ConfirmPopover } from "@/components/ConfirmPopover";
import {
  History as HistoryIcon,
  Briefcase,
  FileText,
  Trash2,
} from "lucide-react";

const JD_PREVIEW_CHARS = 120;

export default function HistoryPage() {
  const [matches, setMatches] = useState<MatchResponse[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    api
      .listMatches()
      .then((data) => {
        setMatches(data as MatchResponse[]);
        if (data[0]) setSelected((data[0] as MatchResponse).id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDeleteMatch(id: string) {
    setDeletingId(id);
    try {
      await api.deleteMatch(id);
      // Remove from local state. If the deleted match was selected,
      // fall back to the first remaining match (or null if list empty).
      setMatches((prev) => {
        const next = prev.filter((m) => m.id !== id);
        if (selected === id) setSelected(next[0]?.id ?? null);
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeletingId(null);
    }
  }

  const selectedMatch = matches.find((m) => m.id === selected);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <HistoryIcon className="w-5 h-5 text-brand-600" />
        <h1 className="text-2xl font-bold">Analysis history</h1>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && matches.length === 0 && (
        <div className="card p-10 text-center text-gray-500">
          No matches yet. Run one from the{" "}
          <a className="text-brand-600" href="/analyze">
            Analyze
          </a>{" "}
          page.
        </div>
      )}

      {matches.length > 0 && (
        <div className="grid lg:grid-cols-[280px_1fr] gap-6">
          <div className="card p-3 max-h-[60vh] overflow-auto">
            <ul className="divide-y divide-gray-100">
              {matches.map((m) => (
                <li key={m.id}>
                  <button
                    onClick={() => setSelected(m.id)}
                    className={`w-full text-left px-3 py-3 rounded-lg flex items-center justify-between gap-2 ${
                      selected === m.id ? "bg-brand-50" : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-gray-900 truncate">
                        {m.job_title ?? "Untitled role"}
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {m.job_company ?? "—"}
                      </div>
                      <div className="text-[11px] text-gray-400 mt-0.5">
                        {formatDate(m.created_at)}
                      </div>
                    </div>
                    <span className="flex items-center gap-1 shrink-0">
                      <span
                        className={`font-semibold ${scoreColor(m.final_score)}`}
                      >
                        {fmtPct(m.final_score)}
                      </span>
                      {/* Trash lives outside the selection button — wrapping
                          its own click target in a stopPropagation-safe
                          ConfirmPopover trigger means clicks on it don't
                          also fire the row's select handler. */}
                      <ConfirmPopover
                        trigger={(open) => (
                          <span
                            role="button"
                            tabIndex={0}
                            onClick={(e) => {
                              e.stopPropagation();
                              open();
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                e.stopPropagation();
                                open();
                              }
                            }}
                            title="Delete match"
                            className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </span>
                        )}
                        title="Delete this match?"
                        body="The match record (scores, breakdown, recommendations) will be removed from your history. This cannot be undone."
                        onConfirm={() => handleDeleteMatch(m.id)}
                        busy={deletingId === m.id}
                      />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-4">
            {selectedMatch ? (
              <>
                <ContextCard match={selectedMatch} />
                <ScoreCard result={selectedMatch} />
                <Match result={selectedMatch} />
              </>
            ) : (
              <div className="card p-10 text-center text-gray-500">
                Select a match from the left.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact card showing the role/company/resume/JD context that produced
 * this match. Sits above the ScoreCard so the user always sees "what was
 * I scoring against?" before the numbers. No buttons — pure context.
 */
function ContextCard({ match }: { match: MatchResponse }) {
  const jdPreview = match.job_description
    ? match.job_description.length > JD_PREVIEW_CHARS
      ? match.job_description.slice(0, JD_PREVIEW_CHARS).trimEnd() + "…"
      : match.job_description
    : null;

  return (
    <div className="card p-4">
      <div className="flex items-start gap-3">
        <Briefcase className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-gray-900 truncate">
            {match.job_title ?? "Untitled role"}
          </div>
          <div className="text-sm text-gray-500 truncate">
            {match.job_company ?? "—"}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-sm text-gray-700 min-w-0">
            <FileText className="w-4 h-4 text-gray-500 shrink-0" />
            <span
              className={`truncate ${
                match.resume_id ? "" : "italic text-gray-400"
              }`}
            >
              {match.resume_filename ?? "Resume deleted"}
            </span>
          </div>
          {jdPreview && (
            <p className="mt-2 text-xs text-gray-500 line-clamp-2">
              {jdPreview}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
