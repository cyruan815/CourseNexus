import { type DragEvent, type FormEvent, type MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text, TextInput, Tooltip } from "@mantine/core";
import {
  IconAlertCircle,
  IconCheck,
  IconChevronDown,
  IconDotsVertical,
  IconFolder,
  IconFolderPlus,
  IconLink,
  IconLoader2,
  IconSearch,
  IconUpload,
  IconX,
} from "@tabler/icons-react";

import { ApiError } from "../../api/errors";
import {
  createMaterialFolder,
  createMaterialLink,
  deleteMaterial,
  deleteMaterialFolder,
  getMaterialPdf,
  listMaterialFolders,
  listMaterials,
  moveMaterialToFolder,
  retryParseMaterial,
  updateMaterial as renameMaterial,
  updateMaterialFolder,
  uploadMaterial,
} from "./api";
import type { Material, MaterialFolder, MaterialScope } from "./types";
import "./material-workspace.css";

type ContextMenu =
  | { folder: MaterialFolder; kind: "folder"; x: number; y: number }
  | { kind: "material"; material: Material; x: number; y: number }
  | null;
type DeleteTarget =
  | { kind: "folder"; folder: MaterialFolder }
  | { kind: "material"; material: Material }
  | null;
type ActionTarget =
  | { kind: "createFolder" }
  | { folder: MaterialFolder; kind: "renameFolder" }
  | { kind: "createLink" }
  | { kind: "renameMaterial"; material: Material }
  | null;

interface MaterialWorkspaceProps {
  courseId: string;
  initialData?: {
    expandedFolderIds?: string[];
    folders: MaterialFolder[];
    materials: Material[];
  };
  materialScope: MaterialScope;
  onParsedMaterialsChange?: (materials: Material[]) => void;
  onMaterialScopeChange: (scope: MaterialScope) => void;
  openUploadPrompt?: boolean;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return "资料操作失败";
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    uploaded: "待解析",
    parsing: "解析中",
    parsed: "可使用",
    parse_failed: "解析失败",
  };
  return labels[status] ?? status;
}

function materialMatchesSearch(material: Material, query: string): boolean {
  return material.name.toLowerCase().includes(query.toLowerCase());
}

function materialKind(material: Material): string {
  if (material.source_type === "url") {
    return "URL";
  }
  const normalizedType = material.material_type.toLowerCase();
  const labels: Record<string, string> = {
    markdown: "MD",
    powerpoint: "PPTX",
    presentation: "PPTX",
    text: "TXT",
    word: "DOCX",
  };
  return labels[normalizedType] ?? (normalizedType.slice(0, 4).toUpperCase() || "FILE");
}

