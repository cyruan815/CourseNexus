import { afterEach, describe, expect, it, vi } from "vitest";

import { createCourse, deleteCourse, fetchCourse, listCourses, updateCourse } from "../../../src/features/courses/api";

const course = {
  id: "crs_123",
  user_id: "usr_123",
  name: "高等数学",
  description: "期末复习",
  teacher: "王老师",
  term: "2026 Spring",
  status: "active",
  created_at: "2026-07-09T12:00:00+00:00",
  updated_at: "2026-07-09T12:00:00+00:00",
  deleted_at: null,
};

describe("courses api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("lists current user's courses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: [course], meta: { request_id: "req_1" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listCourses()).resolves.toEqual([course]);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses", expect.any(Object));
  });

  it("fetches one course by id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: course, meta: { request_id: "req_1" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchCourse("crs_123")).resolves.toEqual(course);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses/crs_123", expect.any(Object));
  });

  it("creates a course with metadata fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: course, meta: { request_id: "req_1" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createCourse({
        name: "高等数学",
        description: "期末复习",
        teacher: "王老师",
        term: "2026 Spring",
      }),
    ).resolves.toEqual(course);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "高等数学",
          description: "期末复习",
          teacher: "王老师",
          term: "2026 Spring",
        }),
      }),
    );
  });

  it("updates a course by id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: course, meta: { request_id: "req_1" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(updateCourse("crs_123", { name: "高等数学复习", teacher: null })).resolves.toEqual(course);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses/crs_123",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "高等数学复习", teacher: null }),
      }),
    );
  });

  it("deletes a course by id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { ...course, status: "deleted" }, meta: { request_id: "req_1" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(deleteCourse("crs_123")).resolves.toEqual({ ...course, status: "deleted" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses/crs_123",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
