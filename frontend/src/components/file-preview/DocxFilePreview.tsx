import { useEffect, useRef, useState } from "react";

import { readBlobAsArrayBuffer } from "./blob-readers";
import { FilePreviewStatus } from "./FilePreviewStatus";

type DocxRenderState = "loading" | "ready" | "error";

export function DocxFilePreview({ file }: { file: Blob }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [renderState, setRenderState] = useState<DocxRenderState>("loading");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    let active = true;
    container.replaceChildren();
    setRenderState("loading");

    Promise.all([readBlobAsArrayBuffer(file), import("docx-preview")])
      .then(async ([buffer, { renderAsync }]) => {
        if (!active) {
          return;
        }
        await renderAsync(buffer, container, container, {
          breakPages: true,
          className: "course-nexus-docx",
          experimental: false,
          ignoreFonts: false,
          ignoreHeight: false,
          ignoreLastRenderedPageBreak: true,
          ignoreWidth: false,
          inWrapper: true,
          renderAltChunks: false,
          renderComments: false,
          renderEndnotes: true,
          renderFooters: true,
          renderFootnotes: true,
          renderHeaders: true,
          useBase64URL: true,
        });
        if (active) {
          setRenderState("ready");
        } else {
          container.replaceChildren();
        }
      })
      .catch(() => {
        if (active) {
          container.replaceChildren();
          setRenderState("error");
        }
      });

    return () => {
      active = false;
      container.replaceChildren();
    };
  }, [file]);

  return (
    <div className="universal-file-preview__docx-shell">
      <div className="universal-file-preview__docx-document" ref={containerRef} />
      {renderState === "loading" ? (
        <FilePreviewStatus message="正在渲染 Word 文档…" role="status" tone="loading" />
      ) : null}
      {renderState === "error" ? (
        <FilePreviewStatus message="Word 文档渲染失败，请下载原文件查看。" role="alert" tone="error" />
      ) : null}
    </div>
  );
}
