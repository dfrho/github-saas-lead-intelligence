/**
 * Typed fetch wrappers for all FastAPI backend endpoints.
 * All authenticated requests pass the Supabase access token as Bearer.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Repo {
  owner: string;
  repo: string;
  label: string;
  added_at: string;
  last_checked: string | null;
  last_activity_hash: string | null;
}

export interface ReportSummary {
  id: string;
  owner: string;
  repo: string;
  run_at: string;
  status: string;
  score_composite: number | null;
  confidence_label: string | null;
}

export interface ReportDetail extends ReportSummary {
  score_activity: number | null;
  score_pain_points: number | null;
  score_dependencies: number | null;
  score_team_size: number | null;
  score_growth: number | null;
  markdown_body: string | null;
  json_body: Record<string, unknown> | null;
}

export interface ReportStatus {
  report_id: string;
  status: string;
}

async function apiFetch<T>(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Repos ─────────────────────────────────────────────────────────────────

export const fetchRepos = (token: string) =>
  apiFetch<Repo[]>("/repos", token);

export const watchRepo = (token: string, owner: string, repo: string, label?: string) =>
  apiFetch<Repo>("/repos", token, {
    method: "POST",
    body: JSON.stringify({ owner, repo, label }),
  });

export const removeRepo = (token: string, owner: string, repo: string) =>
  apiFetch<void>(`/repos/${owner}/${repo}`, token, { method: "DELETE" });

// ── Reports ───────────────────────────────────────────────────────────────

export const triggerReport = (owner: string, repo: string, token: string | null, org_domain?: string) =>
  apiFetch<{ report_id: string; status: string }>("/reports/run", token, {
    method: "POST",
    body: JSON.stringify({ owner, repo, org_domain }),
  });

export const fetchReportStatus = (report_id: string) =>
  apiFetch<ReportStatus>(`/reports/status/${report_id}`, null);

export const fetchReports = (token: string) =>
  apiFetch<ReportSummary[]>("/reports", token);

export const fetchReport = (token: string, id: string) =>
  apiFetch<ReportDetail>(`/reports/${id}`, token);

export const exportReportUrl = (id: string, format: "csv" | "txt") =>
  `${API_URL}/reports/${id}/export?format=${format}`;

// ── Users ─────────────────────────────────────────────────────────────────

export const fetchProfile = (token: string) =>
  apiFetch<{ user_id: string; company_name: string | null; work_domain: string | null }>("/users/me", token);

export const upsertProfile = (token: string, company_name: string, work_domain: string) =>
  apiFetch("/users/me", token, {
    method: "POST",
    body: JSON.stringify({ company_name, work_domain }),
  });
