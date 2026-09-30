export type FilePreviewKind = "pdf" | "docx" | "pptx" | "image" | "text" | "unsupported";

interface FileTypeHint {
  fileName: string;
  materialType?: string | null;
  mimeType?: string | null;
}

const MATERIAL_TYPE_KIND: Record<string, FilePreviewKind> = {
  image: "image",
  markdown: "text",
  pdf: "pdf",
  powerpoint: "pptx",
  ppt: "pptx",
  presentation: "pptx",
  text: "text",
  word: "docx",
};

const EXTENSION_KIND: Record<string, FilePreviewKind> = {
  docx: "docx",
  jpeg: "image",
  jpg: "image",
  md: "text",
  pdf: "pdf",
  png: "image",
  pptx: "pptx",
  txt: "text",
};

export function resolveFilePreviewKind({
  fileName,
  materialType,
  mimeType,
}: FileTypeHint): FilePreviewKind {
  const normalizedMaterialType = materialType?.trim().toLowerCase();
  if (normalizedMaterialType && MATERIAL_TYPE_KIND[normalizedMaterialType]) {
    return MATERIAL_TYPE_KIND[normalizedMaterialType];
  }

  const normalizedMimeType = mimeType?.split(";", 1)[0]?.trim().toLowerCase();
  if (normalizedMimeType === "application/pdf") {
    return "pdf";
  }
  if (normalizedMimeType === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
    return "docx";
  }
  if (normalizedMimeType === "application/vnd.openxmlformats-officedocument.presentationml.presentation") {
    return "pptx";
  }
  if (normalizedMimeType?.startsWith("image/")) {
    return "image";
  }
  if (normalizedMimeType?.startsWith("text/")) {
    return "text";
  }

  const extension = fileName.trim().toLowerCase().match(/\.([^.]+)$/)?.[1];
  return extension ? (EXTENSION_KIND[extension] ?? "unsupported") : "unsupported";
}

export function filePreviewKindLabel(kind: FilePreviewKind): string {
  const labels: Record<FilePreviewKind, string> = {
    docx: "Word",
    image: "图片",
    pdf: "PDF",
    pptx: "PowerPoint",
    text: "文本",
    unsupported: "文件",
  };
  return labels[kind];
}
