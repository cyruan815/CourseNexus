import { describe, expect, it } from "vitest";

import { normalizeApiBaseUrl } from "../../src/api/trusted-url";

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
