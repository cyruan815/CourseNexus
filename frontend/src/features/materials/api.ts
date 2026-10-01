import { apiFileRequest, apiRequest } from "../../api/client";
import type {
  Material,
  MaterialFolder,
  MaterialFolderCreate,
  MaterialFolderUpdate,
  MaterialUpdate,
} from "./types";

export function listMaterials(courseId: string): Promise<Material[]> {
  return apiRequest<Material[]>(`/api/v1/courses/${courseId}/materials`, { method: "GET" });
}

export function getMaterial(materialId: string): Promise<Material> {
  return apiRequest<Material>(`/api/v1/materials/${materialId}`, { method: "GET" });
}

export async function getMaterialFile(materialId: string, signal?: AbortSignal): Promise<Blob> {
  const file = await apiFileRequest(`/api/v1/materials/${materialId}/content`, { signal });
  return file.blob;
}

export function uploadMaterial(courseId: string, file: File, folderId: string | null): Promise<Material> {
  const body = new FormData();
  body.append("file", file);
  if (folderId) {
    body.append("folder_id", folderId);
  }
  return apiRequest<Material>(`/api/v1/courses/${courseId}/materials`, { method: "POST", body });
}

export function updateMaterial(materialId: string, payload: MaterialUpdate): Promise<Material> {
  return apiRequest<Material>(`/api/v1/materials/${materialId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function retryParseMaterial(materialId: string): Promise<Material> {
  return apiRequest<Material>(`/api/v1/materials/${materialId}/parse-retries`, { method: "POST" });
}

export function deleteMaterial(materialId: string): Promise<Material> {
  return apiRequest<Material>(`/api/v1/materials/${materialId}`, { method: "DELETE" });
}

export function listMaterialFolders(courseId: string): Promise<MaterialFolder[]> {
  return apiRequest<MaterialFolder[]>(`/api/v1/courses/${courseId}/material-folders`, { method: "GET" });
}

export function createMaterialFolder(
  courseId: string,
  payload: MaterialFolderCreate,
): Promise<MaterialFolder> {
  return apiRequest<MaterialFolder>(`/api/v1/courses/${courseId}/material-folders`, {
    method: "POST",
    body: payload,
  });
}

export function updateMaterialFolder(
  folderId: string,
  payload: MaterialFolderUpdate,
): Promise<MaterialFolder> {
  return apiRequest<MaterialFolder>(`/api/v1/material-folders/${folderId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteMaterialFolder(folderId: string): Promise<MaterialFolder> {
  return apiRequest<MaterialFolder>(`/api/v1/material-folders/${folderId}`, { method: "DELETE" });
}

export function moveMaterialToFolder(materialId: string, folderId: string | null): Promise<Material> {
  return apiRequest<Material>(`/api/v1/materials/${materialId}/folder`, {
    method: "PATCH",
    body: { folder_id: folderId },
  });
}
