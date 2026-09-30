import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getRuntimeStatus } from "../../src/api/system";
import { RuntimeModeBanner } from "../../src/components/RuntimeModeBanner";

vi.mock("../../src/api/system", () => ({
  getRuntimeStatus: vi.fn(),
}));

const getRuntimeStatusMock = vi.mocked(getRuntimeStatus);

afterEach(() => {
  vi.clearAllMocks();
});

describe("RuntimeModeBanner", () => {
  it("shows a persistent warning when mock mode is enabled", async () => {
    getRuntimeStatusMock.mockResolvedValue({
      status: "ok",
      environment: "development",
      mock_model_provider_enabled: true,
    });

    render(<RuntimeModeBanner />);

    const banner = await screen.findByRole("status");
    expect(banner).toHaveTextContent("模拟模型模式");
    expect(banner).toHaveTextContent("当前生成内容仅用于开发验证");
  });

  it("stays hidden when mock mode is disabled", async () => {
    getRuntimeStatusMock.mockResolvedValue({
      status: "ok",
      environment: "development",
      mock_model_provider_enabled: false,
    });

    render(<RuntimeModeBanner />);

    await waitFor(() => expect(getRuntimeStatusMock).toHaveBeenCalledOnce());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("does not block the shell when runtime status is unavailable", async () => {
    getRuntimeStatusMock.mockRejectedValue(new Error("health unavailable"));

    render(<RuntimeModeBanner />);

    await waitFor(() => expect(getRuntimeStatusMock).toHaveBeenCalledOnce());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
