import { describe, expect, it, vi } from "vitest";

import {
  askCourseQuestion,
  deleteGeneratedContent,
  generateCourseContent,
  getGeneratedContent,
  listCourseConversations,
  listConversationMessages,
  listGeneratedContents,
  listStudyPlans,
  renameGeneratedContent,
  updateKnowledgeItemLearningState,
} from "../../../src/features/course-workspace/api";
import type { MaterialScope } from "../../../src/features/materials/types";

const scope: MaterialScope = {
  include_all_parsed_materials: true,
  material_ids: [],
};

function successResponse(data: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify({ data, meta: { request_id: "req_1" } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("course workspace api", () => {
  it("calls course qa endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => successResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await listCourseConversations("crs_1");
    await listConversationMessages("cnv_1");
    await askCourseQuestion("crs_1", {
      conversation_id: null,
      material_scope: scope,
      question: "什么是模型？",
      source_page: "course_detail",
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/courses/crs_1/conversations",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/conversations/cnv_1/messages",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/courses/crs_1/qa/questions",
      expect.objectContaining({
        body: JSON.stringify({
          conversation_id: null,
          material_scope: scope,
          question: "什么是模型？",
          source_page: "course_detail",
        }),
        method: "POST",
      }),
    );
  });

  it("calls generation and study plan endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => successResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await listGeneratedContents("crs_1");
    await getGeneratedContent("gen_1");
    await renameGeneratedContent("gen_1", "新标题");
    await deleteGeneratedContent("gen_1");
    await generateCourseContent("crs_1", {
      content_type: "outline",
      material_scope: scope,
      parameters: {},
    });
    await listStudyPlans("crs_1");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/courses/crs_1/generated-contents",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/generated-contents/gen_1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/generated-contents/gen_1",
      expect.objectContaining({ body: JSON.stringify({ title: "新标题" }), method: "PATCH" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/generated-contents/gen_1",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/v1/courses/crs_1/generations",
      expect.objectContaining({
        body: JSON.stringify({
          content_type: "outline",
          material_scope: scope,
          parameters: {},
        }),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      "/api/v1/courses/crs_1/study-plans",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("updates one knowledge item's learning state", async () => {
    const generatedContent = { id: "gen_1", content_json: { items: [] } };
    const fetchMock = vi.fn().mockImplementation(() => successResponse(generatedContent));
    vi.stubGlobal("fetch", fetchMock);

    await expect(updateKnowledgeItemLearningState("gen_1", "kp_001", true)).resolves.toEqual(generatedContent);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/generated-contents/gen_1/knowledge-items/kp_001/learning-state",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ learned: true }),
      }),
    );
  });
});
