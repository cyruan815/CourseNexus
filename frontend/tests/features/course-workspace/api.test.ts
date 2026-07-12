import { describe, expect, it, vi } from "vitest";

import {
  askCourseQuestion,
  generateCourseContent,
  listCourseConversations,
  listConversationMessages,
  listGeneratedContents,
  listStudyPlans,
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
      3,
      "/api/v1/courses/crs_1/study-plans",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
