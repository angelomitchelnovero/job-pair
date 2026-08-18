"use client";

import type { MatchResponse } from "@/types/api";
import {
  Check,
  AlertTriangle,
  Info,
  Lightbulb,
  TrendingUp,
  Minus,
} from "lucide-react";

// Human-readable label + direction for the engineered features the matching
// engine reports in `feature_breakdown`. Backend emits raw key names
// (tfidf_cosine, jaccard_skills, …) so we translate them here for the UI.
const FEATURE_META: Record<
  string,
  { label: string; positive: string; negative: string }
> = {
  tfidf_cosine: {
    label: "TF-IDF text similarity",
    positive: "Resume wording overlaps JD wording",
    negative: "Resume wording diverges from JD",
  },
  jaccard_skills: {
    label: "Skill overlap (Jaccard)",
    positive: "Strong overlap of skill vocabularies",
    negative: "Different skill vocabulary",
  },
  jd_coverage: {
    label: "Required-skill coverage",
    positive: "Most required skills are in the resume",
    negative: "Few required skills are in the resume",
  },
  matching_skill_count: {
    label: "Matched required skills",
    positive: "Many required skills present",
    negative: "Few required skills present",
  },
  missing_skill_count: {
    label: "Missing required skills",
    positive: "Few or no missing required skills",
    negative: "Several required skills missing",
  },
  years_gap: {
    label: "Years of experience gap",
    positive: "Meets or exceeds required years",
    negative: "Short of required years",
  },
  education_alignment: {
    label: "Education alignment",
    positive: "Required degree is present",
    negative: "Required degree missing",
  },
};

function featureLabel(key: string): string {
  return FEATURE_META[key]?.label ?? key;
}

function featureHint(key: string, contribution: number): string {
  const meta = FEATURE_META[key];
  if (!meta) return "";
  // Treat anything clearly above 0 as positive, anything below 0 as negative.
  if (contribution > 0.05) return meta.positive;
  if (contribution < -0.05) return meta.negative;
  return "Neutral";
}

