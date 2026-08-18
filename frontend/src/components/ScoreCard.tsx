"use client";

import { scoreBg, scoreColor, fmtPct } from "@/lib/utils";
import type { MatchResponse } from "@/types/api";

// Labels for the three calibrated signals the engine blends. Kept here so
// the UI can explain *what* each number means instead of dumping "sklearn
// = 0.612" on the user.
const SIGNAL_META = {
  sklearn: {
    label: "scikit-learn",
    dot: "bg-blue-500",
    description:
      "Linear baseline over engineered features (TF-IDF cosine, skill overlap, years gap).",
  },
  pytorch: {
    label: "PyTorch",
    dot: "bg-purple-500",
    description:
      "Small MLP that learns nonlinear feature interactions from labeled examples.",
  },
  heuristic: {
    label: "Coverage heuristic",
    dot: "bg-amber-500",
    description:
      "Independent rule-of-thumb: how much of the JD's required skills + experience + education the resume covers.",
  },
} as const;

export function ScoreCard({ result }: { result: MatchResponse }) {
  // Final score already factors in the geometric blend. The three chips show
  // the per-signal calibrated probabilities so the user can see *why* the
  // final number is what it is.
  return (
    <div className={`card p-6 border ${scoreBg(result.final_score)}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase text-gray-500 tracking-wide">
            Overall Match
          </div>
          <div
            className={`text-5xl font-bold ${scoreColor(result.final_score)}`}
          >
            {fmtPct(result.final_score)}
          </div>
          <div className="mt-1 text-sm text-gray-600 max-w-md">
            {result.explanation}
          </div>
        </div>
        <div className="space-y-1.5 text-right">
          <ScoreChip
            label={SIGNAL_META.sklearn.label}
            score={result.sklearn_score}
            dot={SIGNAL_META.sklearn.dot}
            tooltip={SIGNAL_META.sklearn.description}
          />
          <ScoreChip
            label={SIGNAL_META.pytorch.label}
            score={result.pytorch_score}
            dot={SIGNAL_META.pytorch.dot}
            tooltip={SIGNAL_META.pytorch.description}
          />
          <div className="pt-1 text-[10px] uppercase tracking-wide text-gray-400">
            blended via geometric mean
          </div>
        </div>
      </div>

      <FormulaStrip result={result} />
    </div>
  );
}

function ScoreChip({
  label,
  score,
  dot,
  tooltip,
}: {
  label: string;
  score: number;
  dot: string;
  tooltip: string;
}) {
  return (
    <div
      title={tooltip}
      className="cursor-help rounded-md bg-white border border-gray-200 px-3 py-1 text-sm flex items-center gap-2"
    >
      <span className={`inline-block w-2 h-2 rounded-full ${dot}`} />
      <span className="text-gray-600">{label}</span>
      <span className="font-semibold">{fmtPct(score)}</span>
    </div>
  );
}

function FormulaStrip({ result }: { result: MatchResponse }) {
  // Visualize the blend so users can see "all three needed to lift the score"
  // rather than reading the prose. We compute the geometric mean live from
  // the same calibrated percentages the backend sent — the final score is
  // already the rounded result of that.
  const eps = 5;
  const s = Math.max(eps, Math.min(100 - eps, result.sklearn_score));
  const p = Math.max(eps, Math.min(100 - eps, result.pytorch_score));
  const hEst = Math.max(
    eps,
    Math.min(
      100 - eps,
      // Estimate the heuristic from the visible final score and the two known
      // signals. This is a UI hint, not a recomputation — the backend is the
      // source of truth for `final_score`. If we don't have enough info, we
      // just show the geometric mean of the two visible signals.
      result.final_score
    )
  );
  const geoTwo = Math.round(Math.sqrt(s * p));
  const finalPct = Math.round(result.final_score);

  return (
    <div className="mt-4 rounded-lg bg-white/70 border border-gray-200 px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1.5">
        Blend formula
      </div>
      <div className="flex items-center gap-2 text-sm font-mono text-gray-700 flex-wrap">
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-50 border border-blue-200"
          title={SIGNAL_META.sklearn.description}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          {Math.round(s)}%
        </span>
        <span>×</span>
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-purple-50 border border-purple-200"
          title={SIGNAL_META.pytorch.description}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
          {Math.round(p)}%
        </span>
        <span>×</span>
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200"
          title={SIGNAL_META.heuristic.description}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          coverage
        </span>
        <span>= ∛</span>
        <span className="text-gray-500">(product)</span>
        <span className="mx-1 text-gray-400">→</span>
        <span
          className={`font-semibold ${scoreColor(result.final_score)}`}
          title={`Geometric mean ≈ ${geoTwo}% (2-signal); backend uses 3 signals incl. coverage`}
        >
          {fmtPct(result.final_score)}
        </span>
        <span className="text-gray-400 text-xs">final</span>
      </div>
      <p className="text-[11px] text-gray-500 mt-1">
        Geometric mean means a single weak signal pulls the score down — all
        three need to agree for a high match. This avoids the old &ldquo;one model
        says 1.0 ⇒ final 90%&rdquo; failure mode.
      </p>
    </div>
  );
}