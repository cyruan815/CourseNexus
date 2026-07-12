export const TOKEN_STORAGE_KEY = "course_nexus_token";
export const SESSION_CHANGED_EVENT = "course-nexus-session-changed";

function notifySessionChanged(): void {
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

export function getSessionToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setSessionToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  notifySessionChanged();
}

export function clearSessionToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  notifySessionChanged();
}

export function subscribeSessionChange(listener: () => void): () => void {
  window.addEventListener(SESSION_CHANGED_EVENT, listener);

  return () => window.removeEventListener(SESSION_CHANGED_EVENT, listener);
}
