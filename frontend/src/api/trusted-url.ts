const SUPPORTED_API_PROTOCOLS = new Set(["http:", "https:"]);
const API_PATH_PREFIX = "/api/v1";
const URL_VALIDATION_ORIGIN = "https://course-nexus.invalid";

export function normalizeApiBaseUrl(rawValue: string | undefined): string {
  const value = rawValue?.trim() ?? "";
  if (!value) {
    return "";
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("VITE_API_BASE_URL 必须是合法的 HTTP(S) 后端 Origin");
  }

  if (
    !SUPPORTED_API_PROTOCOLS.has(url.protocol) ||
    url.username ||
    url.password ||
    (url.pathname !== "/" && url.pathname !== "") ||
    url.search ||
    url.hash
  ) {
    throw new Error("VITE_API_BASE_URL 只允许配置 HTTP(S) 后端 Origin");
  }

  return url.origin;
}

export function resolveTrustedApiUrl(path: string, apiBaseUrl: string): string {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("\\")) {
    throw new Error("鉴权 API 请求必须使用 /api/v1 根相对路径");
  }

  let url: URL;
  try {
    url = new URL(path, URL_VALIDATION_ORIGIN);
  } catch {
    throw new Error("鉴权 API 请求路径不合法");
  }

  if (
    url.origin !== URL_VALIDATION_ORIGIN ||
    url.hash ||
    (url.pathname !== API_PATH_PREFIX && !url.pathname.startsWith(`${API_PATH_PREFIX}/`))
  ) {
    throw new Error("鉴权 API 请求必须使用 /api/v1 根相对路径");
  }

  return `${apiBaseUrl}${url.pathname}${url.search}`;
}
