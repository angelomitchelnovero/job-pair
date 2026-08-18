import { api } from "@/lib/api";
import type { ModelPerformanceResponse } from "@/types/api";
import { BarChart3 } from "lucide-react";
import { fmtMetric } from "@/lib/utils";

export default async function ModelPerformancePage() {
  let data: ModelPerformanceResponse[] = [];
  let fetchError: string | null = null;
  try {
    data = (await api.modelPerformance()) as ModelPerformanceResponse[];
  } catch (e) {
    fetchError = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-5 h-5 text-brand-600" />
        <h1 className="text-2xl font-bold">Model performance</h1>
      </div>
      <p className="text-gray-600 max-w-3xl">
        Live evaluation snapshots from the loaded scikit-learn baseline and PyTorch matcher.
        We compute a representative set of metrics against a synthetic-but-deterministic
        labeled dataset, then expose them for monitoring. Numbers below are produced from
        the actual models — not hard-coded.
      </p>

      {fetchError && (
        <div className="card p-4 border-red-200 bg-red-50 text-sm text-red-700">
          Could not load metrics: {fetchError}
        </div>
      )}

      {data.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          No performance snapshots yet. Run{" "}
          <code className="bg-gray-100 px-1">make ml</code> to train and refresh.
        </div>
      ) : (
        data.map((d) => (
          <div key={d.id} className="card p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm uppercase tracking-wide text-gray-500">{d.model_name}</div>
                <div className="text-xs text-gray-400">{d.version}</div>
              </div>
              <div className="text-right text-sm">
                <div className="text-gray-500">Training samples</div>
                <div className="font-bold">{d.training_samples}</div>
              </div>
            </div>
            {d.notes && <p className="text-sm text-gray-500 mt-2">{d.notes}</p>}
            <dl className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-4">
              {Object.entries(d.metrics).map(([k, v]) => (
                <div key={k} className="rounded-lg bg-gray-50 px-3 py-2 border border-gray-100">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">{k}</dt>
                  <dd className="font-mono">{fmtMetric(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))
      )}

      <div className="card p-5">
        <h2 className="font-semibold">Approach</h2>
        <ul className="text-sm text-gray-700 mt-2 space-y-2 list-disc list-inside">
          <li>
            <b>scikit-learn baseline</b> — TF-IDF + cosine similarity over the resume/JD pair
            with a Ridge regression head and LogisticRegression classifier head, both trained
            over 15 engineered features.
          </li>
          <li>
            <b>PyTorch matcher</b> — a small MLP consuming the same 15-dimensional feature
            vector. Trained with BCE loss on synthetic labels, validated by holdout.
          </li>
          <li>
            <b>Final score</b> — equal-weighted blend (50/50) of both model scores. The UI
            shows both heads so you can compare them.
          </li>
          <li>
            <b>Training data</b> — synthetic, deterministic, generated from a curated skill
            taxonomy. Documented as replaceable with a real labeled dataset.
          </li>
        </ul>
      </div>
    </div>
  );
}
