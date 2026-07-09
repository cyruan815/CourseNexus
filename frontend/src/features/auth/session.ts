export const TOKEN_STORAGE_KEY = "course_nexus_token";

export function getSessionToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setSessionToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearSessionToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}
