import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState, type ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MaterialWorkspace } from "../../../src/features/materials/MaterialWorkspace";
import * as materialsApi from "../../../src/features/materials/api";
import type { MaterialScope } from "../../../src/features/materials/types";

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

async function openMaterialActions(name = "第一章.pdf") {
  fireEvent.click(await screen.findByRole("button", { name: `${name} 更多操作` }));
}

async function openFolderActions(name = "第一周") {
  fireEvent.click(await screen.findByRole("button", { name: `${name} 更多操作` }));
}

async function findFirstFolderToggle() {
  return screen.findByRole("button", { name: "第一周" });
}

describe("MaterialWorkspace", () => {
  beforeEach(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:material-preview"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.mocked(materialsApi.listMaterialFolders).mockResolvedValue([folder]);
    vi.mocked(materialsApi.listMaterials).mockResolvedValue(materials);
  });

  it("presents the redesigned resource summary without a persistent upload dropzone", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    expect(await screen.findByRole("heading", { name: "课程资料" })).toBeInTheDocument();
    expect(screen.getByText("已选择 0 份资料，共 1 份可用")).toBeInTheDocument();
    expect(screen.getByText("资料选择")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("100 B")).toBeInTheDocument();
    expect(screen.queryByLabelText("拖拽上传课程资料")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "上传资料" }));

    expect(screen.getByRole("dialog", { name: "上传课程资料" })).toBeInTheDocument();
    expect(screen.getByLabelText("拖拽上传课程资料")).toBeInTheDocument();
  });

  it("renders development preview data without calling list APIs", async () => {
    vi.mocked(materialsApi.listMaterialFolders).mockClear();
    vi.mocked(materialsApi.listMaterials).mockClear();

    renderWorkspace(
      <MaterialWorkspace
        courseId="preview-course"
        initialData={{ folders: [folder], materials }}
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    expect(await screen.findByText("第一章.pdf")).toBeInTheDocument();
    expect(materialsApi.listMaterialFolders).not.toHaveBeenCalled();
    expect(materialsApi.listMaterials).not.toHaveBeenCalled();
  });

  it("opens a PDF preview modal when clicking the material name", async () => {
    vi.mocked(materialsApi.getMaterialPdf).mockResolvedValue(
      new Blob(["%PDF-1.4"], { type: "application/pdf" }),
    );

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "预览资料 第一章.pdf" }));

    expect(await screen.findByRole("dialog", { name: "第一章.pdf" })).toBeInTheDocument();
    await waitFor(() => expect(materialsApi.getMaterialPdf).toHaveBeenCalledWith("mat_1"));
    expect(await screen.findByTitle("第一章.pdf PDF 预览")).toHaveAttribute("src", "blob:material-preview");

    fireEvent.click(screen.getByRole("button", { name: "关闭资料预览" }));
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:material-preview");
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

    expect(await findFirstFolderToggle()).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "第一周" })).not.toBeInTheDocument();

    const parsedMaterial = screen.getByRole("checkbox", { name: "选择资料 第一章.pdf" });
    expect(parsedMaterial).toBeEnabled();
    expect(screen.getByRole("checkbox", { name: "选择资料 待解析.md" })).toBeDisabled();

    fireEvent.click(parsedMaterial);
    expect(onScopeChange).toHaveBeenCalledWith({
      include_all_parsed_materials: true,
      material_ids: ["mat_1"],
    });

    fireEvent.click(screen.getByText("待解析.md"));
    expect(await screen.findByRole("alert")).toHaveTextContent("资料需解析成功后才能选择。");
  });

  it("returns to all parsed materials when the last selected material is cleared", async () => {
    const onScopeChange = vi.fn();

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: false, material_ids: ["mat_1"] }}
        onMaterialScopeChange={onScopeChange}
      />,
    );

    const parsedMaterial = await screen.findByRole("checkbox", { name: "选择资料 第一章.pdf" });
    fireEvent.click(parsedMaterial);

    expect(onScopeChange).toHaveBeenCalledWith({
      include_all_parsed_materials: true,
      material_ids: [],
    });
  });

  it("keeps individual material checkboxes empty for the all parsed materials scope", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    expect(await screen.findByRole("checkbox", { name: "全部已解析资料" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "选择资料 第一章.pdf" })).not.toBeChecked();
  });

  it("uses explicit item checks to enter and leave the all parsed materials scope", async () => {
    vi.mocked(materialsApi.listMaterials).mockResolvedValue([
      materials[0],
      {
        ...materials[1],
        id: "mat_2",
        name: "第二章.pdf",
        parse_status: "parsed",
      },
    ]);
    const onScopeChange = vi.fn();

    function ControlledWorkspace() {
      const [scope, setScope] = useState<MaterialScope>({ include_all_parsed_materials: true, material_ids: [] });

      return (
        <MaterialWorkspace
          courseId="crs_1"
          materialScope={scope}
          onMaterialScopeChange={(nextScope) => {
            onScopeChange(nextScope);
            setScope(nextScope);
          }}
        />
      );
    }

    renderWorkspace(<ControlledWorkspace />);

    const allScope = await screen.findByRole("checkbox", { name: "全部已解析资料" });
    const firstMaterial = screen.getByRole("checkbox", { name: "选择资料 第一章.pdf" });
    const secondMaterial = screen.getByRole("checkbox", { name: "选择资料 第二章.pdf" });

    expect(allScope).not.toBeChecked();
    expect(firstMaterial).not.toBeChecked();
    expect(secondMaterial).not.toBeChecked();

    fireEvent.click(firstMaterial);
    expect(onScopeChange).toHaveBeenLastCalledWith({
      include_all_parsed_materials: false,
      material_ids: ["mat_1"],
    });
    expect(firstMaterial).toBeChecked();
    expect(secondMaterial).not.toBeChecked();
    expect(allScope).not.toBeChecked();

    fireEvent.click(secondMaterial);
    expect(onScopeChange).toHaveBeenLastCalledWith({
      include_all_parsed_materials: true,
      material_ids: ["mat_1", "mat_2"],
    });
    expect(firstMaterial).toBeChecked();
    expect(secondMaterial).toBeChecked();
    expect(allScope).toBeChecked();

    fireEvent.click(secondMaterial);
    expect(onScopeChange).toHaveBeenLastCalledWith({
      include_all_parsed_materials: false,
      material_ids: ["mat_1"],
    });
    expect(firstMaterial).toBeChecked();
    expect(secondMaterial).not.toBeChecked();
    expect(allScope).not.toBeChecked();

    fireEvent.click(firstMaterial);
    expect(onScopeChange).toHaveBeenLastCalledWith({
      include_all_parsed_materials: true,
      material_ids: [],
    });
    expect(allScope).not.toBeChecked();
    expect(firstMaterial).not.toBeChecked();
    expect(secondMaterial).not.toBeChecked();
  });

  it("creates folders and moves a material without selecting the folder", async () => {
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
    fireEvent.change(screen.getByRole("textbox", { name: /文件夹名称/ }), { target: { value: "考试" } });
    fireEvent.click(screen.getByRole("button", { name: "确认" }));

    await waitFor(() => {
      expect(materialsApi.createMaterialFolder).toHaveBeenCalledWith("crs_1", { name: "考试" });
    });

    fireEvent.dragStart(screen.getByText("待解析.md"));
    fireEvent.drop(await findFirstFolderToggle());
    await waitFor(() => {
      expect(materialsApi.moveMaterialToFolder).toHaveBeenCalledWith("mat_2", "fld_1");
    });
  });

  it("opens a drag-and-drop upload prompt with a close button when requested by the course creation flow", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
        openUploadPrompt
      />,
    );

    expect(await screen.findByRole("dialog", { name: "上传课程资料" })).toBeInTheDocument();
    expect(screen.getByText("拖拽文件到这里，或点击选择文件")).toBeInTheDocument();
    expect(screen.getByText(/上传后会自动进入解析流程/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "暂不上传" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "关闭上传资料弹窗" }));

    expect(screen.queryByRole("dialog", { name: "上传课程资料" })).not.toBeInTheDocument();
  });

  it("uploads a file selected by dropping it into the upload prompt", async () => {
    const droppedFile = new File(["chapter"], "chapter.pdf", { type: "application/pdf" });
    vi.mocked(materialsApi.uploadMaterial).mockResolvedValue({
      ...materials[1],
      id: "mat_drop",
      name: "chapter.pdf",
      material_type: "pdf",
      mime_type: "application/pdf",
      parse_status: "uploaded",
    });
    vi.mocked(materialsApi.retryParseMaterial).mockResolvedValue({
      ...materials[1],
      id: "mat_drop",
      name: "chapter.pdf",
      material_type: "pdf",
      mime_type: "application/pdf",
      parse_status: "parsing",
    });

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
        openUploadPrompt
      />,
    );

    fireEvent.drop(await screen.findByLabelText("拖拽上传课程资料"), {
      dataTransfer: { files: [droppedFile] },
    });
    fireEvent.click(within(screen.getByRole("dialog", { name: "上传课程资料" })).getByRole("button", { name: "上传资料" }));

    await waitFor(() => {
      expect(materialsApi.uploadMaterial).toHaveBeenCalledWith("crs_1", droppedFile, null);
    });
    await waitFor(() => {
      expect(materialsApi.retryParseMaterial).toHaveBeenCalledWith("mat_drop");
    });
    expect(screen.queryByRole("dialog", { name: "上传课程资料" })).not.toBeInTheDocument();
    expect(screen.getByText("chapter.pdf")).toBeInTheDocument();
    expect(screen.getByText("解析中")).toBeInTheDocument();
  });

  it("opens material actions from a three-dot button without a manual start-parse action", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    await openMaterialActions("待解析.md");

    expect(screen.getByRole("menuitem", { name: "重命名资料" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "删除资料" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "开始解析" })).not.toBeInTheDocument();
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

    await openFolderActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "删除文件夹" }));

    expect(screen.getByRole("dialog", { name: "删除文件夹" })).toHaveTextContent(
      "删除该文件夹后，文件夹下的所有资料也会被一并删除，且无法恢复。",
    );
    expect(materialsApi.deleteMaterialFolder).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(materialsApi.deleteMaterialFolder).toHaveBeenCalledWith("fld_1");
    });
    expect(screen.queryByRole("button", { name: "第一周" })).not.toBeInTheDocument();
    expect(screen.queryByText("第一章.pdf")).not.toBeInTheDocument();
  });

  it("shows the upload target on its own line with a strong folder name", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    await openFolderActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "上传到此文件夹" }));

    const dialog = screen.getByRole("dialog", { name: "上传课程资料" });
    expect(within(dialog).getByText("上传到：")).toBeInTheDocument();
    expect(within(dialog).getByText(folder.name).tagName).toBe("STRONG");
    expect(within(dialog).queryByText(`上传到：${folder.name}。`)).not.toBeInTheDocument();
    expect(within(dialog).getByText(/上传后会自动进入解析流程/)).toBeInTheDocument();
  });

  it("does not expose workspace actions from right-clicking the resource list", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    const resourceList = await screen.findByLabelText("资料列表区域");
    fireEvent.contextMenu(resourceList);

    expect(screen.queryByRole("menuitem", { name: "新建文件夹" })).not.toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "添加链接" })).not.toBeInTheDocument();
    expect(screen.queryByText(/右键/)).not.toBeInTheDocument();
  });

  it("does not open folder actions from right-clicking a folder row", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.contextMenu(await findFirstFolderToggle());

    expect(screen.queryByRole("menuitem", { name: "删除文件夹" })).not.toBeInTheDocument();
  });

  it("keeps folder actions in the folder header without a persistent upload area", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    const folderAction = await screen.findByRole("button", { name: "第一周 更多操作" });

    expect(folderAction.closest(".material-workspace__folder-head")).not.toBeNull();
    expect(screen.queryByText("可在顶部按钮新建文件夹、上传资料或添加链接")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("拖拽上传课程资料")).not.toBeInTheDocument();
  });

  it("creates a link material from the top action button", async () => {
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

    fireEvent.click(await screen.findByRole("button", { name: "添加链接" }));
    fireEvent.change(screen.getByRole("textbox", { name: /资料名称/ }), { target: { value: "课程网站" } });
    fireEvent.change(screen.getByRole("textbox", { name: /资料链接/ }), {
      target: { value: "https://example.com/course" },
    });
    fireEvent.click(screen.getByRole("button", { name: "确认" }));

    await waitFor(() => {
      expect(materialsApi.createMaterialLink).toHaveBeenCalledWith("crs_1", {
        name: "课程网站",
        source_url: "https://example.com/course",
        folder_id: null,
      });
    });
    expect(screen.getByText("课程网站")).toBeInTheDocument();
  });

  it("renames a material from its actions menu", async () => {
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

    await openMaterialActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名资料" }));
    fireEvent.change(screen.getByRole("textbox", { name: /资料名称/ }), { target: { value: "第一章重命名.pdf" } });
    fireEvent.click(screen.getByRole("button", { name: "确认" }));

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

    await openMaterialActions();
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

    await openMaterialActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "删除资料" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("资料索引配置缺失");
    expect(screen.getByText("第一章.pdf")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "删除资料" })).toBeInTheDocument();
  });

  it("closes the material actions menu when left-clicking elsewhere", async () => {
    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    await openMaterialActions();
    expect(screen.getByRole("menuitem", { name: "重命名资料" })).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    expect(screen.queryByRole("menuitem", { name: "重命名资料" })).not.toBeInTheDocument();
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
    fireEvent.drop(await findFirstFolderToggle());

    await waitFor(() => {
      expect(materialsApi.moveMaterialToFolder).toHaveBeenCalledWith("mat_2", "fld_1");
    });
    expect(screen.getByText("待解析.md")).toBeInTheDocument();
  });

  it("keeps material data and shows backend errors when moving fails", async () => {
    vi.mocked(materialsApi.moveMaterialToFolder).mockRejectedValue(new Error("资料索引配置缺失"));

    renderWorkspace(
      <MaterialWorkspace
        courseId="crs_1"
        materialScope={{ include_all_parsed_materials: true, material_ids: [] }}
        onMaterialScopeChange={vi.fn()}
      />,
    );

    fireEvent.dragStart(await screen.findByText("待解析.md"));
    fireEvent.drop(await findFirstFolderToggle());

    expect(await screen.findByRole("alert")).toHaveTextContent("资料索引配置缺失");
    expect(screen.getByText("待解析.md")).toBeInTheDocument();
  });
});