export function MaterialWorkspace({
  courseId,
  initialData,
  materialScope,
  onParsedMaterialsChange,
  onMaterialScopeChange,
  openUploadPrompt = false,
}: MaterialWorkspaceProps) {
  const [folders, setFolders] = useState<MaterialFolder[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [expandedFolderIds, setExpandedFolderIds] = useState<Set<string>>(() => new Set(["unfiled"]));
  const [searchQuery, setSearchQuery] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploadPromptOpen, setIsUploadPromptOpen] = useState(openUploadPrompt);
  const [uploadTargetFolderId, setUploadTargetFolderId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenu>(null);
  const [draggedMaterialId, setDraggedMaterialId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionTarget, setActionTarget] = useState<ActionTarget>(null);
  const [actionName, setActionName] = useState("");
  const [actionUrl, setActionUrl] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewMaterial, setPreviewMaterial] = useState<Material | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const previewRequestId = useRef(0);

  useEffect(() => {
    if (initialData) {
      setFolders(initialData.folders);
      setMaterials(initialData.materials);
      setExpandedFolderIds(new Set(initialData.expandedFolderIds ?? ["unfiled", ...initialData.folders.map((folder) => folder.id)]));
      setError(null);
      setIsLoading(false);
      return undefined;
    }

    let ignore = false;
    setIsLoading(true);
    Promise.all([listMaterialFolders(courseId), listMaterials(courseId)])
      .then(([nextFolders, nextMaterials]) => {
        if (!ignore) {
          setFolders(nextFolders);
          setMaterials(nextMaterials);
          setExpandedFolderIds(new Set(["unfiled", ...nextFolders.map((folder) => folder.id)]));
          setError(null);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [courseId, initialData]);

  useEffect(() => {
    if (!contextMenu) {
      return undefined;
    }

    function closeContextMenu() {
      setContextMenu(null);
    }

    document.addEventListener("mousedown", closeContextMenu);
    return () => document.removeEventListener("mousedown", closeContextMenu);
  }, [contextMenu]);

  useEffect(
    () => () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    },
    [previewUrl],
  );

  const parsedMaterialIds = useMemo(
    () => materials.filter((material) => material.parse_status === "parsed").map((material) => material.id),
    [materials],
  );
  const checkedParsedMaterialIds = materialScope.material_ids.filter((id) => parsedMaterialIds.includes(id));
  const isExplicitAllParsedScope =
    parsedMaterialIds.length > 0 && checkedParsedMaterialIds.length === parsedMaterialIds.length;

  const parsedMaterials = useMemo(
    () => materials.filter((material) => material.parse_status === "parsed"),
    [materials],
  );

  useEffect(() => {
    onParsedMaterialsChange?.(parsedMaterials);
  }, [onParsedMaterialsChange, parsedMaterials]);

  const searchedMaterials = useMemo(
    () => materials.filter((material) => materialMatchesSearch(material, searchQuery.trim())),
    [materials, searchQuery],
  );

  const materialsByFolder = useMemo(() => {
    const grouped = new Map<string, Material[]>();
    grouped.set("unfiled", []);
    for (const folder of folders) {
      grouped.set(folder.id, []);
    }
    for (const material of searchedMaterials) {
      grouped.get(material.folder_id ?? "unfiled")?.push(material);
    }
    return grouped;
  }, [folders, searchedMaterials]);

  async function mutate(action: () => Promise<void>) {
    setIsMutating(true);
    setError(null);
    try {
      await action();
      setContextMenu(null);
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setIsMutating(false);
    }
  }

  function updateMaterial(nextMaterial: Material) {
    setMaterials((current) => current.map((material) => (material.id === nextMaterial.id ? nextMaterial : material)));
  }

  function toggleMaterial(materialId: string) {
    const selected = checkedParsedMaterialIds.includes(materialId);
    const nextMaterialIds = selected
      ? checkedParsedMaterialIds.filter((id) => id !== materialId)
      : [...checkedParsedMaterialIds, materialId];
    onMaterialScopeChange({
      include_all_parsed_materials:
        nextMaterialIds.length === 0 || nextMaterialIds.length === parsedMaterialIds.length,
      material_ids: nextMaterialIds,
    });
  }

  function toggleFolder(folderId: string) {
    setExpandedFolderIds((current) => {
      const next = new Set(current);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  }

  function openUploadDialog(folderId: string | null = null) {
    setUploadTargetFolderId(folderId);
    setUploadFile(null);
    setIsUploadPromptOpen(true);
  }

  function closeUploadDialog() {
    if (isMutating) {
      return;
    }
    setIsUploadPromptOpen(false);
    setUploadFile(null);
  }

  function openCreateFolderModal() {
    setContextMenu(null);
    setActionTarget({ kind: "createFolder" });
    setActionName("");
    setActionUrl("");
    setActionError(null);
  }

  function openRenameFolderModal(folder: MaterialFolder) {
    setContextMenu(null);
    setActionTarget({ folder, kind: "renameFolder" });
    setActionName(folder.name);
    setActionUrl("");
    setActionError(null);
  }

  function openCreateLinkModal() {
    setContextMenu(null);
    setActionTarget({ kind: "createLink" });
    setActionName("");
    setActionUrl("");
    setActionError(null);
  }

  function openRenameMaterialModal(material: Material) {
    setContextMenu(null);
    setActionTarget({ kind: "renameMaterial", material });
    setActionName(material.name);
    setActionUrl("");
    setActionError(null);
  }

  function closeActionModal() {
    if (isMutating) {
      return;
    }
    setActionTarget(null);
    setActionError(null);
  }

  function submitActionModal() {
    if (!actionTarget) {
      return;
    }

    const name = actionName.trim();
    const sourceUrl = actionUrl.trim();

    if (!name) {
      setActionError(actionTarget.kind === "createLink" ? "资料名称不能为空" : "文件夹名称不能为空");
      return;
    }
    if (actionTarget.kind === "createLink" && !sourceUrl) {
      setActionError("资料链接不能为空");
      return;
    }

    void mutate(async () => {
      if (actionTarget.kind === "createFolder") {
        const folder = await createMaterialFolder(courseId, { name });
        setFolders((current) => [...current, folder]);
        setExpandedFolderIds((current) => new Set([...current, folder.id]));
      } else if (actionTarget.kind === "renameFolder") {
        const nextFolder = await updateMaterialFolder(actionTarget.folder.id, { name });
        setFolders((current) => current.map((item) => (item.id === nextFolder.id ? nextFolder : item)));
      } else if (actionTarget.kind === "createLink") {
        const material = await createMaterialLink(courseId, {
          name,
          source_url: sourceUrl,
          folder_id: null,
        });
        setMaterials((current) => [material, ...current]);
        setExpandedFolderIds((current) => new Set([...current, material.folder_id ?? "unfiled"]));
      } else if (actionTarget.kind === "renameMaterial") {
        updateMaterial(await renameMaterial(actionTarget.material.id, { name }));
      }
      setActionTarget(null);
      setActionError(null);
    });
  }

  function requestDeleteFolder(folder: MaterialFolder) {
    setContextMenu(null);
    setDeleteError(null);
    setDeleteTarget({ kind: "folder", folder });
  }

  function requestDeleteMaterial(material: Material) {
    setContextMenu(null);
    setDeleteError(null);
    setDeleteTarget({ kind: "material", material });
  }

  function closeDeleteModal() {
    if (isDeleting) {
      return;
    }
    setDeleteTarget(null);
    setDeleteError(null);
  }

  async function confirmDeleteTarget() {
    if (!deleteTarget) {
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);

    try {
      if (deleteTarget.kind === "folder") {
        const folderId = deleteTarget.folder.id;
        await deleteMaterialFolder(folderId);
        const removedMaterialIds = materials
          .filter((material) => material.folder_id === folderId)
          .map((material) => material.id);
        setFolders((current) => current.filter((item) => item.id !== folderId));
        setMaterials((current) => current.filter((material) => material.folder_id !== folderId));
        setExpandedFolderIds((current) => {
          const next = new Set(current);
          next.delete(folderId);
          return next;
        });
        if (!materialScope.include_all_parsed_materials && removedMaterialIds.length > 0) {
          const nextMaterialIds = materialScope.material_ids.filter((id) => !removedMaterialIds.includes(id));
          onMaterialScopeChange({
            include_all_parsed_materials: nextMaterialIds.length === 0,
            material_ids: nextMaterialIds,
          });
        }
      } else {
        const materialId = deleteTarget.material.id;
        await deleteMaterial(materialId);
        setMaterials((current) => current.filter((item) => item.id !== materialId));
        if (!materialScope.include_all_parsed_materials) {
          const nextMaterialIds = materialScope.material_ids.filter((id) => id !== materialId);
          onMaterialScopeChange({
            include_all_parsed_materials: nextMaterialIds.length === 0,
            material_ids: nextMaterialIds,
          });
        }
      }
      setDeleteTarget(null);
    } catch (nextError) {
      setDeleteError(errorMessage(nextError));
    } finally {
      setIsDeleting(false);
    }
  }

  function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!uploadFile) {
      return;
    }
    void mutate(async () => {
      const material = await uploadMaterial(courseId, uploadFile, uploadTargetFolderId);
      const insertedMaterial: Material =
        material.parse_status === "uploaded" ? { ...material, parse_status: "parsing" } : material;
      setMaterials((current) => [insertedMaterial, ...current]);
      setExpandedFolderIds((current) => new Set([...current, material.folder_id ?? "unfiled"]));
      setIsUploadPromptOpen(false);
      setUploadFile(null);
      const input = document.getElementById("material-upload-input") as HTMLInputElement | null;
      if (input) {
        input.value = "";
      }
      if (material.parse_status === "uploaded") {
        try {
          updateMaterial(await retryParseMaterial(material.id));
        } catch (parseError) {
          updateMaterial(material);
          setError(errorMessage(parseError));
        }
      }
    });
  }

  function handleUploadDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      setUploadFile(file);
    }
  }

  function handleMove(material: Material, folderId: string | null) {
    void mutate(async () => {
      updateMaterial(await moveMaterialToFolder(material.id, folderId));
      setExpandedFolderIds((current) => new Set([...current, folderId ?? "unfiled"]));
    });
  }

  function handleMoveById(materialId: string, folderId: string | null) {
    const material = materials.find((item) => item.id === materialId);
    if (material) {
      handleMove(material, folderId);
    }
  }

  function openFolderMenu(event: MouseEvent<HTMLElement>, folder: MaterialFolder) {
    event.preventDefault();
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    setContextMenu({ folder, kind: "folder", x: Math.max(8, rect.right - 148), y: rect.bottom + 4 });
  }

  function openMaterialMenu(event: MouseEvent<HTMLElement>, material: Material) {
    event.preventDefault();
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    setContextMenu({ kind: "material", material, x: Math.max(8, rect.right - 148), y: rect.bottom + 4 });
  }

  function handleParse(material: Material) {
    void mutate(async () => {
      updateMaterial(await retryParseMaterial(material.id));
    });
  }

  async function openPdfPreview(material: Material) {
    const requestId = previewRequestId.current + 1;
    previewRequestId.current = requestId;
    setPreviewMaterial(material);
    setPreviewUrl(null);
    setPreviewError(null);
    setIsPreviewLoading(true);
    try {
      const blob = await getMaterialPdf(material.id);
      const objectUrl = URL.createObjectURL(blob);
      if (previewRequestId.current !== requestId) {
        URL.revokeObjectURL(objectUrl);
        return;
      }
      setPreviewUrl(objectUrl);
    } catch (nextError) {
      if (previewRequestId.current === requestId) {
        setPreviewError(errorMessage(nextError));
      }
    } finally {
      if (previewRequestId.current === requestId) {
        setIsPreviewLoading(false);
      }
    }
  }

  function closePdfPreview() {
    previewRequestId.current += 1;
    setPreviewMaterial(null);
    setPreviewUrl(null);
    setPreviewError(null);
    setIsPreviewLoading(false);
  }

  function renderMaterialRow(material: Material) {
    const isParsed = material.parse_status === "parsed";
    const checked = isParsed && materialScope.material_ids.includes(material.id);
    const kind = materialKind(material);
    const status = statusText(material.parse_status);
    const StatusIcon = material.parse_status === "parsed"
      ? IconCheck
      : material.parse_status === "parse_failed"
        ? IconAlertCircle
        : IconLoader2;

    return (
      <li
        className="material-workspace__file-row"
        draggable
        key={material.id}
        onDragStart={() => setDraggedMaterialId(material.id)}
      >
        <div
          className="material-workspace__material-select"
          onClick={(event) => {
            if (!isParsed) {
              event.preventDefault();
              setError("资料需解析成功后才能选择。");
            }
          }}
        >
          <input
            aria-label={`选择资料 ${material.name}`}
            checked={checked}
            disabled={!isParsed}
            onChange={() => toggleMaterial(material.id)}
            title={isParsed ? "选择资料" : "资料需解析成功后才能选择"}
            type="checkbox"
          />
          <span
            className={`material-workspace__file-icon${material.source_type === "url" ? " material-workspace__file-icon--link" : ""}`}
            aria-hidden
          >
            {kind}
          </span>
          <span className="material-workspace__file-copy">
            {material.source_type === "file" && material.material_type === "pdf" ? (
              <button
                aria-label={`预览资料 ${material.name}`}
                className="material-workspace__file-name material-workspace__file-name-button"
                onClick={(event) => {
                  event.stopPropagation();
                  void openPdfPreview(material);
                }}
                type="button"
              >
                {material.name}
              </button>
            ) : (
              <span className="material-workspace__file-name">{material.name}</span>
            )}
          </span>
        </div>
        <span
          aria-label={status}
          className={`material-workspace__status material-workspace__status--${material.parse_status}`}
          title={status}
        >
          <StatusIcon
            className={material.parse_status === "parsed" || material.parse_status === "parse_failed" ? undefined : "is-spinning"}
            size={17}
            stroke={2}
          />
          <span className="material-workspace__sr-only">{status}</span>
        </span>
        <button
          aria-label={`${material.name} 更多操作`}
          className="material-workspace__file-actions"
          disabled={isMutating}
          onClick={(event) => openMaterialMenu(event, material)}
          type="button"
        >
          <IconDotsVertical size={18} stroke={1.8} />
        </button>
      </li>
    );
  }

  function renderFolderSection(folderId: string, folderName: string, folder?: MaterialFolder) {
    const folderMaterials = materialsByFolder.get(folderId) ?? [];
    const isExpanded = expandedFolderIds.has(folderId);

    return (
      <section
        className="material-workspace__folder-section"
        key={folderId}
        onDragOver={(event) => event.preventDefault()}
        onDrop={() => {
          if (draggedMaterialId) {
            handleMoveById(draggedMaterialId, folder?.id ?? null);
            setDraggedMaterialId(null);
          }
        }}
      >
        <div className="material-workspace__folder-head">
          <button
            aria-label={folderName}
            aria-expanded={isExpanded}
            className="material-workspace__folder-title"
            onClick={() => toggleFolder(folderId)}
            type="button"
          >
            <IconChevronDown
              className={`material-workspace__folder-chevron${isExpanded ? " is-expanded" : ""}`}
              size={20}
              stroke={1.8}
            />
            <span className="material-workspace__folder-icon" aria-hidden>
              <IconFolder size={21} stroke={1.8} />
            </span>
            <span className="material-workspace__folder-copy">
              <span className="material-workspace__folder-name">{folderName}</span>
              <span className="material-workspace__folder-meta">{folder ? "资料文件夹" : "默认文件夹"}</span>
            </span>
          </button>
          <span className="material-workspace__folder-count">{folderMaterials.length}</span>
          {folder ? (
            <button
              aria-label={`${folderName} 更多操作`}
              className="material-workspace__folder-actions"
              disabled={isMutating}
              onClick={(event) => openFolderMenu(event, folder)}
              type="button"
            >
              <IconDotsVertical size={18} stroke={1.8} />
            </button>
          ) : null}
        </div>
        {isExpanded ? (
          folderMaterials.length > 0 ? (
            <ul aria-label={`${folderName} 资料列表`} className="material-workspace__file-list">
              {folderMaterials.map(renderMaterialRow)}
            </ul>
          ) : (
            <p className="material-workspace__empty-row">这里还没有资料</p>
          )
        ) : null}
      </section>
    );
  }

  const uploadTargetName = uploadTargetFolderId
    ? folders.find((folder) => folder.id === uploadTargetFolderId)?.name ?? "所选文件夹"
    : "未分类";

  return (
    <section aria-label="资料区" className="material-workspace">
      <header className="material-workspace__header">
        <div className="material-workspace__title-group">
          <h2>课程资料</h2>
          <p>已选择 {checkedParsedMaterialIds.length} 份资料，共 {parsedMaterialIds.length} 份可用</p>
        </div>
        <div className="material-workspace__header-actions">
          <Tooltip label="新建文件夹" openDelay={250} position="bottom" withArrow>
            <button
              aria-label="新建文件夹"
              className="material-workspace__action-button"
              disabled={isMutating}
              onClick={openCreateFolderModal}
              type="button"
            >
              <IconFolderPlus aria-hidden size={19} stroke={1.8} />
            </button>
          </Tooltip>
          <Tooltip label="上传资料" openDelay={250} position="bottom" withArrow>
            <button
              aria-label="上传资料"
              className="material-workspace__action-button"
              disabled={isMutating}
              onClick={() => openUploadDialog(null)}
              type="button"
            >
              <IconUpload aria-hidden size={19} stroke={1.8} />
            </button>
          </Tooltip>
          <Tooltip label="添加链接" openDelay={250} position="bottom" withArrow>
            <button
              aria-label="添加链接"
              className="material-workspace__action-button"
              disabled={isMutating}
              onClick={openCreateLinkModal}
              type="button"
            >
              <IconLink aria-hidden size={19} stroke={1.8} />
            </button>
          </Tooltip>
        </div>
      </header>

      {error ? <p role="alert">{error}</p> : null}
      {isLoading ? <p role="status">正在加载资料...</p> : null}

      {isUploadPromptOpen ? (
        <div aria-labelledby="material-upload-dialog-title" className="material-workspace__upload-dialog" role="dialog">
          <div className="material-workspace__upload-dialog-panel">
            <div className="material-workspace__upload-dialog-head">
              <div>
                <h3 id="material-upload-dialog-title">上传课程资料</h3>
                <p className="material-workspace__upload-target">
                  <span>上传到：</span>
                  <strong>{uploadTargetName}</strong>
                </p>
                <p>上传后会自动进入解析流程，解析完成后可用于问答、生成内容和学习计划。</p>
              </div>
              <button
                aria-label="关闭上传资料弹窗"
                className="material-workspace__upload-close"
                disabled={isMutating}
                onClick={closeUploadDialog}
                type="button"
              >
                <IconX size={18} stroke={1.8} />
              </button>
            </div>
            <form className="material-workspace__upload" onSubmit={handleUpload}>
              <label
                aria-label="拖拽上传课程资料"
                className="material-workspace__dropzone"
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleUploadDrop}
              >
                <IconUpload size={28} stroke={1.6} />
                <span className="material-workspace__dropzone-title">拖拽文件到这里，或点击选择文件</span>
                <span className="material-workspace__dropzone-hint">支持 PDF、Markdown、文本和常见课程资料文件</span>
                <input
                  id="material-upload-input"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                  type="file"
                />
              </label>
              {uploadFile ? (
                <Text c="dimmed" size="sm">
                  已选择：{uploadFile.name}
                </Text>
              ) : null}
              <button className="material-workspace__upload-submit" disabled={isMutating || !uploadFile} type="submit">
                上传资料
              </button>
            </form>
          </div>
        </div>
      ) : null}

      {!isLoading ? (
        <div className="material-workspace__body">
          <div className="material-workspace__selection-bar">
            <span>资料选择</span>
            <label className="material-workspace__scope-all">
              <input
                aria-label="全部已解析资料"
                checked={isExplicitAllParsedScope}
                onChange={() =>
                  onMaterialScopeChange({
                    include_all_parsed_materials: true,
                    material_ids: isExplicitAllParsedScope ? [] : parsedMaterialIds,
                  })
                }
                type="checkbox"
              />
              全部
            </label>
          </div>
          <div className="material-workspace__explorer">
          <div className="material-workspace__toolbar">
            <label className="material-workspace__search">
              <span className="material-workspace__sr-only">搜索资料</span>
              <IconSearch aria-hidden size={21} stroke={1.8} />
              <input
                aria-label="搜索资料"
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索资料"
                value={searchQuery}
              />
              {searchQuery ? (
                <button aria-label="清空搜索" onClick={() => setSearchQuery("")} type="button">
                  <IconX size={17} stroke={1.8} />
                </button>
              ) : null}
            </label>
          </div>

          <div aria-label="资料列表区域" className="material-workspace__content">
            {renderFolderSection("unfiled", "未分类")}
            {folders.map((folder) => renderFolderSection(folder.id, folder.name, folder))}
          </div>
          </div>
        </div>
      ) : null}

      {contextMenu ? (
        <div
          className="material-workspace__context-menu"
          onMouseDown={(event) => event.stopPropagation()}
          role="menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenu.kind === "folder" ? (
            <>
              <button onClick={() => openRenameFolderModal(contextMenu.folder)} role="menuitem" type="button">
                重命名文件夹
              </button>
              <button
                onClick={() => {
                  setContextMenu(null);
                  openUploadDialog(contextMenu.folder.id);
                }}
                role="menuitem"
                type="button"
              >
                上传到此文件夹
              </button>
              <button onClick={() => requestDeleteFolder(contextMenu.folder)} role="menuitem" type="button">
                删除文件夹
              </button>
            </>
          ) : null}
          {contextMenu.kind === "material" ? (
            <>
              <button onClick={() => openRenameMaterialModal(contextMenu.material)} role="menuitem" type="button">
                重命名资料
              </button>
              {contextMenu.material.parse_status === "parse_failed" ? (
                <button onClick={() => handleParse(contextMenu.material)} role="menuitem" type="button">
                  重试解析
                </button>
              ) : null}
              <button onClick={() => requestDeleteMaterial(contextMenu.material)} role="menuitem" type="button">
                删除资料
              </button>
            </>
          ) : null}
        </div>
      ) : null}
      <DeleteConfirmModal
        error={deleteError}
        isSubmitting={isDeleting}
        onClose={closeDeleteModal}
        onConfirm={confirmDeleteTarget}
        target={deleteTarget}
      />
      <ActionModal
        error={actionError}
        isSubmitting={isMutating}
        name={actionName}
        onChangeName={setActionName}
        onChangeUrl={setActionUrl}
        onClose={closeActionModal}
        onSubmit={submitActionModal}
        target={actionTarget}
        url={actionUrl}
      />
      <PdfPreviewModal
        error={previewError}
        isLoading={isPreviewLoading}
        material={previewMaterial}
        onClose={closePdfPreview}
        url={previewUrl}
      />
    </section>
  );
}

