import { useState } from "react";

import { MaterialWorkspace } from "../features/materials/MaterialWorkspace";
import type { Material, MaterialFolder, MaterialScope } from "../features/materials/types";
import type { Course } from "../types/course";
import { CourseDetailWorkbench } from "./CourseDetailPage";
import "./course-detail.css";

const previewTimestamp = "2026-07-15T08:00:00Z";

const previewCourse: Course = {
  id: "preview-course",
  user_id: "preview-user",
  name: "计算机网络",
  description: "围绕课程资料构建可追溯的问答与学习路径。",
  teacher: "王老师",
  term: "2026 SPRING",
  status: "active",
  created_at: previewTimestamp,
  updated_at: previewTimestamp,
  deleted_at: null,
};

const previewFolders: MaterialFolder[] = [
  {
    id: "preview-folder-01",
    user_id: "preview-user",
    course_id: "preview-course",
    name: "01 基础概念",
    sort_order: 1,
    created_at: previewTimestamp,
    updated_at: previewTimestamp,
    deleted_at: null,
  },
  {
    id: "preview-folder-02",
    user_id: "preview-user",
    course_id: "preview-course",
    name: "02 物理层",
    sort_order: 2,
    created_at: previewTimestamp,
    updated_at: previewTimestamp,
    deleted_at: null,
  },
];

function previewMaterial(
  id: string,
  folderId: string | null,
  name: string,
  materialType: string,
  fileSize: number,
  parseStatus = "parsed",
  parseError: string | null = parseStatus === "parse_failed" ? "示例解析失败" : null,
): Material {
  return {
    id,
    course_id: "preview-course",
    user_id: "preview-user",
    folder_id: folderId,
    name,
    material_type: materialType,
    source_type: "file",
    file_url: `preview/${name}`,
    source_url: null,
    file_size: fileSize,
    mime_type: materialType === "pdf" ? "application/pdf" : "application/octet-stream",
    parse_status: parseStatus,
    parse_error: parseError,
    active_parse_version_id: parseStatus === "parsed" || parseStatus === "parsing" ? `mpv-${id}` : null,
    is_learning_ready: parseStatus === "parsed" || parseStatus === "parsing",
    page_count: materialType === "pdf" ? 12 : null,
    created_at: previewTimestamp,
    updated_at: previewTimestamp,
    deleted_at: null,
  };
}

const previewMaterials: Material[] = [
  previewMaterial("preview-u1", null, "课程教学大纲.pdf", "pdf", 1_840_000),
  previewMaterial("preview-u2", null, "课程说明.txt", "text", 4_800),
  previewMaterial("preview-u3", null, "学习资源索引.md", "markdown", 12_600),
  previewMaterial("preview-11", "preview-folder-01", "第一章 绪论.pdf", "pdf", 3_100_000),
  previewMaterial("preview-12", "preview-folder-01", "第二章 数据通信基础.pdf", "pdf", 4_800_000),
  previewMaterial("preview-13", "preview-folder-01", "核心概念清单.md", "markdown", 26_700),
  previewMaterial("preview-14", "preview-folder-01", "基础概念练习.pptx", "powerpoint", 9_200_000),
  previewMaterial("preview-15", "preview-folder-01", "参考链接汇总.txt", "text", 8_600),
  previewMaterial("preview-21", "preview-folder-02", "Chap7 物理层.pdf", "pdf", 3_800_000),
  previewMaterial("preview-22", "preview-folder-02", "信号、信道与带宽补充讲义.pdf", "pdf", 5_300_000),
  previewMaterial("preview-23", "preview-folder-02", "数据编码与调制方法.pptx", "powerpoint", 12_700_000),
  previewMaterial("preview-24", "preview-folder-02", "物理层重点清单.md", "markdown", 33_200),
  previewMaterial("preview-25", "preview-folder-02", "实验一说明.pdf", "pdf", 2_100_000, "parsing"),
  previewMaterial("preview-26", "preview-folder-02", "旧版课件.pdf", "pdf", 2_500_000, "parse_failed"),
  previewMaterial("preview-27", "preview-folder-02", "课堂例题.docx", "word", 880_000, "parsed", "INDEXING_FAILED"),
];

const previewData = {
  expandedFolderIds: ["preview-folder-02"],
  folders: previewFolders,
  materials: previewMaterials,
};

export function CourseDetailPreviewPage() {
  const [materialScope, setMaterialScope] = useState<MaterialScope>({
    include_all_parsed_materials: true,
    material_ids: [],
  });

  return (
    <CourseDetailWorkbench
      course={previewCourse}
      materialPanel={(
        <MaterialWorkspace
          courseId={previewCourse.id}
          initialData={previewData}
          materialScope={materialScope}
          onMaterialScopeChange={setMaterialScope}
        />
      )}
      materialScope={materialScope}
      qaMessages={[
        { content: "物理层的主要作用是什么？", id: "preview-question", role: "user" },
        {
          answerType: "grounded",
          citations: [{
            chunk_id: "preview-chunk",
            hit_text: "物理层负责在传输介质上传输原始比特流，并定义机械、电气、功能和过程特性。",
            material_id: "preview-material",
            material_name: "Chap7 物理层.pdf",
            page: "12",
            page_index: 11,
          }],
          content: "物理层负责在传输介质上传输原始比特流，并规定接口的机械、电气、功能与过程特性。 [[cite:1]]",
          id: "preview-answer",
          role: "assistant",
          status: "done",
        },
      ]}
    />
  );
}
