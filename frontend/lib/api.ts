const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; formData?: FormData } = {}
): Promise<T> {
  const method = options.method || "GET";
  const headers: Record<string, string> = {};

  if (method !== "GET" && method !== "HEAD") {
    const csrf = readCookie("netrasee_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData; // browser sets multipart Content-Type with boundary
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body,
    credentials: "include",
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      message = data.detail ? JSON.stringify(data.detail) : message;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, formData: FormData) => request<T>(path, { method: "POST", formData }),
};

export interface UserOut {
  id: string;
  email: string;
  name: string;
}

export interface MembershipOut {
  organization_id: string;
  organization_name: string;
  role: "OWNER" | "ADMIN" | "VIEWER";
}

export interface MeResponse {
  user: UserOut;
  memberships: MembershipOut[];
}

export interface FrameworkProgress {
  framework_key: string;
  framework_name: string;
  progress_percent: number;
  control_count: number;
  passing_count: number;
}

export interface DashboardOut {
  frameworks: FrameworkProgress[];
  controls: { passing: number; failing: number; needs_review: number; not_applicable: number; not_tested: number };
  evidence: { valid: number; expiring: number; expired: number; under_review: number };
}

export interface ControlListItem {
  id: string;
  control_key: string;
  name: string;
  category: string;
  status: "PASS" | "FAIL" | "NEEDS_REVIEW" | "NOT_APPLICABLE" | "NOT_TESTED";
  automation_status: "MANUAL" | "AUTOMATED" | "HYBRID";
  owner_user_id: string | null;
  next_review_at: string | null;
}

export interface RequirementMapping {
  requirement_id: string;
  requirement_key: string;
  requirement_name: string;
  framework_key: string;
  framework_name: string;
}

export interface ControlEvidenceRef {
  id: string;
  name: string;
  status: string;
}

export interface ControlDetail extends ControlListItem {
  description: string;
  objective: string;
  testing_frequency: string;
  last_tested_at: string | null;
  requirements: RequirementMapping[];
  evidence: ControlEvidenceRef[];
}

export interface EvidenceOut {
  id: string;
  name: string;
  description: string;
  source: string;
  collected_at: string;
  expires_at: string | null;
  status: "VALID" | "EXPIRING" | "EXPIRED" | "UNDER_REVIEW";
  checksum_sha256: string;
  collection_method: string;
  owner_user_id: string | null;
  controls: { control_id: string; control_key: string; control_name: string }[];
}

export interface AdoptedFramework {
  framework: { id: string; key: string; name: string; description: string };
  adopted_at: string;
  progress_percent: number;
  requirements: {
    id: string;
    key: string;
    name: string;
    description: string;
    control_count: number;
    passing_count: number;
  }[];
}

export interface MemberOut {
  user_id: string;
  email: string;
  name: string;
  role: "OWNER" | "ADMIN" | "VIEWER";
}

export interface AuditEventOut {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  created_at: string;
}
