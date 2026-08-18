"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ScoreCard } from "@/components/ScoreCard";
import { Match } from "@/components/Match";
import { ConfirmPopover } from "@/components/ConfirmPopover";
import { Upload, Sparkles, Trash2, AlertTriangle } from "lucide-react";
import type { JobResponse, MatchResponse, ResumeResponse } from "@/types/api";

// Count saved matches per resume_id so the inline delete confirm can
// tell the user how many matches will also be cascade-deleted.
function countMatchesByResume(matches: MatchResponse[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const m of matches) {
    if (m.resume_id) counts[m.resume_id] = (counts[m.resume_id] ?? 0) + 1;
  }
  return counts;
}

export default function AnalyzePage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeResponse[]>([]);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [resumeMode, setResumeMode] = useState<"upload" | "paste" | "existing">("upload");
  const [jobMode, setJobMode] = useState<"paste" | "existing">("paste");

  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [resumeId, setResumeId] = useState("");

  const [jobText, setJobText] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [jobCompany, setJobCompany] = useState("");
  const [jobId, setJobId] = useState("");

  const [persisting, setPersisting] = useState(true);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Match counts per resume, used by the inline delete confirm.
  const [matchCounts, setMatchCounts] = useState<Record<string, number>>({});
  const [deletingResumeId, setDeletingResumeId] = useState<string | null>(null);

  useEffect(() => {
    api
      .listResumes()
      .then((data) => setResumes(data as ResumeResponse[]))
      .catch(() => undefined);
    api
      .listJobs()
      .then((data) => setJobs(data as JobResponse[]))
      .catch(() => undefined);
    // Fetch matches so we can show "Will delete N matches" in the confirm.
    api
      .listMatches()
      .then((data) =>
        setMatchCounts(countMatchesByResume(data as MatchResponse[]))
      )
      .catch(() => undefined);
  }, []);

  async function handleDeleteResume(id: string) {
    setDeletingResumeId(id);
    try {
      await api.deleteResume(id);
      // Remove from the picker; clear the selected id if it was the one
      // the user just deleted so the form falls back to "Select a resume".
      setResumes((prev) => prev.filter((r) => r.id !== id));
      if (resumeId === id) setResumeId("");
      // Refetch match counts — the cascade will have wiped them.
      const ms = (await api.listMatches()) as MatchResponse[];
      setMatchCounts(countMatchesByResume(ms));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeletingResumeId(null);
    }
  }

  const canSubmit = useMemo(() => {
    if (resumeMode === "existing" && !resumeId) return false;
    if (resumeMode === "upload" && !resumeFile) return false;
    if (resumeMode === "paste" && resumeText.trim().length < 20) return false;
    if (jobMode === "existing" && !jobId) return false;
    if (jobMode === "paste" && (jobText.trim().length < 20 || !jobTitle.trim())) return false;
    return true;
  }, [resumeMode, jobMode, resumeId, resumeFile, resumeText, jobId, jobText, jobTitle]);

  async function handleUploadResume(file: File): Promise<string> {
    const out = (await api.uploadResume(file)) as ResumeResponse;
    setResumes((prev) => [out, ...prev]);
    return out.id;
  }

  async function handleCreateJob(): Promise<string> {
    const payload = { title: jobTitle, company: jobCompany || null, description: jobText };
    const created = (await api.createJob(payload)) as JobResponse;
    setJobs((prev) => [created, ...prev]);
    return created.id;
  }

  async function handleSubmit() {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      // Determine final resume_id / job_id when persisting. For pasted
      // inputs we fall back to raw-text payloads so the backend can persist
      // them too — see backend /matches handler.
      const payload: Record<string, unknown> = {};
      if (persisting) {
        if (resumeMode === "upload" && resumeFile) {
          payload.resume_id = await handleUploadResume(resumeFile);
        } else if (resumeMode === "existing") {
          payload.resume_id = resumeId;
        } else if (resumeMode === "paste") {
          payload.resume_text = resumeText;
        }

        if (jobMode === "paste") {
          payload.job_text = jobText;
          payload.job_title = jobTitle;
          payload.job_company = jobCompany || null;
        } else {
          payload.job_id = jobId;
        }

        const res = (await api.createMatch(payload)) as MatchResponse;
        setResult(res);
        router.refresh();
      } else {
        // Preview mode — always use raw-text payload
        const resumeTextValue =
          resumeMode === "paste"
            ? resumeText
            : resumes.find((r) => r.id === resumeId)?.raw_text ?? "";
        const jobTextValue =
          jobMode === "paste"
            ? jobText
            : jobs.find((j) => j.id === jobId)?.description ?? "";
        const jobTitleValue =
          jobMode === "paste"
            ? jobTitle
            : jobs.find((j) => j.id === jobId)?.title ?? "";

        const res = (await api.previewMatch({
          resume_text: resumeTextValue,
          job_text: jobTextValue,
          job_title: jobTitleValue,
          job_company: jobMode === "paste" ? jobCompany || null : (jobs.find((j) => j.id === jobId)?.company ?? null),
        })) as MatchResponse;
        setResult(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div className="card p-5">
          <h2 className="font-semibold flex items-center gap-2">
            <Upload className="w-4 h-4 text-brand-600" /> Resume
          </h2>
          <div className="flex gap-2 mt-3 text-xs">
            {(["upload", "paste", "existing"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setResumeMode(m)}
                className={`px-3 py-1.5 rounded-lg border ${
                  resumeMode === m
                    ? "bg-brand-50 border-brand-300 text-brand-700"
                    : "border-gray-200 hover:bg-gray-50"
                }`}
              >
                {m === "upload" ? "Upload PDF" : m === "paste" ? "Paste Text" : "Pick Existing"}
              </button>
            ))}
          </div>

          {resumeMode === "upload" && (
            <input
              type="file"
              accept=".pdf"
              className="input mt-3"
              onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
            />
          )}
          {resumeMode === "paste" && (
            <textarea
              className="input mt-3 min-h-[180px] font-mono text-xs"
              placeholder="Paste resume text here..."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
            />
          )}
          {resumeMode === "existing" && (
            <div className="flex items-stretch gap-2 mt-3">
              <select
                className="input flex-1"
                value={resumeId}
                onChange={(e) => setResumeId(e.target.value)}
              >
                <option value="">Select a resume</option>
                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.filename}
                  </option>
                ))}
              </select>
              <ConfirmPopover
                trigger={(open) => (
                  <button
                    type="button"
                    onClick={open}
                    disabled={!resumeId || deletingResumeId === resumeId}
                    title={
                      resumeId
                        ? "Delete selected resume"
                        : "Select a resume first"
                    }
                    className="px-3 rounded-md border border-gray-200 text-gray-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:hover:text-gray-500 disabled:hover:bg-transparent"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                title="Delete this resume?"
                body={(() => {
                  const n = resumeId ? matchCounts[resumeId] ?? 0 : 0;
                  if (n === 0) {
                    return "This resume has no saved matches and can be safely removed.";
                  }
                  return (
                    <span className="flex items-start gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
                      <span>
                        <strong>
                          {n} saved match{n === 1 ? "" : "es"}
                        </strong>{" "}
                        reference this resume. They will keep existing;
                        the resume label will read &ldquo;Resume
                        deleted&rdquo; in history.
                      </span>
                    </span>
                  );
                })()}
                onConfirm={() => handleDeleteResume(resumeId)}
                busy={deletingResumeId === resumeId}
              />
            </div>
          )}
        </div>

        <div className="card p-5">
          <h2 className="font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-600" /> Job description
          </h2>
          <div className="flex gap-2 mt-3 text-xs">
            {(["paste", "existing"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setJobMode(m)}
                className={`px-3 py-1.5 rounded-lg border ${
                  jobMode === m
                    ? "bg-brand-50 border-brand-300 text-brand-700"
                    : "border-gray-200 hover:bg-gray-50"
                }`}
              >
                {m === "paste" ? "Paste Text" : "Pick Existing"}
              </button>
            ))}
          </div>

          {jobMode === "paste" ? (
            <div className="space-y-3 mt-3">
              <input
                className="input"
                placeholder="Role / Title"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
              />
              <input
                className="input"
                placeholder="Company (optional)"
                value={jobCompany}
                onChange={(e) => setJobCompany(e.target.value)}
              />
              <textarea
                className="input min-h-[180px] font-mono text-xs"
                placeholder="Paste the job description here..."
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
              />
            </div>
          ) : (
            <select
              className="input mt-3"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            >
              <option value="">Select a job</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="card p-5 flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={persisting}
              onChange={(e) => setPersisting(e.target.checked)}
              className="rounded"
            />
            Save this match to history
          </label>
          <button
            disabled={!canSubmit || loading}
            onClick={handleSubmit}
            className="btn-primary"
          >
            {loading ? "Analyzing..." : "Analyze match"}
          </button>
        </div>

        {error && <div className="card p-4 border-red-200 bg-red-50 text-sm text-red-700">{error}</div>}
      </div>

      <div>
        {result ? (
          <div className="space-y-4">
            <ScoreCard result={result} />
            <Match result={result} />
          </div>
        ) : (
          <div className="card p-10 text-center text-gray-500">
            <Sparkles className="w-6 h-6 text-brand-500 mx-auto" />
            <p className="mt-2 text-sm">Run an analysis to see the results here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
