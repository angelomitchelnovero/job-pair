# JobPair.aloe — ML training & inference guide

This document explains the dual-model approach used in the project.

## Two pipelines, one feature set

Both models consume the same 15-dimensional engineered feature vector:

| Feature              | Source                                                    |
| -------------------- | --------------------------------------------------------- |
| tfidf_cosine         | Scikit-learn TF-IDF + cosine over resume ↔ JD             |
| jaccard_skills       | Set Jaccard between resume skills and JD required skills  |
| jd_coverage          | % of JD required skills covered by the resume             |
| skill counts         | Resume / JD / matching / missing / extra                  |
| years_required       | Years required by the JD                                  |
| years_estimated      | Years extracted from the resume                           |
| years_gap            | Estimated − required                                      |
| education_required   | 0/1 boolean from JD                                       |
| education_present    | 0/1 boolean from resume                                   |
| resume_length        | Char count of resume raw text                             |
| jd_length            | Char count of JD                                          |

## scikit-learn baseline (`app/ml/sklearn_baseline.py`)

- **Vectorization** — `TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True, min_df=1)`
- **Regressor** — `Ridge(alpha=1.0)`, continuous output in [0, 1]
- **Classifier** — `LogisticRegression(multi_class='multinomial')`, three buckets
  (poor / average / good) for monitoring
- **Metrics** — MSE, MAE, R², precision/recall/F1 (macro), ROC-AUC (OvR), confusion matrix

## PyTorch matcher (`app/ml/pytorch_model.py`)

- **Architecture** — `nn.Sequential(Linear(15, 32) -> ReLU -> Dropout -> Linear(16) -> ReLU -> Dropout -> Linear(1))`
- **Output** — `torch.sigmoid` for [0, 1] score
- **Loss** — `BCELoss`
- **Optimizer** — `Adam(lr=1e-3)`
- **Training** — 80 epochs by default, mini-batch size 32, holdout split 80/20,
  best-validation-loss model checkpointed and persisted.
- **Device** — auto-selects CUDA if available

## Final score

Final score = `0.5 * sklearn_score + 0.5 * pytorch_score`, expressed as a percentage.

Both raw scores are exposed to the UI so the user can see where they agree and disagree.

## Synthetic training data

See `app/ml/synthetic_data.py`. The dataset is generated from the curated skill
taxonomy (`app/services/skills_taxonomy.py`). Ground truth is computed deterministically
from features (coverage + experience + education), so the same input always yields the
same target. Replace this with a real labeled corpus (e.g. a public resume-JD dataset
or your own annotations) by implementing the same `TrainingExample` dataclass.
