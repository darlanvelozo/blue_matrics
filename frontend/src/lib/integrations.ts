import { apiFetch } from "./api";

export type ConnectionStatus = "disconnected" | "connected" | "error" | "revoked";

export interface ContaAzulStatus {
  status: ConnectionStatus;
  scope: string;
  expires_at: string | null;
  connected_at: string | null;
  last_synced_at: string | null;
  last_error: string;
  has_credentials: boolean;
  client_id: string;
  redirect_uri: string;
}

export interface ContaAzulCredentials {
  has_credentials: boolean;
  client_id: string;
  redirect_uri: string;
}

export function getContaAzulStatus(): Promise<ContaAzulStatus> {
  return apiFetch<ContaAzulStatus>("/api/integrations/contaazul/status");
}

export function getContaAzulCredentials(): Promise<ContaAzulCredentials> {
  return apiFetch<ContaAzulCredentials>("/api/integrations/contaazul/credentials");
}

export function saveContaAzulCredentials(payload: {
  client_id: string;
  client_secret: string;
}): Promise<ContaAzulCredentials> {
  return apiFetch<ContaAzulCredentials>("/api/integrations/contaazul/credentials", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteContaAzulCredentials(): Promise<{ has_credentials: false }> {
  return apiFetch<{ has_credentials: false }>(
    "/api/integrations/contaazul/credentials",
    { method: "DELETE" },
  );
}

export function startContaAzulAuthorize(): Promise<{ url: string; state: string }> {
  return apiFetch<{ url: string; state: string }>(
    "/api/integrations/contaazul/authorize",
  );
}

export function disconnectContaAzul(): Promise<ContaAzulStatus> {
  return apiFetch<ContaAzulStatus>("/api/integrations/contaazul/disconnect", {
    method: "POST",
  });
}
