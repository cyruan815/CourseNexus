import { type DragEvent, type FormEvent, type MouseEvent, useEffect, useMemo, useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { IconUpload, IconX } from "@tabler/icons-react";

import { ApiError } from "../../api/errors";
import {
  createMaterialFolder,
  createMaterialLink,
  deleteMaterial,
  deleteMaterialFolder,
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
  | { kind: "workspace"; x: number; y: number }
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
  materialScope: MaterialScope;
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

export function MaterialWorkspace({
  courseId,
  materialScope,
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

  useEffect(() => {
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
  }, [courseId]);

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

  const parsedMaterialIds = useMemo(
    () => materials.filter((material) => material.parse_status === "parsed").map((material) => material.id),
    [materials],
  );

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
    if (materialScope.include_all_parsed_materials) {
      onMaterialScopeChange({
        include_all_parsed_materials: false,
        material_ids: parsedMaterialIds.filter((id) => id !== materialId),
      });
      return;
    }
    const selected = materialScope.material_ids.includes(materialId);
    onMaterialScopeChange({
      include_all_parsed_materials: false,
      material_ids: selected
        ? materialScope.material_ids.filter((id) => id !== materialId)
        : [...materialScope.material_ids, materialId],
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
          onMaterialScopeChange({
            include_all_parsed_materials: false,
            material_ids: materialScope.material_ids.filter((id) => !removedMaterialIds.includes(id)),
          });
        }
      } else {
        const materialId = deleteTarget.material.id;
        await deleteMaterial(materialId);
        setMaterials((current) => current.filter((item) => item.id !== materialId));
        if (!materialScope.include_all_parsed_materials) {
          onMaterialScopeChange({
            include_all_parsed_materials: false,
            material_ids: materialScope.material_ids.filter((id) => id !== materialId),
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
      setMaterials((current) => [material, ...current]);
      setExpandedFolderIds((current) => new Set([...current, material.folder_id ?? "unfiled"]));
      setIsUploadPromptOpen(false);
      setUploadFile(null);
      const input = document.getElementById("material-upload-input") as HTMLInputElement | null;
      if (input) {
        input.value = "";
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

  function openWorkspaceMenu(event: MouseEvent<HTMLElement>) {
    event.preventDefault();
    setContextMenu({ kind: "workspace", x: event.clientX, y: event.clientY });
  }

  function openFolderMenu(event: MouseEvent<HTMLElement>, folder: MaterialFolder) {
    event.preventDefault();
    event.stopPropagation();
    setContextMenu({ folder, kind: "folder", x: event.clientX, y: event.clientY });
  }

  function openMaterialMenu(event: MouseEvent<HTMLElement>, material: Material) {
    event.preventDefault();
    event.stopPropagation();
    setContextMenu({ kind: "material", material, x: event.clientX, y: event.clientY });
  }

  function handleParse(material: Material) {
    void mutate(async () => {
      updateMaterial(await retryParseMaterial(material.id));
    });
  }

  function renderMaterialRow(material: Material) {
    const isParsed = material.parse_status === "parsed";
    const checked = isParsed &&
      (materialScope.include_all_parsed_materials || materialScope.material_ids.includes(material.id));

    return (
      <li
        className="material-workspace__file-row"
        draggable
        key={material.id}
        onContextMenu={(event) => openMaterialMenu(event, material)}
        onDragStart={() => setDraggedMaterialId(material.id)}
      >
        <label
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
          <span className="material-workspace__file-icon" aria-hidden>
            {material.source_type === "url" ? "Link" : "File"}
          </span>
          <span className="material-workspace__file-name">{material.name}</span>
        </label>
        <span className={`material-workspace__status material-workspace__status--${material.parse_status}`}>
          {statusText(material.parse_status)}
        </span>
      </li>
    );
  }

  function renderFolderSection(folderId: string, folderName: string, folder?: MaterialFolder) {
    const folderMaterials = materialsByFolder.get(folderId) ?? [];
    const isExpanded = expandedFolderIds.has(folderId);
    const contextMenuHandler = folder
      ? (event: MouseEvent<HTMLElement>) => openFolderMenu(event, folder)
      : undefined;

    return (
      <section
        className="material-workspace__folder-section"
        key={folderId}
        onContextMenu={contextMenuHandler}
        onDragOver={(event) => event.preventDefault()}
        onDrop={() => {
          if (draggedMaterialId) {
            handleMoveById(draggedMaterialId, folder?.id ?? null);
            setDraggedMaterialId(null);
          }
        }}
      >
        <button
          aria-expanded={isExpanded}
          className="material-workspace__folder-title"
          onClick={() => toggleFolder(folderId)}
          type="button"
        >
          <span className="material-workspace__folder-chevron" aria-hidden>
            {isExpanded ? "v" : ">"}
          </span>
          <span className="material-workspace__folder-icon" aria-hidden>
            Folder
          </span>
          <span>{folderName}</span>
          <span className="material-workspace__folder-count">{folderMaterials.length}</span>
        </button>
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
        <div>
          <h2>课程资料</h2>
          <p>{materials.length} 份资料，{parsedMaterialIds.length} 份可用于 Agent</p>
        </div>
        <div className="material-workspace__header-actions">
          <button disabled={isMutating} onClick={openCreateFolderModal} type="button">
            新建文件夹
          </button>
          <button disabled={isMutating} onClick={() => openUploadDialog(null)} type="button">
            上传资料
          </button>
          <label className="material-workspace__scope-all">
            <input
              checked={materialScope.include_all_parsed_materials}
              onChange={(event) =>
                onMaterialScopeChange({
                  include_all_parsed_materials: event.target.checked,
                  material_ids: [],
                })
              }
              type="checkbox"
            />
            全部已解析资料
          </label>
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
                <p>
                  上传到：{uploadTargetName}。上传后会自动进入解析流程，解析完成后可用于问答、生成内容和学习计划。
                </p>
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
        <div className="material-workspace__explorer">
          <div className="material-workspace__toolbar">
            <label>
              <span className="material-workspace__sr-only">搜索资料</span>
              <input
                aria-label="搜索资料"
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索资料"
                value={searchQuery}
              />
            </label>
          </div>

          <div aria-label="资料列表区域" className="material-workspace__content" onContextMenu={openWorkspaceMenu}>
            {renderFolderSection("unfiled", "未分类")}
            {folders.map((folder) => renderFolderSection(folder.id, folder.name, folder))}
            <div className="material-workspace__context-zone">
              <Text c="dimmed" size="sm">
                在这里右键新建文件夹、上传资料或添加链接
              </Text>
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
          {contextMenu.kind === "workspace" ? (
            <>
              <button onClick={openCreateFolderModal} role="menuitem" type="button">
                新建文件夹
              </button>
              <button
                onClick={() => {
                  setContextMenu(null);
                  openUploadDialog(null);
                }}
                role="menuitem"
                type="button"
              >
                上传资料
              </button>
              <button onClick={openCreateLinkModal} role="menuitem" type="button">
                添加链接
              </button>
            </>
          ) : null}
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
              {contextMenu.material.parse_status === "uploaded" || contextMenu.material.parse_status === "parse_failed" ? (
                <button onClick={() => handleParse(contextMenu.material)} role="menuitem" type="button">
                  {contextMenu.material.parse_status === "parse_failed" ? "重试解析" : "开始解析"}
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
    </section>
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
