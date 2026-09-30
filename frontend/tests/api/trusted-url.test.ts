import { describe, expect, it } from "vitest";

import { normalizeApiBaseUrl, resolveTrustedApiUrl } from "../../src/api/trusted-url";

describe("normalizeApiBaseUrl", () => {
  it("supports same-origin requests and normalizes a configured backend origin", () => {
    expect(normalizeApiBaseUrl(undefined)).toBe("");
    expect(normalizeApiBaseUrl("  ")).toBe("");
    expect(normalizeApiBaseUrl("http://localhost:8000/")).toBe("http://localhost:8000");
    expect(normalizeApiBaseUrl("https://api.example.com")).toBe("https://api.example.com");
  });

  it.each([
    "ftp://api.example.com",
    "//api.example.com",
    "/api",
    "https://user:password@api.example.com",
    "https://api.example.com/base",
    "https://api.example.com?tenant=one",
    "https://api.example.com#config",
  ])("rejects an untrusted API base value: %s", (value) => {
    expect(() => normalizeApiBaseUrl(value)).toThrow(/VITE_API_BASE_URL/);
  });
});

describe("resolveTrustedApiUrl", () => {
  it("resolves API paths against same-origin and configured backends", () => {
    expect(resolveTrustedApiUrl("/api/v1/courses?term=2026", "")).toBe(
      "/api/v1/courses?term=2026",
    );
    expect(resolveTrustedApiUrl("/api/v1/courses", "http://localhost:8000")).toBe(
      "http://localhost:8000/api/v1/courses",
    );
  });

  it.each([
    "https://attacker.example/api/v1/courses",
    "//attacker.example/api/v1/courses",
    "data:text/plain,secret",
    "api/v1/courses",
    "/api/v1\\courses",
    "/api/v1/../admin",
    "/api/v1/%2e%2e/admin",
    "/api/v10/courses",
    "/api/v1/courses#token",
  ])("rejects an untrusted authenticated request path: %s", (path) => {
    expect(() => resolveTrustedApiUrl(path, "http://localhost:8000")).toThrow(
      /鉴权 API 请求/,
    );
  });
});