function PdfPreviewModal({
  error,
  isLoading,
  material,
  onClose,
  url,
}: {
  error: string | null;
  isLoading: boolean;
  material: Material | null;
  onClose: () => void;
  url: string | null;
}) {
  return (
    <Modal
      centered
      classNames={{ body: "material-workspace__preview-body", content: "material-workspace__preview-modal" }}
      closeButtonProps={{ "aria-label": "关闭资料预览" }}
      onClose={onClose}
      opened={Boolean(material)}
      size="min(1120px, calc(100vw - 32px))"
      title={material?.name}
      transitionProps={{ duration: 0 }}
    >
      <div className="material-workspace__preview-content">
        {isLoading ? <Text role="status">正在加载 PDF...</Text> : null}
        {error ? (
          <Alert color="red" role="alert" title="预览失败" variant="light">
            {error}
          </Alert>
        ) : null}
        {url && material ? <iframe src={url} title={`${material.name} PDF 预览`} /> : null}
      </div>
    </Modal>
  );
}

function DeleteConfirmModal({
  error,
  isSubmitting,
  onClose,
  onConfirm,
  target,
}: {
  error: string | null;
  isSubmitting: boolean;
  onClose: () => void;
  onConfirm: () => void;
  target: DeleteTarget;
}) {
  const isFolder = target?.kind === "folder";
  const title = isFolder ? "删除文件夹" : "删除资料";
  const message = isFolder
    ? "删除该文件夹后，文件夹下的所有资料也会被一并删除，且无法恢复。"
    : "确定删除该资料吗？删除后将无法恢复。";

  return (
    <Modal centered onClose={onClose} opened={Boolean(target)} title={title} transitionProps={{ duration: 0 }}>
      <Stack gap="md">
        {error ? (
          <Alert color="red" role="alert" title="删除失败" variant="light">
            {error}
          </Alert>
        ) : null}
        <Text>{message}</Text>
        <Group justify="flex-end">
          <Button disabled={isSubmitting} onClick={onClose} variant="default">
            取消
          </Button>
          <Button color="red" loading={isSubmitting} onClick={onConfirm}>
            确认删除
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function ActionModal({
  error,
  isSubmitting,
  name,
  onChangeName,
  onChangeUrl,
  onClose,
  onSubmit,
  target,
  url,
}: {
  error: string | null;
  isSubmitting: boolean;
  name: string;
  onChangeName: (value: string) => void;
  onChangeUrl: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  target: ActionTarget;
  url: string;
}) {
  const titleMap: Record<NonNullable<ActionTarget>["kind"], string> = {
    createFolder: "新建文件夹",
    createLink: "添加链接资料",
    renameFolder: "重命名文件夹",
    renameMaterial: "重命名资料",
  };
  const isLink = target?.kind === "createLink";
  const isRenameMaterial = target?.kind === "renameMaterial";
  const label = isLink || isRenameMaterial ? "资料名称" : "文件夹名称";
  const canSubmit = Boolean(name.trim()) && (!isLink || Boolean(url.trim())) && !isSubmitting;

  return (
    <Modal
      centered
      onClose={onClose}
      opened={Boolean(target)}
      title={target ? titleMap[target.kind] : undefined}
      transitionProps={{ duration: 0 }}
    >
      <Stack gap="md">
        {error ? (
          <Alert color="red" role="alert" title="操作失败" variant="light">
            {error}
          </Alert>
        ) : null}
        <TextInput
          data-autofocus
          label={label}
          maxLength={255}
          onChange={(event) => onChangeName(event.currentTarget.value)}
          required
          value={name}
        />
        {isLink ? (
          <TextInput
            label="资料链接"
            maxLength={2048}
            onChange={(event) => onChangeUrl(event.currentTarget.value)}
            required
            value={url}
          />
        ) : null}
        <Group justify="flex-end">
          <Button disabled={isSubmitting} onClick={onClose} variant="default">
            取消
          </Button>
          <Button disabled={!canSubmit} loading={isSubmitting} onClick={onSubmit}>
            确认
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
