import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { setSessionToken } from "../../../src/features/auth/session";
import type { ModelRuntimeConfigRead } from "../../../src/features/profile/api";
import { ModelConfigModal } from "../../../src/features/profile/ModelConfigModal";


function jsonResponse(data: unknown, requestId = "req_model_config") {
  return Promise.resolve(
    new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function modelConfig(apiKeyHint: string | null = "gene••••"): ModelRuntimeConfigRead {
  return {
    embedding: {
      model: "text-embedding-3-large",
      base_url: "https://embedding.example/v1",
      api_key_configured: true,
      api_key_hint: "embe••••",
    },
    general: {
      model: "general-model",
      base_url: "https://models.example/v1",
      api_key_configured: true,
      api_key_hint: apiKeyHint,
    },
    general_config_consistent: true,
  };
}

function ModelConfigHarness() {
  const [opened, setOpened] = useState(false);
  return (
    <MantineProvider>
      <button onClick={() => setOpened(true)} type="button">打开模型配置</button>
      <ModelConfigModal onClose={() => setOpened(false)} opened={opened} />
    </MantineProvider>
  );
}

describe("ModelConfigModal", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("saves two groups and only shows key prefixes when reopened", async () => {
    setSessionToken("token-profile");
    let saved = false;
    let savedPayload: unknown = null;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/model-runtime/config" && init?.method === "GET") {
        return jsonResponse(modelConfig(saved ? "newg••••" : "gene••••"));
      }
      if (url === "/api/v1/model-runtime/config" && init?.method === "PUT") {
        saved = true;
        savedPayload = JSON.parse(String(init.body));
        return jsonResponse(modelConfig("newg••••"), "req_model_config_update");
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ModelConfigHarness />);
    fireEvent.click(screen.getByRole("button", { name: "打开模型配置" }));

    expect(await screen.findByRole("dialog", { name: "模型配置" })).toBeInTheDocument();
    expect(await screen.findByDisplayValue("text-embedding-3-large")).toBeInTheDocument();
    expect(screen.getByText("当前 Key：embe••••；留空则保留")).toBeInTheDocument();
    expect(screen.getByText("当前 Key：gene••••；留空则保留")).toBeInTheDocument();
    expect(screen.queryByText("embedding-complete-secret")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^其他模型名称/), {
      target: { value: "new-general-model" },
    });
    fireEvent.change(screen.getByLabelText(/^其他模型 Base URL/), {
      target: { value: "https://new-models.example/v1" },
    });
    fireEvent.change(screen.getByLabelText("其他模型 API Key"), {
      target: { value: "new-general-complete-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(await screen.findByText("新配置已写入并用于后续模型请求。")).toBeInTheDocument();
    expect(savedPayload).toEqual({
      embedding: {
        model: "text-embedding-3-large",
        base_url: "https://embedding.example/v1",
      },
      general: {
        model: "new-general-model",
        base_url: "https://new-models.example/v1",
        api_key: "new-general-complete-secret",
      },
    });
    expect(screen.getByLabelText("其他模型 API Key")).toHaveValue("");
    expect(screen.queryByDisplayValue("new-general-complete-secret")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "关闭模型配置弹窗" }));
    fireEvent.click(screen.getByRole("button", { name: "打开模型配置" }));

    expect(await screen.findByText("当前 Key：newg••••；留空则保留")).toBeInTheDocument();
    await waitFor(() => {
      const getCalls = fetchMock.mock.calls.filter(
        ([input, init]) => String(input) === "/api/v1/model-runtime/config" && init?.method === "GET",
      );
      expect(getCalls).toHaveLength(2);
    });
  });

  it("requires keys when the server has no existing configuration", async () => {
    const unconfigured = modelConfig();
    unconfigured.embedding.api_key_configured = false;
    unconfigured.embedding.api_key_hint = null;
    unconfigured.general.api_key_configured = false;
    unconfigured.general.api_key_hint = null;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/v1/model-runtime/config" && init?.method === "GET") {
        return jsonResponse(unconfigured);
      }
      throw new Error("PUT must not be called before local validation passes");
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ModelConfigHarness />);
    fireEvent.click(screen.getByRole("button", { name: "打开模型配置" }));
    await screen.findByDisplayValue("text-embedding-3-large");
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(await screen.findByText("首次配置时必须填写 Embedding API Key")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
