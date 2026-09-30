const SUPPORTED_API_PROTOCOLS = new Set(["http:", "https:"]);

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
