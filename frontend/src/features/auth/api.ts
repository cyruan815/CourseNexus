import { apiRequest } from "../../api/client";
import { clearSessionToken, setSessionToken } from "./session";

export interface AuthUser {
  id: string;
  username: string;
  nickname: string | null;
  avatar_url: string | null;
  status: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: AuthUser;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  nickname?: string | null;
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
