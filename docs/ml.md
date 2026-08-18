# ML approach

We deliberately use **two independent models** for resume → JD matching so the
user sees not just a number, but a comparison between a classical baseline and
a learned neural matcher. Both are real, both are trained.

## Feature engineering (shared)

Every pair is converted into a 15-dim feature vector (`MatchFeatures`):

```
[0]  tfidf_cosine
[1]  jaccard_skills
[2]  jd_coverage
[3]  resume_skill_count
[4]  jd_required_skill_count
[5]  matching_skill_count
[6]  missing_skill_count
[7]  extra_skill_count
[8]  years_required
[9]  years_estimated
[10] years_gap
[11] education_required
[12] education_present
[13] resume_length
[14] jd_length
```

Why this combination? Cosine similarity captures topical overlap; the skill
counts/jaccard/coverage capture set-alignment; years and education signals
hard-filter out under-qualified candidates. Together they form a compact,
interpretable vector that downstream models can both consume.

## Baseline — scikit-learn (`app/ml/sklearn_baseline.py`)

- **Vectorization:** `TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)`
- **Regressor head:** `Ridge(alpha=1.0)` — predicts continuous score in [0, 1]
  after clipping.
- **Classifier head:** `LogisticRegression(multi_class='multinomial')` —
  predicts poor / average / good. Used primarily for stratified evaluation.
- **Metrics computed at training:** MSE, MAE, RMSE, R², precision/recall/F1
  (macro), ROC-AUC (OvR), confusion matrix.

## Neural matcher — PyTorch (`app/ml/pytorch_model.py`)

```
Linear(15, 32) → ReLU → Dropout(0.1) →
Linear(16)     → ReLU → Dropout(0.1) →
Linear(1)      → Sigmoid
```

- **Loss:** `BCELoss`
- **Optimizer:** `Adam(lr=1e-3)`
- **Epochs:** 80 by default, configurable
- **Validation:** holdout 80/20; best-val-loss weights are checkpointed and
  saved as `ml_models/pytorch_matcher.pt`.
- **Device:** auto-selects CUDA if available.

## Synthetic training data

See `app/ml/synthetic_data.py`. The dataset is constructed from a curated skill
taxonomy. For each pair, the ground-truth score is computed deterministically:

```
base       = (matched_required / required_count) * 0.75
            + (matched_preferred / preferred_count) * 0.10
exp_score  = 0.15 if yrs >= required
             0.08 if yrs + 1.5 >= required
             max(0, 0.05 - 0.02 * gap)
edu_score  = 0.05 if (not edu_required or edu_present) else 0
score      = base + exp_score + edu_score + small_noise
```

Why deterministic? To avoid leaking randomness into evaluation; to make the
synthetic generator reproducible; and to keep the relationship between inputs
and labels discoverable.

To swap in a real dataset, drop in the same `TrainingExample` shape via
`load_dataset()` in `app/ml/synthetic_data.py`.

## Final score

```
final = 0.5 * sklearn_score + 0.5 * pytorch_score
```

We treat both heads as equally authoritative. If you have evidence that one
outperforms the other on your real data, weight accordingly.

## Evaluation

The `/api/v1/models/performance` endpoint re-runs both models on a fresh slice
of labeled examples and reports live metrics. The UI surfaces them on the
**Models** page.
