import { render, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  resolveFilePreviewKind,
  UniversalFilePreview,
} from "../../../src/components/file-preview";
import { renderAsync } from "docx-preview";

vi.mock("docx-preview", () => ({
  renderAsync: vi.fn(async (_file: ArrayBuffer, container: HTMLElement) => {
    const page = document.createElement("section");
    page.textContent = "Word document rendered";
    container.append(page);
  }),
}));

describe("UniversalFilePreview", () => {
  beforeAll(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:universal-preview"),
      writable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
      writable: true,
    });
  });

  beforeEach(() => {
    vi.mocked(URL.createObjectURL).mockClear();
    vi.mocked(URL.revokeObjectURL).mockClear();
    vi.mocked(renderAsync).mockClear();
  });

  it("resolves supported formats from project type, MIME type, and extension", () => {
    expect(resolveFilePreviewKind({ fileName: "renamed", materialType: "ppt" })).toBe("pptx");
    expect(
      resolveFilePreviewKind({
        fileName: "renamed",
        mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    ).toBe("docx");
    expect(resolveFilePreviewKind({ fileName: "diagram.PNG" })).toBe("image");
    expect(resolveFilePreviewKind({ fileName: "archive.zip" })).toBe("unsupported");
  });

  it("renders a PDF object URL with an initial page and releases it on unmount", async () => {
    const { unmount } = render(
      <UniversalFilePreview
        file={new Blob(["%PDF-1.4"], { type: "application/pdf" })}
        fileName="第一章.pdf"
        initialPage={7}
      />,
    );

    expect(await screen.findByTitle("第一章.pdf PDF 预览")).toHaveAttribute(
      "src",
      "blob:universal-preview#page=7&view=FitH",
    );
    expect(screen.getByRole("link", { name: "下载原文件" })).toHaveAttribute("download", "第一章.pdf");

    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:universal-preview");
  });

  it("renders text as literal content without interpreting markup", async () => {
    const file = new File(["<script>danger()</script>\n# Heading"], "notes.md", { type: "text/markdown" });

    render(<UniversalFilePreview file={file} fileName={file.name} />);

    expect(await screen.findByText(/<script>danger\(\)<\/script>/)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });

  it("renders DOCX with the secure read-only options", async () => {
    const file = new File(["docx fixture"], "lecture.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    render(<UniversalFilePreview file={file} fileName={file.name} materialType="word" />);

    expect(screen.getByText("正在渲染 Word 文档…")).toBeInTheDocument();
    expect(await screen.findByText("Word document rendered")).toBeInTheDocument();
    expect(renderAsync).toHaveBeenCalledWith(
      expect.any(ArrayBuffer),
      expect.any(HTMLElement),
      expect.any(HTMLElement),
      expect.objectContaining({
        breakPages: true,
        renderAltChunks: false,
        useBase64URL: true,
      }),
    );
  });

  it("falls back to download for unsupported files", async () => {
    render(
      <UniversalFilePreview
        file={new Blob(["unknown"], { type: "application/octet-stream" })}
        fileName="archive.zip"
      />,
    );

    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());
    expect(screen.getByText("暂不支持在页面内预览此格式，请下载原文件查看。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "下载原文件" })).toHaveAttribute("href", "blob:universal-preview");
  });
});
