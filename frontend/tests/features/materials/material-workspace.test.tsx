import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MaterialWorkspace } from "../../../src/features/materials/MaterialWorkspace";
import * as materialsApi from "../../../src/features/materials/api";

vi.mock("../../../src/features/materials/api");

const folder = {
  id: "fld_1",
  user_id: "usr_1",
  course_id: "crs_1",
  name: "第一周",
  sort_order: 1,
  created_at: "2026-07-10T00:00:00Z",
  updated_at: "2026-07-10T00:00:00Z",
  deleted_at: null,
};

const materials = [
  {
    id: "mat_1",
    course_id: "crs_1",
    user_id: "usr_1",
    folder_id: "fld_1",
    name: "第一章.pdf",
    material_type: "pdf",
    source_type: "file",
    file_url: "stored/source.pdf",
    source_url: null,
    file_size: 100,
    mime_type: "application/pdf",
    parse_status: "parsed",
    parse_error: null,
    page_count: 10,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
    deleted_at: null,
  },
  {
    id: "mat_2",
    course_id: "crs_1",
    user_id: "usr_1",
    folder_id: null,
    name: "待解析.md",
    material_type: "markdown",
    source_type: "file",
    file_url: "stored/source.md",
    source_url: null,
    file_size: 20,
    mime_type: "text/markdown",
    parse_status: "uploaded",
    parse_error: null,
    page_count: null,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
    deleted_at: null,
  },
];

describe("MaterialWorkspace", () => {
  beforeEach(() => {
    vi.mocked(materialsApi.listMaterialFolders).mockResolvedValue([folder]);
    vi.mocked(materialsApi.listMaterials).mockResolvedValue(materials);
  });

  it("uses folders only for organization and selects individual parsed files", async () => {
    const onScopeChange = vi.fn();

    render(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: false, material_ids: [] }}
        onMaterialScopeChange={onScopeChange}
      />,
    );

    expect(await screen.findByRole("button", { name: "第一周" })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "第一周" })).not.toBeInTheDocument();

    const parsedMaterial = screen.getByRole("checkbox", { name: "选择资料 第一章.pdf" });
    expect(parsedMaterial).toBeEnabled();
    expect(screen.getByRole("checkbox", { name: "选择资料 待解析.md" })).toBeDisabled();

    fireEvent.click(parsedMaterial);
    expect(onScopeChange).toHaveBeenCalledWith({
      include_all_parsed_materials: false,
      material_ids: ["mat_1"],
    });
  });

  it("creates folders and moves a material without selecting the folder", async () => {
    vi.mocked(materialsApi.createMaterialFolder).mockResolvedValue({ ...folder, id: "fld_2", name: "考试" });
    vi.mocked(materialsApi.moveMaterialToFolder).mockResolvedValue({ ...materials[1], folder_id: "fld_1" });

    render(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    await screen.findByText("第一章.pdf");
    fireEvent.change(screen.getByLabelText("新建资料文件夹"), { target: { value: "考试" } });
    fireEvent.click(screen.getByRole("button", { name: "新建文件夹" }));

    await waitFor(() => {
      expect(materialsApi.createMaterialFolder).toHaveBeenCalledWith("crs_1", { name: "考试" });
    });

    fireEvent.change(screen.getByLabelText("待解析.md 所属文件夹"), { target: { value: "fld_1" } });
    await waitFor(() => {
      expect(materialsApi.moveMaterialToFolder).toHaveBeenCalledWith("mat_2", "fld_1");
    });
  });
});
