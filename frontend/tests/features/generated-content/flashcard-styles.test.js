import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const css = fs.readFileSync(
  path.resolve(process.cwd(), "src/features/generated-content/generated-content.css"),
  "utf8",
);

describe("flashcard face colors", () => {
  it("uses the requested solid colors for question and answer faces", () => {
    expect(css).toMatch(/\.gc-flashcard-question\s*\{[^}]*background:\s*#E5EDF5/i);
    expect(css).toMatch(/\.gc-flashcard-answer\s*\{[^}]*background:\s*#EFF2F5/i);
  });
});
