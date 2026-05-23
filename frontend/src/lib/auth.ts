import { apiFetch, tokens } from "./api";

export interface TenantSummary {
  public_id: string;
  name: string;
  slug: string;
  status: "trial" | "active" | "past_due" | "canceled" | "suspended";
  trial_ends_at: string | null;
  role: "owner" | "admin" | "viewer";
}

export interface User {
  public_id: string;
  email: string;
  full_name: string;
  is_staff: boolean;
  tenant: TenantSummary | null;
}

interface AuthResponse {
  user: User;
  tokens: { access: string; refresh: string };
}

export async function registerUser(payload: {
  email: string;
  password: string;
  full_name?: string;
  company_name: string;
}) {
  const data = await apiFetch<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
  tokens.set(data.tokens.access, data.tokens.refresh);
  return data.user;
}

export async function loginUser(email: string, password: string) {
  const data = await apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    skipAuth: true,
  });
  tokens.set(data.tokens.access, data.tokens.refresh);
  return data.user;
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/api/auth/me");
}

export function logout() {
  tokens.clear();
}

export async function requestPasswordReset(email: string): Promise<{ detail: string }> {
  return apiFetch("/api/auth/password-reset", {
    method: "POST",
    body: JSON.stringify({ email }),
    skipAuth: true,
  });
}

export async function confirmPasswordReset(payload: {
  uid: string;
  token: string;
  new_password: string;
}): Promise<{ detail: string }> {
  return apiFetch("/api/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
}
