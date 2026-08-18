# JobPair.aloe

> **AI-powered Resume → Job matching platform.**
> Explainable scores from a scikit-learn TF-IDF/cosine baseline **and** a PyTorch neural matcher.

JobPair.aloe takes a resume (PDF or pasted text) and a job description and produces:

- An **overall match score** (0–100%)
- A breakdown of **matching skills** and **missing skills**
- **Experience** and **education alignment** with explicit reasoning
- A **comparison** between the two independent model scores
- A plain-language **explanation** of why the score is what it is
- Concrete **recommendations** to improve the match

This is a portfolio project that demonstrates end-to-end ML engineering with both
classical and deep learning models, a clean FastAPI backend, PostgreSQL persistence,
and a polished Next.js + Tailwind frontend — all orchestrated with Docker.

---

## ✨ Highlights

| Area        | What's used                                                   |
| ----------- | ------------------------------------------------------------- |
| Frontend    | Next.js 15 (App Router) · React 19 · TypeScript · Tailwind    |
| Backend     | Python 3.12 · FastAPI · Pydantic · SQLAlchemy 2 (async)      |
| Database    | PostgreSQL 16 · Alembic migrations                            |
| ML          | scikit-learn 1.6 (Ridge + LogReg + TF-IDF) · PyTorch 2.2 MLP  |
| Tests       | pytest (backend) · jest (frontend utils)                      |
| Infra       | Docker · docker-compose · structured JSON logging             |
| NLP         | pdfplumber · NLTK (lemmatization + stopwords)                 |

---

## 🏗️ Architecture

```
job-pair/
├── backend/                # FastAPI app
│   ├── app/
│   │   ├── api/v1/         # Routers: resumes, jobs, matches, models
│   │   ├── core/           # Config, logging, exceptions
│   │   ├── db/             # Async SQLAlchemy session
│   │   ├── ml/             # scikit-learn + PyTorch models
│   │   ├── models/         # ORM models (SQLAlchemy)
│   │   ├── schemas/        # Pydantic request/response models
│   │   └── services/       # Resume/JD parsing, matching engine
│   ├── alembic/            # Migrations
│   └── tests/              # pytest suite
├── frontend/               # Next.js 15 app
│   └── src/
│       ├── app/            # App-router pages
│       ├── components/     # Score card, Match card, Navbar
│       └── lib/            # API client, utils
├── docker/                 # Architecture & ML docs
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── Makefile
└── README.md
```

### Request flow

```
Resume PDF ──▶ pdfplumber ──▶ SectionSplit ──▶ SkillExtractor ──▶ Resume ORM
                                                                       │
                                                                       ▼
Job Description ──▶ JobParser (required/preferred/responsibilities/years) ──▶ Job ORM
                                                                       │
                                                                       ▼
          ┌────────────────────── MatchingEngine ──────────────────────┐
          │                                                             │
          │            ┌─── scikit-learn baseline ───┐                  │
          │            │   TF-IDF cosine + 15 fea   │                  │
          │            │   tures → Ridge + LogReg   │  ── 50% blend ──▶ Final %
          │            └────────────────────────────┘                  │
          │            ┌─── PyTorch matcher ────────┐                  │
          │            │   15 → 32 → 16 → 1 MLP    │                  │
          │            │   sigmoid / BCELoss         │                  │
          │            └────────────────────────────┘                  │
          │                                                             │
          └─────────── Explainable breakdown (skill match, gaps, yrs, edu) ─▶ Match ORM
```

---

## 🚀 Quick start

### 1. One command (Docker)

```bash
cd job-pair
cp .env.example .env
docker-compose up --build
```

- Frontend: <http://localhost:3000>
- Backend:  <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

The compose file trains the ML models on first startup, then runs migrations and
serves FastAPI + Next.js.

### 2. Local development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# ML training (optional — auto-trains on first run if models are missing)
python -m app.ml.train_pipeline

