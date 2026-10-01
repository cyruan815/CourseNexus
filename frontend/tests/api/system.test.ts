import { afterEach, describe, expect, it, vi } from "vitest";

import { getRuntimeStatus } from "../../src/api/system";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("system API", () => {
  it("reads the public runtime mode from health", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            status: "ok",
            environment: "development",
            mock_model_provider_enabled: true,
          },
          meta: {},
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getRuntimeStatus()).resolves.toEqual({
      status: "ok",
      environment: "development",
      mock_model_provider_enabled: true,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({ headers: {} }),
    );
  });
});
