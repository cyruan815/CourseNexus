import { useEffect, useRef, useState } from "react";
import type { PptxViewer as PptxViewerInstance } from "@aiden0z/pptx-renderer";

import { readBlobAsArrayBuffer } from "./blob-readers";
import { FilePreviewStatus } from "./FilePreviewStatus";

type PptxRenderState = "loading" | "ready" | "error";

export function PptxFilePreview({ file }: { file: Blob }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<PptxViewerInstance | null>(null);
  const [renderState, setRenderState] = useState<PptxRenderState>("loading");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const abortController = new AbortController();
    let active = true;
    container.replaceChildren();
    setRenderState("loading");

    Promise.all([readBlobAsArrayBuffer(file), import("@aiden0z/pptx-renderer")])
      .then(async ([buffer, { PptxViewer, RECOMMENDED_ZIP_LIMITS }]) => {
        if (!active) {
          return;
        }
        const viewer = await PptxViewer.open(buffer, container, {
          fitMode: "contain",
          lazyMedia: true,
          lazySlides: true,
          listOptions: {
            batchSize: 4,
            initialSlides: 4,
            overscanViewport: 1,
            showSlideLabels: true,
            windowed: true,
          },
          renderMode: "list",
          scrollContainer: container,
          signal: abortController.signal,
          zipLimits: RECOMMENDED_ZIP_LIMITS,
        });
        if (!active) {
          viewer.destroy();
          return;
        }
        viewerRef.current = viewer;
        setRenderState("ready");
      })
      .catch(() => {
        if (active && !abortController.signal.aborted) {
          container.replaceChildren();
          setRenderState("error");
        }
      });

    return () => {
      active = false;
      abortController.abort();
      viewerRef.current?.destroy();
      viewerRef.current = null;
      container.replaceChildren();
    };
  }, [file]);

  return (
    <div className="universal-file-preview__pptx-shell">
      <div className="universal-file-preview__pptx-document" ref={containerRef} />
      {renderState === "loading" ? (
        <FilePreviewStatus message="正在渲染 PowerPoint 演示文稿…" role="status" tone="loading" />
      ) : null}
      {renderState === "error" ? (
        <FilePreviewStatus message="PowerPoint 演示文稿渲染失败，请下载原文件查看。" role="alert" tone="error" />
      ) : null}
    </div>
  );
}
