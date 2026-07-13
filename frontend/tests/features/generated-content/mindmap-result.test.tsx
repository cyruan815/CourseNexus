import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const fit = vi.fn(); const rescale = vi.fn(); const setData = vi.fn(); const destroy = vi.fn();
  const create = vi.fn(() => ({ fit, rescale, setData, destroy }));
  return { fit, rescale, setData, destroy, create };
});
vi.mock("markmap-view", () => ({ Markmap: { create: mocks.create } }));

import { MindmapResult } from "../../../src/features/generated-content/renderers/MindmapResult";

const content = {
  root_node_id: "node_001",
  nodes: [{ id: "node_001", label: "Root", summary: "Summary", level: 1 }],
  edges: [],
  markmap_data: { root: { content: "Root", children: [{ content: "Child" }] }, features: {}, assets: {} },
};

describe("MindmapResult", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the preprocessed root with markmap-view and exposes view controls", async () => {
    render(<MantineProvider><MindmapResult content={content} /></MantineProvider>);
    await waitFor(() => expect(mocks.create).toHaveBeenCalled());
    expect((mocks.create.mock.calls as unknown[][])[0][2]).toBeUndefined();
    expect(mocks.setData).toHaveBeenCalledWith(expect.objectContaining({
      content: "Root",
      payload: expect.objectContaining({ fold: 1 }),
    }));
    expect(content.markmap_data.root).not.toHaveProperty("payload");
    fireEvent.click(screen.getByRole("button", { name: "适配画布" }));
    fireEvent.click(screen.getByRole("button", { name: "放大" }));
    expect(mocks.fit).toHaveBeenCalled();
    expect(mocks.rescale).toHaveBeenCalledWith(1.2);
  });

  it("falls back to graph text when markmap initialization fails", async () => {
    mocks.create.mockImplementationOnce(() => { throw new Error("svg failed"); });
    render(<MantineProvider><MindmapResult content={content} /></MantineProvider>);
    expect(await screen.findByText("Root")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("图形视图暂不可用，已显示结构化内容。");
  });
});
