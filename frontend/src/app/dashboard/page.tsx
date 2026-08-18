import { api } from "@/lib/api";
import { formatDate, fmtPct, scoreColor } from "@/lib/utils";
import type { MatchResponse } from "@/types/api";
import Link from "next/link";
import { Upload, FileText, Briefcase, BarChart3, Activity } from "lucide-react";

export default async function DashboardPage() {
  const [resumes, jobs, matches, perf] = await Promise.allSettled([
    api.listResumes() as Promise<Array<{ id: string; filename: string; skills: string[]; created_at: string }>>,
    api.listJobs() as Promise<Array<{ id: string; title: string; created_at: string }>>,
    api.listMatches() as Promise<MatchResponse[]>,
    api.modelPerformance() as Promise<Array<{ metrics: Record<string, number> }>>,
  ]);

  const resumesCount = resumes.status === "fulfilled" ? resumes.value.length : 0;
  const jobsCount = jobs.status === "fulfilled" ? jobs.value.length : 0;
  const matchesCount = matches.status === "fulfilled" ? matches.value.length : 0;
  const recentMatches =
    matches.status === "fulfilled"
      ? (matches.value.slice(0, 5) as MatchResponse[])
      : [];
  const avgScore =
    recentMatches.length > 0
      ? Math.round(recentMatches.reduce((a, b) => a + b.final_score, 0) / recentMatches.length)
      : 0;
  const liveMetrics =
    perf.status === "fulfilled" && perf.value[0]?.metrics ? perf.value[0].metrics : null;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Resumes" value={resumesCount} icon={<Upload className="w-4 h-4" />} />
        <Stat label="Jobs" value={jobsCount} icon={<Briefcase className="w-4 h-4" />} />
        <Stat label="Matches" value={matchesCount} icon={<FileText className="w-4 h-4" />} />
        <Stat
          label="Avg score (recent)"
          value={`${avgScore}%`}
          icon={<BarChart3 className="w-4 h-4" />}
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Recent matches</h2>
            <Link className="text-brand-600 text-sm" href="/history">
              View all →
            </Link>
          </div>
          {recentMatches.length === 0 ? (
            <p className="text-sm text-gray-500">
              No matches yet. Run one on the{" "}
              <Link className="text-brand-600" href="/analyze">
                Analyze
              </Link>{" "}
              page.
            </p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {recentMatches.map((m) => (
                <li
                  key={m.id}
                  className="py-3 flex items-center justify-between gap-3"
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
                  <span
                    className={`font-semibold shrink-0 ${scoreColor(m.final_score)}`}
                  >
                    {fmtPct(m.final_score)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-brand-600" />
            <h2 className="font-semibold">Model snapshot</h2>
          </div>
          {liveMetrics ? (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {Object.entries(liveMetrics)
                .slice(0, 8)
                .map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-gray-50 px-3 py-2">
                    <dt className="text-gray-500 text-xs uppercase tracking-wide">{k}</dt>
                    <dd className="font-mono">{typeof v === "number" ? v.toFixed(3) : String(v)}</dd>
                  </div>
                ))}
            </dl>
          ) : (
            <p className="text-sm text-gray-500">Models not loaded yet.</p>
          )}
          <Link
            href="/model-performance"
            className="text-brand-600 text-sm mt-3 inline-block"
          >
            Full performance →
          </Link>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wide">
        {icon}
        {label}
      </div>
      <div className="text-2xl font-bold mt-2">{value}</div>
    </div>
  );
}