# Frontend
cd ../frontend
npm install
npm run dev
```

---

## 🧪 Tests

```bash
cd backend && pytest -v
cd frontend && npm test
```

The backend suite covers:

- `tests/test_skills_taxonomy.py` — canonicalization + detection
- `tests/test_text_processing.py` — NLTK pipeline
- `tests/test_resume_parser.py` — section splitting, contact info, years
- `tests/test_job_parser.py` — required/preferred skills, years, education
- `tests/test_ml.py` — TF-IDF, sklearn baseline fit/predict, PyTorch fit/predict, MatchNet forward shape
- `tests/test_matching_engine.py` — full end-to-end match result

---

## 🔌 API

All endpoints live under `/api/v1`:

| Method | Path                       | Description                                     |
| ------ | -------------------------- | ----------------------------------------------- |
| POST   | `/resumes`                 | Upload PDF resume (multipart `file=...`)        |
| GET    | `/resumes`                 | List resumes                                    |
| GET    | `/resumes/{id}`            | Retrieve resume                                 |
| DELETE | `/resumes/{id}`            | Delete resume                                   |
| POST   | `/jobs`                    | Create job + parse                              |
| GET    | `/jobs`                    | List jobs                                       |
| GET    | `/jobs/{id}`               | Retrieve job                                    |
| DELETE | `/jobs/{id}`               | Delete job                                      |
| POST   | `/matches`                 | Persist match between two persisted artifacts   |
| POST   | `/matches/preview`         | Live match without persistence                  |
| GET    | `/matches`                 | List previous analyses                          |
| GET    | `/matches/{id}`            | Retrieve match with full breakdown              |
| GET    | `/models/performance`      | Live metrics from the loaded models             |

All errors return a unified JSON shape:

```json
{ "error": "validation_error", "message": "...", "details": {...} }
```

---

## 🧠 ML details

Two independent models are trained on the same 15-dimensional engineered feature
vector. See [`docker/README.md`](docker/README.md) for the full guide.

**scikit-learn baseline**

- TF-IDF (1-2 n-grams, sublinear) + cosine similarity
- Ridge regression head (continuous score in [0, 1])
- LogisticRegression classifier head (poor / average / good)
- Reports: MSE, MAE, R², precision, recall, F1, ROC-AUC, confusion matrix

**PyTorch matcher**

- 3-layer MLP: `Linear(15, 32) → ReLU → Dropout → Linear(16) → ReLU → Dropout → Linear(1) → Sigmoid`
- BCELoss, Adam(1e-3), 80 epochs, holdout 80/20, best-val-loss checkpoint

**Final score**

```
final = 0.5 * sklearn_score + 0.5 * pytorch_score
```

The UI shows both raw scores side-by-side so the comparison is transparent.

---

## 🧾 Database schema

```text
resumes         (id, filename, full_name, email, raw_text,
                 sections JSON, skills JSON, experience JSON,
                 education JSON, projects JSON, certifications JSON,
                 created_at, updated_at)

jobs            (id, title, company, description,
                 skills_required JSON, skills_preferred JSON,
                 responsibilities JSON, experience_years,
                 education_required, created_at, updated_at)

matches         (id, resume_id FK, job_id FK,
                 sklearn_score, pytorch_score, final_score,
                 matching_skills JSON, missing_skills JSON,
                 extra_skills JSON, experience_alignment JSON,
                 education_alignment JSON, recommendations JSON,
                 feature_breakdown JSON, explanation TEXT,
                 created_at, updated_at)

model_performance (id, model_name, version, metrics JSON,
                   training_samples, notes, created_at, updated_at)
```

No raw resume PDFs are stored — only extracted text + structured fields.

---

## 🔧 Environment variables

See [`.env.example`](.env.example). Everything is optional in development.
Required in production:

- `DATABASE_URL` — async SQLAlchemy URL
- `DATABASE_URL_SYNC` — sync URL (used by Alembic)
- `BACKEND_URL` / `FRONTEND_URL` — CORS configuration

---

## ⚠️ Limitations

- **Synthetic training data.** The current dataset is generated from the skill
  taxonomy using a deterministic scoring function. It is intentionally
  synthetic and clearly marked so it can be replaced with a real labeled set
  (e.g. a public resume-vs-JD dataset, or human-annotated examples).
- **Skill taxonomy is hand-curated.** New domains may require extending
  `app/services/skills_taxonomy.py`.
- **Years / education are heuristic.** Regexes and section detection work well
  on typical Western resumes; exotic formats may need manual sections.
- **No auth.** This is a portfolio project. Add an auth layer (FastAPI Users,
  JWT, or NextAuth) before exposing publicly.

---

## 🌱 Future improvements

- Real resume-JD labeled dataset + fine-tuned BERT-style model
- Per-job-description skill weighting (semantic similarity rather than bag-of-skills)
- Multi-resume ranking (recruiter view)
- Auth + multi-user workspaces
- Streaming responses for large analyses
- CI/CD with model evaluation gates