export function Match({ result }: { result: MatchResponse }) {
  const topMissing = result.missing_skills.slice(0, 3);
  const breakdown = result.feature_breakdown ?? [];

  return (
    <div className="space-y-4">
      {/* High-visibility CTA: the top 3 missing skills. Job hunters care
          about this most — show it first, not buried in prose. */}
      {topMissing.length > 0 && (
        <div className="card p-4 border-orange-200 bg-orange-50">
          <h3 className="font-semibold flex items-center gap-2 text-orange-800">
            <Lightbulb className="w-4 h-4" /> Top skills to add
          </h3>
          <p className="text-xs text-orange-700 mt-1">
            Adding these required skills will lift your score the most.
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {topMissing.map((s) => (
              <li
                key={s.name}
                className="inline-flex items-center gap-1.5 rounded-full bg-white border border-orange-300 px-3 py-1 text-sm font-medium text-orange-900"
              >
                <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />
                {s.name}
              </li>
            ))}
          </ul>
          {result.recommendations[0] && (
            <p className="text-xs text-gray-700 mt-3 italic">
              {result.recommendations[0]}
            </p>
          )}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <SkillList
          title="Matching skills"
          variant="success"
          items={result.matching_skills.map((s) => ({
            name: s.name,
            tag: typeof s.matched === "string" ? s.matched : undefined,
          }))}
        />
        <SkillList
          title="Missing required skills"
          variant="warning"
          items={result.missing_skills.map((s) => ({ name: s.name }))}
        />
      </div>

      <div className="card p-4">
        <h3 className="font-semibold flex items-center gap-2">
          <Info className="w-4 h-4 text-brand-600" /> Experience & education
        </h3>
        <div className="grid sm:grid-cols-2 gap-4 mt-3 text-sm">
          <div>
            <div className="text-gray-500 text-xs uppercase tracking-wide">
              Experience
            </div>
            <p className="mt-1">{result.experience_alignment?.notes ?? "—"}</p>
          </div>
          <div>
            <div className="text-gray-500 text-xs uppercase tracking-wide">
              Education
            </div>
            <p className="mt-1">{result.education_alignment?.notes ?? "—"}</p>
          </div>
        </div>
      </div>

      {/* Render feature contributions in two visual buckets so the user
          can see what helped vs what hurt at a glance. The backend returns
          a flat dict; we sort by sign here. */}
      {breakdown.length > 0 && (
        <div className="card p-4">
          <h3 className="font-semibold">Why this score?</h3>
          <p className="text-sm text-gray-600 mt-1">
            Each row is a feature the matching engine looked at. Positive
            contributions helped the score; negative ones pulled it down.
          </p>
          <div className="mt-3 grid sm:grid-cols-2 gap-4">
            <FeatureBucket
              title="Helped"
              icon={<TrendingUp className="w-3.5 h-3.5 text-green-600" />}
              entries={breakdown
                .filter((f) => Number(f.contribution) > 0.001)
                .map((f) => ({
                  feature: f.feature,
                  contribution: Number(f.contribution),
                }))}
              tone="positive"
            />
            <FeatureBucket
              title="Hurt / neutral"
              icon={<Minus className="w-3.5 h-3.5 text-gray-500" />}
              entries={breakdown
                .filter((f) => Number(f.contribution) <= 0.001)
                .map((f) => ({
                  feature: f.feature,
                  contribution: Number(f.contribution),
                }))}
              tone="negative"
            />
          </div>
        </div>
      )}

      {/* Skip the first recommendation — we surfaced it above the missing
          skills as the "what to do next" CTA. */}
      {result.recommendations.length > 1 && (
        <div className="card p-4">
          <h3 className="font-semibold">Other recommendations</h3>
          <ul className="mt-2 space-y-1 list-disc list-inside text-sm text-gray-700">
            {result.recommendations.slice(1).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SkillList({
  title,
  items,
  variant,
}: {
  title: string;
  items: Array<{ name: string; tag?: string }>;
  variant: "success" | "warning";
}) {
  const border =
    variant === "success"
      ? "border-green-200 bg-green-50"
      : "border-orange-200 bg-orange-50";
  const icon =
    variant === "success" ? (
      <Check className="w-4 h-4 text-green-700" />
    ) : (
      <AlertTriangle className="w-4 h-4 text-orange-700" />
    );
  const headingColor =
    variant === "success" ? "text-green-700" : "text-orange-700";

  return (
    <div className={`rounded-xl border p-4 ${border}`}>
      <h3
        className={`text-sm font-semibold ${headingColor} flex items-center gap-2`}
      >
        {icon} {title}
      </h3>
      {items.length === 0 ? (
        <p className="text-sm text-gray-500 mt-2">None.</p>
      ) : (
        <ul className="mt-2 grid grid-cols-2 gap-1.5 text-sm">
          {items.map((it, i) => (
            <li
              key={`${it.name}-${i}`}
              className="flex items-center gap-2 bg-white/70 rounded px-2 py-1 border border-gray-200"
            >
              {variant === "success" ? (
                <Check className="w-3.5 h-3.5 text-green-600" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />
              )}
              <span>{it.name}</span>
              {it.tag && (
                <span className="ml-auto text-[10px] uppercase text-gray-500">
                  {it.tag}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FeatureBucket({
  title,
  icon,
  entries,
  tone,
}: {
  title: string;
  icon: React.ReactNode;
  entries: Array<{ feature: string; contribution: number }>;
  tone: "positive" | "negative";
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-gray-500 flex items-center gap-1.5">
        {icon} {title}
      </div>
      {entries.length === 0 ? (
        <p className="text-xs text-gray-400 mt-2">Nothing in this bucket.</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {entries
            .sort((a, b) =>
              tone === "positive"
                ? Math.abs(b.contribution) - Math.abs(a.contribution)
                : a.contribution - b.contribution
            )
            .map((e) => (
              <li
                key={e.feature}
                title={featureHint(e.feature, e.contribution)}
                className="text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-gray-700">{featureLabel(e.feature)}</span>
                  <span
                    className={`font-mono ${
                      e.contribution > 0 ? "text-green-700" : "text-gray-500"
                    }`}
                  >
                    {e.contribution > 0 ? "+" : ""}
                    {e.contribution.toFixed(3)}
                  </span>
                </div>
                <div className="h-1 bg-gray-100 rounded-full mt-1 overflow-hidden">
                  <div
                    className={`h-full ${
                      tone === "positive" ? "bg-green-500" : "bg-gray-400"
                    }`}
                    style={{
                      width: `${Math.min(
                        100,
                        Math.abs(e.contribution) * 200
                      )}%`,
                    }}
                  />
                </div>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}