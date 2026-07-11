import { describe, expect, it } from "vitest";

import configSource from "../../vite.config.ts?raw";

describe("vite dev server config", () => {
  it("proxies API requests to the local FastAPI backend", () => {
    expect(configSource).toContain('"/api"');
    expect(configSource).toContain('target: "http://127.0.0.1:8000"');
    expect(configSource).toContain("changeOrigin: true");
  });
});
