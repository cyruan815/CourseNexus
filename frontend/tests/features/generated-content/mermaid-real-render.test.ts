import mermaid from "mermaid";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MERMAID_CONFIG } from "../../../src/features/generated-content/renderers/handout/MermaidDiagram";

describe("Mermaid real SVG rendering", () => {
  const originalGetBBox = SVGElement.prototype.getBBox;
  const originalGetComputedTextLength = SVGElement.prototype.getComputedTextLength;

  beforeEach(() => {
    SVGElement.prototype.getBBox = () => ({
      bottom: 20,
      height: 20,
      left: 0,
      right: 100,
      toJSON: () => ({}),
      top: 0,
      width: 100,
      x: 0,
      y: 0,
    });
    SVGElement.prototype.getComputedTextLength = () => 80;
  });

  afterEach(() => {
    SVGElement.prototype.getBBox = originalGetBBox;
    SVGElement.prototype.getComputedTextLength = originalGetComputedTextLength;
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  it("emits flowchart labels as safe SVG text instead of foreignObject HTML", async () => {
    mermaid.initialize(MERMAID_CONFIG);

    const { svg } = await mermaid.render(
      "handout-mermaid-real-render",
      "flowchart LR\n  A[Input] --> B[Output]",
    );
    const parsed = new DOMParser().parseFromString(svg, "image/svg+xml");

    expect(parsed.querySelector("foreignObject")).toBeNull();
    expect(Array.from(parsed.querySelectorAll("text"), (node) => node.textContent)).toEqual(
      expect.arrayContaining(["Input", "Output"]),
    );
  });
});
