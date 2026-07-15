import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const styles = readFileSync(resolve(process.cwd(), "src/pages/course-detail.css"), "utf8");

describe("course detail generated-content layout", () => {
  it("keeps every generated-content row at its full height inside the scroll list", () => {
    const itemRule = styles.match(/\.course-detail-generated-item\s*\{([^}]+)\}/)?.[1] ?? "";

    expect(itemRule).toContain("flex: 0 0 auto");
    expect(itemRule).toContain("min-height: 64px");
  });
});
