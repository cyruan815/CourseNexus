import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createMaterialFolder,
  listMaterialFolders,
  moveMaterialToFolder,
  uploadMaterial,
} from "../../../src/features/materials/api";

describe("materials api", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() =>
        Promise.resolve(
          new Response(JSON.stringify({ data: [], meta: { request_id: "req_1" } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        ),
      ),
    );
  });

  it("calls folder and material assignment endpoints", async () => {
    await listMaterialFolders("crs_1");
    await createMaterialFolder("crs_1", { name: "第一周" });
    await moveMaterialToFolder("mat_1", "fld_1");

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/courses/crs_1/material-folders",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/courses/crs_1/material-folders",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ name: "第一周" }) }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      3,
      "/api/v1/materials/mat_1/folder",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ folder_id: "fld_1" }) }),
    );
  });

  it("uploads a file with an optional folder id", async () => {
    const file = new File(["notes"], "notes.md", { type: "text/markdown" });

    await uploadMaterial("crs_1", file, "fld_1");

    const request = vi.mocked(fetch).mock.calls[0];
    expect(request[0]).toBe("/api/v1/courses/crs_1/materials");
    expect(request[1]).toEqual(expect.objectContaining({ method: "POST" }));
    const body = request[1]?.body as FormData;
    expect(body.get("file")).toBe(file);
    expect(body.get("folder_id")).toBe("fld_1");
  });
});
