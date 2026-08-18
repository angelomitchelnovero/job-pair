# API reference

Base URL: `http://localhost:8000/api/v1`

## Resumes

### `POST /resumes`
Upload a PDF. Multipart form field: `file`.

```bash
curl -F "file=@resume.pdf" http://localhost:8000/api/v1/resumes
```

### `GET /resumes?limit=50&offset=0`
List uploaded resumes, newest first.

### `GET /resumes/{id}`
Retrieve one resume, including extracted skills and sections.

### `DELETE /resumes/{id}`
Delete a resume and cascade-delete its matches.

## Jobs

### `POST /jobs`
```json
{
  "title": "Senior ML Engineer",
  "company": "Acme",
  "description": "..."
}
```

### `GET /jobs`
### `GET /jobs/{id}`
### `DELETE /jobs/{id}`

## Matches

### `POST /matches`
Two modes:

- **By persisted artifacts:**
```json
{ "resume_id": "...", "job_id": "..." }
```

- **Live text:**
```json
{
  "resume_text": "...",
  "job_text": "...",
  "job_title": "Senior ML Engineer",
  "job_company": "Acme"
}
```

### `POST /matches/preview`
Same payload shape as the live text mode but does **not** persist.

### `GET /matches`
### `GET /matches/{id}`

Response includes:

```json
{
  "id": "...",
  "sklearn_score": 82.0,
  "pytorch_score": 87.0,
  "final_score": 85.0,
  "matching_skills": [{"name": "python", "matched": "required"}],
  "missing_skills":  [{"name": "aws", "matched": false}],
  "extra_skills":    ["snowflake"],
  "experience_alignment": {"required_years": 5, "estimated_years": 6, "matched": true, "notes": "..."},
  "education_alignment":  {"required": "bachelor", "candidates": ["Bachelor"], "matched": true, "notes": "..."},
  "recommendations": ["Build a small project..."],
  "feature_breakdown": [
    {"feature": "tfidf_cosine", "contribution": 0.42, "direction": "positive"}
  ],
  "explanation": "Final score 85% = 50% scikit-learn (82%) + 50% PyTorch (87%). ..."
}
```

## Models

### `GET /models/performance`
Returns live evaluation metrics for the loaded models, plus any snapshots
stored in the `model_performance` table.

## Errors

All errors return:

```json
{ "error": "<code>", "message": "<human readable>", "details": <optional> }
```

Status codes used:
- `400` Bad Request (handled by FastAPI)
- `404` Resource not found
- `413` File too large
- `415` Unsupported media type
- `422` Validation error
- `500` Unhandled exception
- `503` Model not loaded
