import { useEffect, useMemo, useState } from "react";
import { IconDownload, IconFileAlert } from "@tabler/icons-react";

import { filePreviewKindLabel, resolveFilePreviewKind } from "./file-types";
import type { FilePreviewKind } from "./file-types";
import "./universal-file-preview.css";

const TEXT_PREVIEW_LIMIT_BYTES = 2 * 1024 * 1024;

export interface UniversalFilePreviewProps {
  file: Blob;
  fileName: string;
  initialPage?: number | null;
  materialType?: string | null;
  mimeType?: string | null;
}

export function UniversalFilePreview({
  file,
  fileName,
  initialPage,
  materialType,
  mimeType,
}: UniversalFilePreviewProps) {
  const kind = useMemo(
    () => resolveFilePreviewKind({ fileName, materialType, mimeType: mimeType ?? file.type }),
    [file.type, fileName, materialType, mimeType],
  );
  const objectUrl = useObjectUrl(file);

  return (
    <section aria-label={`${fileName} 文件预览`} className="universal-file-preview">
      <header className="universal-file-preview__toolbar">
        <div className="universal-file-preview__identity">
          <span className={`universal-file-preview__kind universal-file-preview__kind--${kind}`}>
            {filePreviewKindLabel(kind)}
          </span>
          <span className="universal-file-preview__name" title={fileName}>
            {fileName}
          </span>
        </div>
        <a
          aria-disabled={!objectUrl}
          className="universal-file-preview__download"
          download={fileName}
          href={objectUrl ?? undefined}
        >
          <IconDownload aria-hidden size={17} stroke={1.8} />
          下载原文件
        </a>
      </header>
      <div className={`universal-file-preview__viewport universal-file-preview__viewport--${kind}`}>
        <PreviewBody file={file} fileName={fileName} initialPage={initialPage} kind={kind} objectUrl={objectUrl} />
      </div>
    </section>
  );
}

function PreviewBody({
  file,
  fileName,
  initialPage,
  kind,
  objectUrl,
}: {
  file: Blob;
  fileName: string;
  initialPage?: number | null;
  kind: FilePreviewKind;
  objectUrl: string | null;
}) {
  if (!objectUrl) {
    return <PreviewState message="正在准备文件预览…" role="status" />;
  }
  if (kind === "pdf") {
    const pageFragment = initialPage && initialPage > 0 ? `#page=${Math.floor(initialPage)}&view=FitH` : "";
    return <iframe src={`${objectUrl}${pageFragment}`} title={`${fileName} PDF 预览`} />;
  }
  if (kind === "image") {
    return <img alt={fileName} className="universal-file-preview__image" src={objectUrl} />;
  }
  if (kind === "text") {
    return <TextFilePreview file={file} />;
  }
  if (kind === "docx" || kind === "pptx") {
    return <PreviewState message={`${filePreviewKindLabel(kind)} 预览器正在准备接入`} role="status" />;
  }
  return <PreviewState message="暂不支持在页面内预览此格式，请下载原文件查看。" />;
}

function TextFilePreview({ file }: { file: Blob }) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const isTruncated = file.size > TEXT_PREVIEW_LIMIT_BYTES;

  useEffect(() => {
    let active = true;
    setContent(null);
    setError(false);
    readBlobAsText(file.slice(0, TEXT_PREVIEW_LIMIT_BYTES))
      .then((text) => {
        if (active) {
          setContent(text);
        }
      })
      .catch(() => {
        if (active) {
          setError(true);
        }
      });
    return () => {
      active = false;
    };
  }, [file]);

  if (error) {
    return <PreviewState message="文本读取失败，请下载原文件查看。" role="alert" />;
  }
  if (content === null) {
    return <PreviewState message="正在读取文本…" role="status" />;
  }
  return (
    <article className="universal-file-preview__text-document">
      {isTruncated ? <p className="universal-file-preview__truncated">文件较长，仅展示前 2 MiB。</p> : null}
      <pre>{content}</pre>
    </article>
  );
}

function readBlobAsText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(reader.error ?? new Error("File read failed"));
    reader.readAsText(blob);
  });
}

function PreviewState({ message, role }: { message: string; role?: "alert" | "status" }) {
  return (
    <div className="universal-file-preview__state" role={role}>
      <span className="universal-file-preview__state-icon" aria-hidden>
        <IconFileAlert size={25} stroke={1.7} />
      </span>
      <p>{message}</p>
    </div>
  );
}

function useObjectUrl(file: Blob): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const nextUrl = URL.createObjectURL(file);
    setUrl(nextUrl);
    return () => {
      URL.revokeObjectURL(nextUrl);
    };
  }, [file]);

  return url;
}
