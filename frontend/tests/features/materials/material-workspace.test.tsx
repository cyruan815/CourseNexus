import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
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

function renderWorkspace(ui: ReactElement) {
  render(<MantineProvider>{ui}</MantineProvider>);
}

describe("MaterialWorkspace", () => {
  beforeEach(() => {
    vi.mocked(materialsApi.listMaterialFolders).mockResolvedValue([folder]);
    vi.mocked(materialsApi.listMaterials).mockResolvedValue(materials);
  });

  it("uses folders only for organization and selects individual parsed files", async () => {
    const onScopeChange = vi.fn();

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: false, material_ids: [] }}
        onMaterialScopeChange={onScopeChange}
      />,
    );

    expect(await screen.findByRole("button", { name: /第一周/ })).toBeInTheDocument();
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
    vi.spyOn(window, "prompt").mockReturnValue("考试");
    vi.mocked(materialsApi.createMaterialFolder).mockResolvedValue({ ...folder, id: "fld_2", name: "考试" });
    vi.mocked(materialsApi.moveMaterialToFolder).mockResolvedValue({ ...materials[1], folder_id: "fld_1" });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    await screen.findByText("第一章.pdf");
    fireEvent.click(screen.getByRole("button", { name: "新建文件夹" }));

    await waitFor(() => {
      expect(materialsApi.createMaterialFolder).toHaveBeenCalledWith("crs_1", { name: "考试" });
    });

    fireEvent.dragStart(screen.getByText("待解析.md"));
    fireEvent.drop(screen.getByRole("button", { name: /第一周/ }));
    await waitFor(() => {
      expect(materialsApi.moveMaterialToFolder).toHaveBeenCalledWith("mat_2", "fld_1");
    });
  });

  it("opens and closes the upload prompt when requested by the course creation flow", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
        openUploadPrompt
      />,
    );

    expect(await screen.findByRole("dialog", { name: "上传课程资料" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "暂不上传" }));

    expect(screen.queryByRole("dialog", { name: "上传课程资料" })).not.toBeInTheDocument();
  });

  it("removes a deleted folder and its materials after confirmation", async () => {
    vi.mocked(materialsApi.deleteMaterialFolder).mockResolvedValue({
      ...folder,
      deleted_at: "2026-07-12T00:00:00Z",
    });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    const folderButton = await screen.findByRole("button", { name: /第一周/ });
    fireEvent.contextMenu(folderButton);
    fireEvent.click(screen.getByRole("menuitem", { name: "删除文件夹" }));

    expect(screen.getByRole("dialog", { name: "删除文件夹" })).toHaveTextContent(
      "删除该文件夹后，文件夹下的所有资料和子文件夹也会被一并删除，且无法恢复。",
    );
    expect(materialsApi.deleteMaterialFolder).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(materialsApi.deleteMaterialFolder).toHaveBeenCalledWith("fld_1");
    });
    expect(screen.queryByRole("button", { name: /第一周/ })).not.toBeInTheDocument();
    expect(screen.queryByText("第一章.pdf")).not.toBeInTheDocument();
  });

  it("creates a link material from the workspace context menu", async () => {
    vi.spyOn(window, "prompt")
      .mockReturnValueOnce("课程网站")
      .mockReturnValueOnce("https://example.com/course");
    vi.mocked(materialsApi.createMaterialLink).mockResolvedValue({
      ...materials[1],
      id: "mat_link",
      name: "课程网站",
      source_type: "url",
      material_type: "link",
      file_url: null,
      source_url: "https://example.com/course",
    });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.contextMenu(await screen.findByLabelText("资料列表区域"));
    fireEvent.click(screen.getByRole("menuitem", { name: "添加链接" }));

    await waitFor(() => {
      expect(materialsApi.createMaterialLink).toHaveBeenCalledWith("crs_1", {
        name: "课程网站",
        source_url: "https://example.com/course",
        folder_id: null,
      });
    });
    expect(screen.getByText("课程网站")).toBeInTheDocument();
  });

  it("renames a material from its context menu", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("第一章重命名.pdf");
    vi.mocked(materialsApi.updateMaterial).mockResolvedValue({
      ...materials[0],
      name: "第一章重命名.pdf",
    });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.contextMenu(await screen.findByText("第一章.pdf"));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名资料" }));

    await waitFor(() => {
      expect(materialsApi.updateMaterial).toHaveBeenCalledWith("mat_1", { name: "第一章重命名.pdf" });
    });
    expect(screen.getByText("第一章重命名.pdf")).toBeInTheDocument();
  });

  it("removes a deleted material from the explorer immediately", async () => {
    vi.mocked(materialsApi.deleteMaterial).mockResolvedValue({
      ...materials[0],
      parse_status: "deleted",
      deleted_at: "2026-07-12T00:00:00Z",
    });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: false, material_ids: ["mat_1"] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.contextMenu(await screen.findByText("第一章.pdf"));
    fireEvent.click(screen.getByRole("menuitem", { name: "删除资料" }));

    expect(screen.getByRole("dialog", { name: "删除资料" })).toHaveTextContent(
      "确定删除该资料吗？删除后将无法恢复。",
    );
    expect(materialsApi.deleteMaterial).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(materialsApi.deleteMaterial).toHaveBeenCalledWith("mat_1");
    });
    expect(screen.queryByText("第一章.pdf")).not.toBeInTheDocument();
  });

  it("keeps material data and shows backend errors when deletion fails", async () => {
    vi.mocked(materialsApi.deleteMaterial).mockRejectedValue(new Error("资料索引配置缺失"));

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.contextMenu(await screen.findByText("第一章.pdf"));
    fireEvent.click(screen.getByRole("menuitem", { name: "删除资料" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("资料索引配置缺失");
    expect(screen.getByText("第一章.pdf")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "删除资料" })).toBeInTheDocument();
  });

  it("closes the context menu when left-clicking elsewhere", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.contextMenu(await screen.findByLabelText("资料列表区域"));
    expect(screen.getByRole("menuitem", { name: "添加链接" })).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    expect(screen.queryByRole("menuitem", { name: "添加链接" })).not.toBeInTheDocument();
  });

  it("moves a material by dragging it onto a folder", async () => {
    vi.mocked(materialsApi.moveMaterialToFolder).mockResolvedValue({ ...materials[1], folder_id: "fld_1" });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.dragStart(await screen.findByText("待解析.md"));
    fireEvent.drop(screen.getByRole("button", { name: /第一周/ }));

    await waitFor(() => {
      expect(materialsApi.moveMaterialToFolder).toHaveBeenCalledWith("mat_2", "fld_1");
    });
    expect(screen.getByText("待解析.md")).toBeInTheDocument();
  });
});

