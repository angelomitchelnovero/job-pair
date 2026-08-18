// Browser requests use NEXT_PUBLIC_API_URL (set to http://localhost:8000/api/v1
// at build time). Server Components run inside the frontend container, where
// `localhost` resolves to the container itself, not the host. We therefore
// route server-side fetches through a different env var that uses the Docker
// service name `backend` — falling back to the public URL if not set.
const SERVER_API_BASE =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL?.replace("localhost", "backend") ||
  "http://localhost:8000/api/v1";

const API_BASE =
  typeof window === "undefined" ? SERVER_API_BASE : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type FetchOpts = RequestInit & { json?: unknown };

async function http<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const headers: HeadersInit = { ...(opts.headers as Record<string, string> | undefined) };
  let body = opts.body;
  if (opts.json !== undefined) {
    body = JSON.stringify(opts.json);
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers,
    body,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = data?.message || JSON.stringify(data);
    } catch {}
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => fetch(`${API_BASE.replace(/\/api\/v1$/, "")}/health`).then((r) => r.json()),

  listResumes: () => http<unknown[]>("/resumes"),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http("/resumes", { method: "POST", body: form });
  },
  getResume: (id: string) => http(`/resumes/${id}`),
  // Backend returns 204 No Content; http() handles that as `undefined` so
  // deleteResume resolves with `void` on success and throws on any non-2xx.
  // Note: deleting a resume also cascade-deletes any saved Match rows
  // that reference it (FK ondelete="CASCADE" on the matches table).
  deleteResume: (id: string) =>
    http<void>(`/resumes/${id}`, { method: "DELETE" }),

  listJobs: () => http<unknown[]>("/jobs"),
  createJob: (payload: unknown) =>
    http("/jobs", { method: "POST", json: payload }),
  getJob: (id: string) => http(`/jobs/${id}`),

  listMatches: () => http<unknown[]>("/matches"),
  getMatch: (id: string) => http(`/matches/${id}`),
  // Backend returns 204 No Content; http() handles that as `undefined` so
  // deleteMatch resolves with `void` on success and throws on any non-2xx.
  deleteMatch: (id: string) =>
    http<void>(`/matches/${id}`, { method: "DELETE" }),
  createMatch: (payload: unknown) =>
    http("/matches", { method: "POST", json: payload }),
  previewMatch: (payload: unknown) =>
    http("/matches/preview", { method: "POST", json: payload }),

  modelPerformance: () => http<unknown[]>("/models/performance"),
};
