# Architecture

## Modules

```
backend/app/
  api/v1/        REST surface (resumes, jobs, matches, models)
  core/          Config, structured logging, custom exceptions
  db/            Async SQLAlchemy engine + session
  ml/            scikit-learn baseline, PyTorch matcher, feature
                 engineering, synthetic data generator, training
                 pipeline orchestrator
  models/        ORM: Resume, Job, Match, ModelPerformance
  schemas/       Pydantic v2 request/response schemas
  services/      Resume parser, JD parser, matching engine,
                 skill taxonomy, text preprocessing
  main.py        FastAPI entry point with lifespan loader
```

## Data flow

1. **Resume upload** → `pdfplumber` → text → `ResumeParser` splits sections,
   detects skills via `SkillsTaxonomy`, extracts years/experience heuristically.
   Stored as ORM row.

2. **Job create** → `JobParser` walks known section headers ("Requirements",
   "Nice to have", "Responsibilities"), tokenizes and tags skills.

3. **Match** → `MatchingEngine` computes the 15-dim feature vector, runs both
   models, blends scores (50/50), and writes the match record with the
   explainability fields.

4. **Performance** → on demand, generates fresh features from the cached
   training set, runs both models, reports live metrics.

## Persistence

- PostgreSQL 16 with Alembic migrations in `backend/alembic/`.
- Async SQLAlchemy 2.x; Pydantic 2 schemas for all endpoints.
- No PDF binaries persisted — only text + structures.

## ML lifecycle

- **Training** is decoupled from inference. `app/ml/train_pipeline.py`
  generates → fits → persists. The FastAPI lifespan tries to load persisted
  artifacts; if none exist, it auto-trains on synthetic data so the app is
  runnable with zero setup.
- **Inference** path lives in `MatchingEngine.match`, designed for sub-100ms
  responses on CPU for a single pair.

## Error handling

- Custom `AppException` hierarchy with HTTP status codes.
- Unified `JSONResponse` shape: `{ error, message, details }`.
- `RequestValidationError` translated to 422 with field details.

## Logging

- `python-json-logger` for production; readable text format in development.
- All requests decorated with an `X-Response-Time-ms` header for observability.
