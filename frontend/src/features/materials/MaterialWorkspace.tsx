import { type FormEvent, type MouseEvent, useEffect, useMemo, useState } from "react";

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

  function handleCreateFolder() {
    const name = window.prompt("文件夹名称");
    if (!name?.trim()) {
      return;
    }
    void mutate(async () => {
      const folder = await createMaterialFolder(courseId, { name: name.trim() });
      setFolders((current) => [...current, folder]);
      setExpandedFolderIds((current) => new Set([...current, folder.id]));
    });
  }

  function handleRenameFolder(folder: MaterialFolder) {
    const name = window.prompt("文件夹名称", folder.name);
    if (!name?.trim() || name.trim() === folder.name) {
      setContextMenu(null);
      return;
    }
    void mutate(async () => {
      const nextFolder = await updateMaterialFolder(folder.id, { name: name.trim() });
      setFolders((current) => current.map((item) => (item.id === nextFolder.id ? nextFolder : item)));
    });
  }

  function handleDeleteFolder(folder: MaterialFolder) {
    if (!window.confirm(`删除文件夹“${folder.name}”？其中资料会回到未分类。`)) {
      return;
    }
    void mutate(async () => {
      await deleteMaterialFolder(folder.id);
      setFolders((current) => current.filter((item) => item.id !== folder.id));
      setMaterials((current) =>
        current.map((material) => (material.folder_id === folder.id ? { ...material, folder_id: null } : material)),
      );
      setExpandedFolderIds((current) => {
        const next = new Set(current);
        next.delete(folder.id);
        next.add("unfiled");
        return next;
      });
    });
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

  function handleCreateLink() {
    const name = window.prompt("资料名称");
    if (!name?.trim()) {
      setContextMenu(null);
      return;
    }

    const sourceUrl = window.prompt("资料链接");
    if (!sourceUrl?.trim()) {
      setContextMenu(null);
      return;
    }

    void mutate(async () => {
      const material = await createMaterialLink(courseId, {
        name: name.trim(),
        source_url: sourceUrl.trim(),
        folder_id: null,
      });
      setMaterials((current) => [material, ...current]);
      setExpandedFolderIds((current) => new Set([...current, material.folder_id ?? "unfiled"]));
    });
  }

  function handleRenameMaterial(material: Material) {
    const name = window.prompt("资料名称", material.name);
    if (!name?.trim() || name.trim() === material.name) {
      setContextMenu(null);
      return;
    }

    void mutate(async () => {
      updateMaterial(await renameMaterial(material.id, { name: name.trim() }));
    });
  }

  function handleParse(material: Material) {
    void mutate(async () => {
      updateMaterial(await retryParseMaterial(material.id));
    });
  }

  function handleDeleteMaterial(material: Material) {
    if (!window.confirm(`删除资料“${material.name}”？`)) {
      return;
    }
    void mutate(async () => {
      await deleteMaterial(material.id);
      setMaterials((current) => current.filter((item) => item.id !== material.id));
      if (!materialScope.include_all_parsed_materials) {
        onMaterialScopeChange({
          include_all_parsed_materials: false,
          material_ids: materialScope.material_ids.filter((id) => id !== material.id),
        });
      }
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
        <label className="material-workspace__material-select">
          <input
            aria-label={`选择资料 ${material.name}`}
            checked={checked}
            disabled={!isParsed}
            onChange={() => toggleMaterial(material.id)}
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
          <button disabled={isMutating} onClick={handleCreateFolder} type="button">
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
            <h3 id="material-upload-dialog-title">上传课程资料</h3>
            <p>资料将上传到：{uploadTargetName}。也可以先关闭，之后在课程详情页继续上传。</p>
            <form className="material-workspace__upload" onSubmit={handleUpload}>
              <input
                id="material-upload-input"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                type="file"
              />
              <button disabled={isMutating || !uploadFile} type="submit">上传资料</button>
            </form>
            <button disabled={isMutating} onClick={() => setIsUploadPromptOpen(false)} type="button">
              暂不上传
            </button>
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

          <div
            aria-label="资料列表区域"
            className="material-workspace__content"
            onContextMenu={openWorkspaceMenu}
          >
            {renderFolderSection("unfiled", "未分类")}
            {folders.map((folder) => renderFolderSection(folder.id, folder.name, folder))}
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
              <button onClick={handleCreateFolder} role="menuitem" type="button">
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
              <button onClick={handleCreateLink} role="menuitem" type="button">
                添加链接
              </button>
            </>
          ) : null}
          {contextMenu.kind === "folder" ? (
            <>
              <button onClick={() => handleRenameFolder(contextMenu.folder)} role="menuitem" type="button">
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
              <button onClick={() => handleDeleteFolder(contextMenu.folder)} role="menuitem" type="button">
                删除文件夹
              </button>
            </>
          ) : null}
          {contextMenu.kind === "material" ? (
            <>
              <button onClick={() => handleRenameMaterial(contextMenu.material)} role="menuitem" type="button">
                重命名资料
              </button>
              {contextMenu.material.parse_status === "uploaded" || contextMenu.material.parse_status === "parse_failed" ? (
                <button onClick={() => handleParse(contextMenu.material)} role="menuitem" type="button">
                  {contextMenu.material.parse_status === "parse_failed" ? "重试解析" : "开始解析"}
                </button>
              ) : null}
              <button onClick={() => handleDeleteMaterial(contextMenu.material)} role="menuitem" type="button">
                删除资料
              </button>
            </>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
