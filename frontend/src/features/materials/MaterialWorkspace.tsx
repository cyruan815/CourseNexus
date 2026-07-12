import { type FormEvent, type MouseEvent, useEffect, useMemo, useState } from "react";

import { ApiError } from "../../api/errors";
import {
  createMaterialLink,
  createMaterialFolder,
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

type FolderView = "all" | "unfiled" | string;
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

export function MaterialWorkspace({
  courseId,
  materialScope,
  onMaterialScopeChange,
  openUploadPrompt = false,
}: MaterialWorkspaceProps) {
  const [folders, setFolders] = useState<MaterialFolder[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [folderView, setFolderView] = useState<FolderView>("all");
  const [newFolderName, setNewFolderName] = useState("");
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [editingFolderName, setEditingFolderName] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploadPromptOpen, setIsUploadPromptOpen] = useState(openUploadPrompt);
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

  const visibleMaterials = useMemo(() => {
    if (folderView === "all") {
      return materials;
    }
    if (folderView === "unfiled") {
      return materials.filter((material) => material.folder_id === null);
    }
    return materials.filter((material) => material.folder_id === folderView);
  }, [folderView, materials]);

  const parsedMaterialIds = useMemo(
    () => materials.filter((material) => material.parse_status === "parsed").map((material) => material.id),
    [materials],
  );

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

  function handleCreateFolder(event: FormEvent) {
    event.preventDefault();
    const name = newFolderName.trim();
    if (!name) {
      return;
    }
    void mutate(async () => {
      const folder = await createMaterialFolder(courseId, { name });
      setFolders((current) => [...current, folder]);
      setNewFolderName("");
    });
  }

  function handleSaveFolder(folderId: string) {
    const name = editingFolderName.trim();
    if (!name) {
      return;
    }
    void mutate(async () => {
      const folder = await updateMaterialFolder(folderId, { name });
      setFolders((current) => current.map((item) => (item.id === folder.id ? folder : item)));
      setEditingFolderId(null);
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
      if (folderView === folder.id) {
        setFolderView("unfiled");
      }
    });
  }

  function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!uploadFile) {
      return;
    }
    const destination = folderView !== "all" && folderView !== "unfiled" ? folderView : null;
    void mutate(async () => {
      const material = await uploadMaterial(courseId, uploadFile, destination);
      setMaterials((current) => [material, ...current]);
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
    });
  }

  function handleCreateFolderFromMenu() {
    const name = window.prompt("文件夹名称");
    if (!name?.trim()) {
      setContextMenu(null);
      return;
    }

    void mutate(async () => {
      const folder = await createMaterialFolder(courseId, { name: name.trim() });
      setFolders((current) => [...current, folder]);
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

    const folderId = folderView !== "all" && folderView !== "unfiled" ? folderView : null;
    void mutate(async () => {
      const material = await createMaterialLink(courseId, {
        name: name.trim(),
        source_url: sourceUrl.trim(),
        folder_id: folderId,
      });
      setMaterials((current) => [material, ...current]);
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

  return (
    <section aria-label="资料区" className="material-workspace">
      <header className="material-workspace__header">
        <div>
          <h2>课程资料</h2>
          <p>{materials.length} 份资料，{parsedMaterialIds.length} 份可用于 Agent</p>
        </div>
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
      </header>

      {error ? <p role="alert">{error}</p> : null}
      {isLoading ? <p role="status">正在加载资料...</p> : null}

      {isUploadPromptOpen ? (
        <div aria-labelledby="material-upload-dialog-title" className="material-workspace__upload-dialog" role="dialog">
          <div className="material-workspace__upload-dialog-panel">
            <h3 id="material-upload-dialog-title">上传课程资料</h3>
            <p>课程已创建成功，可以现在上传资料；也可以先关闭，之后在课程详情页继续上传。</p>
            <form className="material-workspace__upload" onSubmit={handleUpload}>
              <input
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
        <div className="material-workspace__body">
          <aside aria-label="资料文件夹" className="material-workspace__folders">
            <button aria-pressed={folderView === "all"} onClick={() => setFolderView("all")} type="button">
              全部资料
            </button>
            <button
              aria-pressed={folderView === "unfiled"}
              onClick={() => setFolderView("unfiled")}
              type="button"
            >
              未分类
            </button>
            {folders.map((folder, index) => (
              <div className="material-workspace__folder-row" key={folder.id}>
                {editingFolderId === folder.id ? (
                  <>
                    <input
                      aria-label={`重命名 ${folder.name}`}
                      onChange={(event) => setEditingFolderName(event.target.value)}
                      value={editingFolderName}
                    />
                    <button disabled={isMutating} onClick={() => handleSaveFolder(folder.id)} type="button">
                      保存
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      aria-pressed={folderView === folder.id}
                      onContextMenu={(event) => openFolderMenu(event, folder)}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={() => {
                        if (draggedMaterialId) {
                          handleMoveById(draggedMaterialId, folder.id);
                          setDraggedMaterialId(null);
                        }
                      }}
                      onClick={() => setFolderView(folder.id)}
                      type="button"
                    >
                      {folder.name}
                    </button>
                    <button
                      aria-label={`重命名 ${folder.name}`}
                      onClick={() => {
                        setEditingFolderId(folder.id);
                        setEditingFolderName(folder.name);
                      }}
                      title="重命名"
                      type="button"
                    >
                      编辑
                    </button>
                    <button
                      aria-label={`删除 ${folder.name}`}
                      disabled={isMutating}
                      onClick={() => handleDeleteFolder(folder)}
                      title="删除文件夹"
                      type="button"
                    >
                      删除
                    </button>
                  </>
                )}
                <span>{index + 1}</span>
              </div>
            ))}
            <form onSubmit={handleCreateFolder}>
              <label>
                <span className="material-workspace__sr-only">新建资料文件夹</span>
                <input
                  aria-label="新建资料文件夹"
                  maxLength={255}
                  onChange={(event) => setNewFolderName(event.target.value)}
                  placeholder="文件夹名称"
                  value={newFolderName}
                />
              </label>
              <button disabled={isMutating || !newFolderName.trim()} type="submit">
                新建文件夹
              </button>
            </form>
          </aside>

          <div
            aria-label="资料列表区域"
            className="material-workspace__content"
            onContextMenu={openWorkspaceMenu}
          >
            <form className="material-workspace__upload" onSubmit={handleUpload}>
              <input
                id="material-upload-input"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                type="file"
              />
              <button disabled={isMutating || !uploadFile} type="submit">上传资料</button>
            </form>

            {visibleMaterials.length === 0 ? <p>当前文件夹没有资料</p> : null}
            <ul aria-label="资料列表" className="material-workspace__list">
              {visibleMaterials.map((material) => {
                const isParsed = material.parse_status === "parsed";
                const checked = isParsed &&
                  (materialScope.include_all_parsed_materials || materialScope.material_ids.includes(material.id));
                return (
                  <li
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
                      <span>{material.name}</span>
                    </label>
                    <span className={`material-workspace__status material-workspace__status--${material.parse_status}`}>
                      {statusText(material.parse_status)}
                    </span>
                    <label>
                      <span className="material-workspace__sr-only">{material.name} 所属文件夹</span>
                      <select
                        aria-label={`${material.name} 所属文件夹`}
                        disabled={isMutating}
                        onChange={(event) => handleMove(material, event.target.value || null)}
                        value={material.folder_id ?? ""}
                      >
                        <option value="">未分类</option>
                        {folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}
                      </select>
                    </label>
                    {material.parse_status === "uploaded" || material.parse_status === "parse_failed" ? (
                      <button disabled={isMutating} onClick={() => handleParse(material)} type="button">
                        {material.parse_status === "parse_failed" ? "重试解析" : "开始解析"}
                      </button>
                    ) : null}
                    <button disabled={isMutating} onClick={() => handleDeleteMaterial(material)} type="button">
                      删除
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      ) : null}

      {contextMenu ? (
        <div
          className="material-workspace__context-menu"
          role="menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenu.kind === "workspace" ? (
            <>
              <button onClick={handleCreateFolderFromMenu} role="menuitem" type="button">
                新建文件夹
              </button>
              <button
                onClick={() => {
                  setContextMenu(null);
                  setIsUploadPromptOpen(true);
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
              <button
                onClick={() => {
                  setEditingFolderId(contextMenu.folder.id);
                  setEditingFolderName(contextMenu.folder.name);
                  setContextMenu(null);
                }}
                role="menuitem"
                type="button"
              >
                重命名文件夹
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
