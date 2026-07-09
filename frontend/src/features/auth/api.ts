import { apiRequest } from "../../api/client";
import { clearSessionToken, setSessionToken } from "./session";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  display_name?: string | null;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const auth = await apiRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: payload,
  });
  setSessionToken(auth.access_token);
  return auth;
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const auth = await apiRequest<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: payload,
  });
  setSessionToken(auth.access_token);
  return auth;
}

export function fetchCurrentUser(): Promise<AuthUser> {
  return apiRequest<AuthUser>("/api/v1/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await apiRequest("/api/v1/auth/logout", { method: "POST" });
  } finally {
    clearSessionToken();
  }
}
