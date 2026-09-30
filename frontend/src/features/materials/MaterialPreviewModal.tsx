import { useEffect, useState } from "react";
import { Alert, Button, Loader, Modal } from "@mantine/core";

import { UniversalFilePreview } from "../../components/file-preview";
import { ApiError } from "../../api/errors";
import { getMaterialFile } from "./api";
import type { Material } from "./types";
import "./material-preview-modal.css";

interface MaterialPreviewModalProps {
  material: Material | null;
  onClose: () => void;
}

function previewErrorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return "资料原文件加载失败";
}

export function MaterialPreviewModal({ material, onClose }: MaterialPreviewModalProps) {
  const [file, setFile] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!material) {
      setFile(null);
      setError(null);
      return;
    }

    const abortController = new AbortController();
    setFile(null);
    setError(null);
    getMaterialFile(material.id, abortController.signal)
      .then((nextFile) => {
        if (!abortController.signal.aborted) {
          setFile(nextFile);
        }
      })
      .catch((nextError: unknown) => {
        if (!abortController.signal.aborted) {
          setError(previewErrorMessage(nextError));
        }
      });

    return () => {
      abortController.abort();
    };
  }, [material, reloadToken]);

  const accessibleTitle = material ? `预览 · ${material.name}` : "资料预览";

  return (
    <Modal
      centered
      classNames={{
        body: "material-preview-modal__body",
        content: "material-preview-modal__content",
        header: "material-preview-modal__header",
        title: "material-preview-modal__title",
      }}
      closeButtonProps={{ "aria-label": "关闭资料预览" }}
      onClose={onClose}
      opened={Boolean(material)}
      size="min(1240px, calc(100vw - 32px))"
      title={accessibleTitle}
      transitionProps={{ duration: 0 }}
    >
      <div className="material-preview-modal__stage">
        {material && !file && !error ? (
          <div className="material-preview-modal__loading" role="status">
            <Loader color="blue" size="sm" />
            <div>
              <strong>正在加载原文件</strong>
              <span>{material.name}</span>
            </div>
          </div>
        ) : null}
        {material && error ? (
          <Alert className="material-preview-modal__error" color="red" role="alert" title="预览加载失败" variant="light">
            <p>{error}</p>
            <Button color="red" onClick={() => setReloadToken((current) => current + 1)} size="xs" variant="light">
              重新加载
            </Button>
          </Alert>
        ) : null}
        {material && file ? (
          <UniversalFilePreview
            file={file}
            fileName={material.name}
            materialType={material.material_type}
            mimeType={material.mime_type}
          />
        ) : null}
      </div>
    </Modal>
  );
}
