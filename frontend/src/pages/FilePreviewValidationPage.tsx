import { useMemo, useState } from "react";

import { UniversalFilePreview } from "../components/file-preview";
import "./file-preview-validation-page.css";

export function FilePreviewValidationPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const selectedFile = useMemo(
    () => files.find((file) => file.name === selectedName) ?? files[0] ?? null,
    [files, selectedName],
  );

  return (
    <main className="file-preview-validation-page">
      <header className="file-preview-validation-page__header">
        <div>
          <span className="file-preview-validation-page__eyebrow">CourseNexus · Release validation</span>
          <h1>真实文件预览验收</h1>
          <p>选择 PDF、DOCX、PPTX、图片或文本文件，直接验证项目统一预览组件。</p>
        </div>
        <label className="file-preview-validation-page__picker">
          <span>选择预览文件</span>
          <input
            accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg,.gif,.webp,.txt,.md,.csv,.json"
            aria-label="选择预览文件"
            multiple
            onChange={(event) => {
              const nextFiles = Array.from(event.currentTarget.files ?? []);
              setFiles(nextFiles);
              setSelectedName(nextFiles[0]?.name ?? null);
            }}
            type="file"
          />
        </label>
      </header>

      {files.length > 1 ? (
        <nav aria-label="已选择文件" className="file-preview-validation-page__tabs">
          {files.map((file) => (
            <button
              aria-pressed={selectedFile?.name === file.name}
              className={selectedFile?.name === file.name ? "is-active" : undefined}
              key={file.name}
              onClick={() => setSelectedName(file.name)}
              type="button"
            >
              {file.name}
            </button>
          ))}
        </nav>
      ) : null}

      <section className="file-preview-validation-page__stage">
        {selectedFile ? (
          <UniversalFilePreview
            file={selectedFile}
            fileName={selectedFile.name}
            mimeType={selectedFile.type}
          />
        ) : (
          <div className="file-preview-validation-page__empty">
            <strong>等待选择真实文件</strong>
            <span>文件只在当前浏览器标签页中读取，不会上传。</span>
          </div>
        )}
      </section>
    </main>
  );
}
