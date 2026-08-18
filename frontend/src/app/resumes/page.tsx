"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ConfirmPopover } from "@/components/ConfirmPopover";
import type { MatchResponse, ResumeResponse } from "@/types/api";
import { FileText, Trash2, Files, AlertTriangle } from "lucide-react";

/**
 * Count saved matches per resume_id. Used by the delete confirmation so
 * users know how many matches will also be cascade-deleted.
 */
function countMatchesByResume(matches: MatchResponse[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const m of matches) {
    if (m.resume_id) counts[m.resume_id] = (counts[m.resume_id] ?? 0) + 1;
  }
  return counts;
}

export default function ResumesPage() {
  const [resumes, setResumes] = useState<ResumeResponse[]>([]);
  const [matchCounts, setMatchCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listResumes(), api.listMatches()])
      .then(([rs, ms]) => {
        setResumes(rs as ResumeResponse[]);
        setMatchCounts(countMatchesByResume(ms as MatchResponse[]));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const totalResumes = resumes.length;
  const totalSkills = useMemo(
    () => resumes.reduce((acc, r) => acc + (r.skills?.length ?? 0), 0),
    [resumes]
  );

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await api.deleteResume(id);
      // Remove the resume from local state and recompute match counts.
      setResumes((prev) => prev.filter((r) => r.id !== id));
      // After cascade-delete, refetch matches to keep counts honest.
      const ms = (await api.listMatches()) as MatchResponse[];
      setMatchCounts(countMatchesByResume(ms));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Files className="w-5 h-5 text-brand-600" />
        <h1 className="text-2xl font-bold">Resumes</h1>
        {totalResumes > 0 && (
          <span className="text-sm text-gray-500">
            {totalResumes} saved · {totalSkills} total skills
          </span>
        )}
      </div>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {!loading && resumes.length === 0 && (
        <div className="card p-10 text-center text-gray-500">
          <FileText className="w-6 h-6 text-brand-500 mx-auto" />
          <p className="mt-2 text-sm">
            No resumes yet. Upload one from the{" "}
            <a className="text-brand-600" href="/analyze">
              Analyze
            </a>{" "}
            page.
          </p>
        </div>
      )}

      {resumes.length > 0 && (
        <div className="card p-3">
          <ul className="divide-y divide-gray-100">
            {resumes.map((r) => {
              const matchCount = matchCounts[r.id] ?? 0;
              return (
                <li
                  key={r.id}
                  className="flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-gray-50"
                >
                  <FileText className="w-5 h-5 text-gray-500 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-gray-900 truncate">
                      {r.filename}
                    </div>
                    <div className="text-xs text-gray-500 truncate">
                      {(r.skills?.length ?? 0)} skills ·{" "}
                      {formatDate(r.created_at)}
                      {matchCount > 0 && (
                        <>
                          {" · "}
                          <span className="text-gray-600">
                            {matchCount} saved match
                            {matchCount === 1 ? "" : "es"}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <ConfirmPopover
                    trigger={(open) => (
                      <button
                        type="button"
                        onClick={open}
                        disabled={deletingId === r.id}
                        title="Delete resume"
                        className="p-2 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    title="Delete this resume?"
                    body={
                      matchCount === 0 ? (
                        "This resume has no saved matches and can be safely removed."
                      ) : (
                        <span className="flex items-start gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
                          <span>
                            <strong>
                              {matchCount} saved match
                              {matchCount === 1 ? "" : "es"}
                            </strong>{" "}
                            reference this resume. They will keep existing;
                            the resume label will read &ldquo;Resume
                            deleted&rdquo; in history.
                          </span>
                        </span>
                      )
                    }
                    onConfirm={() => handleDelete(r.id)}
                    busy={deletingId === r.id}
                  />
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}