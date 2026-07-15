import { useEffect, useId, useState } from "react";

type MermaidRenderState =
  | { status: "loading" }
  | { status: "ready"; svg: string }
  | { status: "error" };

let mermaidRenderSequence = 0;

const allowedSvgTags = new Set([
  "a",
  "circle",
  "defs",
  "desc",
  "ellipse",
  "g",
  "line",
  "lineargradient",
  "marker",
  "path",
  "polygon",
  "polyline",
  "radialgradient",
  "rect",
  "stop",
  "svg",
  "text",
  "title",
  "tspan",
]);

const allowedSvgAttributes = new Set([
  "aria-hidden",
  "class",
  "cx",
  "cy",
  "d",
  "data-testid",
  "dominant-baseline",
  "dx",
  "dy",
  "fill",
  "fill-opacity",
  "font-family",
  "font-size",
  "height",
  "href",
  "id",
  "marker-end",
  "marker-height",
  "marker-mid",
  "marker-start",
  "marker-width",
  "offset",
  "opacity",
  "orient",
  "points",
  "r",
  "refx",
  "refy",
  "role",
  "rx",
  "ry",
  "stroke",
  "stroke-dasharray",
  "stroke-linecap",
  "stroke-linejoin",
  "stroke-opacity",
  "stroke-width",
  "text-anchor",
  "transform",
  "viewbox",
  "width",
  "x",
  "x1",
  "x2",
  "xlink:href",
  "xmlns",
  "y",
  "y1",
  "y2",
]);

const urlAttributes = new Set(["href", "xlink:href", "marker-end", "marker-mid", "marker-start"]);

function sanitizeMermaidSvg(svg: string): string {
  if (typeof DOMParser === "undefined" || typeof XMLSerializer === "undefined") return "";

  const document = new DOMParser().parseFromString(svg, "image/svg+xml");
  if (document.querySelector("parsererror") || document.documentElement.tagName.toLowerCase() !== "svg") {
    return "";
  }

  sanitizeSvgElement(document.documentElement);
  return new XMLSerializer().serializeToString(document.documentElement);
}

function sanitizeSvgElement(element: Element) {
  for (const child of Array.from(element.children)) {
    const tagName = child.tagName.toLowerCase();
    if (!allowedSvgTags.has(tagName)) {
      child.remove();
      continue;
    }

    sanitizeSvgElement(child);
  }

  for (const attribute of Array.from(element.attributes)) {
    const attributeName = attribute.name.toLowerCase();
    if (!allowedSvgAttributes.has(attributeName) || attributeName.startsWith("on") || attributeName === "style") {
      element.removeAttribute(attribute.name);
      continue;
    }

    if (urlAttributes.has(attributeName) && !isSafeSvgUrl(attribute.value)) {
      element.removeAttribute(attribute.name);
    }
  }
}

function isSafeSvgUrl(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue.startsWith("#") || /^(https?:|mailto:)/i.test(trimmedValue);
}
export function MermaidDiagram({ chart }: { chart: string }) {
  const reactId = useId();
  const renderId = `handout-mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const [state, setState] = useState<MermaidRenderState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });

    void (async () => {
      try {
        const { default: mermaid } = await import("mermaid");
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
        const requestId = `${renderId}-${++mermaidRenderSequence}`;
        const { svg } = await mermaid.render(requestId, chart);
        if (active) setState({ status: "ready", svg: sanitizeMermaidSvg(svg) });
      } catch {
        if (active) setState({ status: "error" });
      }
    })();

    return () => {
      active = false;
    };
  }, [chart, renderId]);

  if (state.status === "loading") {
    return (
      <div className="handout-mermaid handout-mermaid-loading" aria-live="polite">
        {"Mermaid \u56fe\u8868\u6e32\u67d3\u4e2d..."}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="handout-mermaid handout-mermaid-error" role="alert">
        <strong>{"Mermaid \u56fe\u8868\u6e32\u67d3\u5931\u8d25"}</strong>
        <pre>
          <code>{chart}</code>
        </pre>
      </div>
    );
  }

  return (
    <div
      className="handout-mermaid handout-mermaid-diagram"
      dangerouslySetInnerHTML={{ __html: state.svg }}
    />
  );
}
