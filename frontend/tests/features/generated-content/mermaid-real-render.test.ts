import mermaid from "mermaid";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MERMAID_CONFIG } from "../../../src/features/generated-content/renderers/handout/MermaidDiagram";

type MeasurableSvgPrototype = SVGElement & {
  getBBox: () => DOMRect;
  getComputedTextLength: () => number;
};

describe("Mermaid real SVG rendering", () => {
  const svgPrototype = SVGElement.prototype as MeasurableSvgPrototype;
  const originalGetBBox = svgPrototype.getBBox;
  const originalGetComputedTextLength = svgPrototype.getComputedTextLength;

  beforeEach(() => {
    svgPrototype.getBBox = () => new DOMRect(0, 0, 100, 20);
    svgPrototype.getComputedTextLength = () => 80;
  });

  afterEach(() => {
    svgPrototype.getBBox = originalGetBBox;
    svgPrototype.getComputedTextLength = originalGetComputedTextLength;
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
