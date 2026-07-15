import { Children, isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema, type Options as RehypeSanitizeOptions } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";
import "./handout-markdown.css";
import { MermaidDiagram } from "./MermaidDiagram";
import { remarkHandoutCallouts } from "./remarkHandoutCallouts";

type HastNode = {
  type?: string;
  tagName?: string;
  children?: HastNode[];
};
const svgTagNames = [
  "svg",
  "g",
  "path",
  "circle",
  "ellipse",
  "line",
  "rect",
  "polygon",
  "polyline",
  "text",
  "tspan",
  "defs",
  "marker",
  "linearGradient",
  "radialGradient",
  "stop",
  "title",
  "desc",
];

const svgAttributes = [
  "aria-hidden",
  "className",
  "cx",
  "cy",
  "d",
  "data-testid",
  "dominantBaseline",
  "dx",
  "dy",
  "fill",
  "fillOpacity",
  "fontFamily",
  "fontSize",
  "height",
  "id",
  "markerEnd",
  "markerHeight",
  "markerMid",
  "markerStart",
  "markerWidth",
  "offset",
  "opacity",
  "orient",
  "points",
  "r",
  "refX",
  "refY",
  "role",
  "rx",
  "ry",
  "stroke",
  "strokeDasharray",
  "strokeLinecap",
  "strokeLinejoin",
  "strokeOpacity",
  "strokeWidth",
  "textAnchor",
  "transform",
  "viewBox",
  "width",
  "x",
  "x1",
  "x2",
  "xlinkHref",
  "xmlns",
  "y",
  "y1",
  "y2",
];

const svgTagNamesLowercase = new Set(svgTagNames.map((tagName) => tagName.toLowerCase()));

function rehypeStripUnsafeSvgChildren() {
  return (tree: HastNode) => stripUnsafeSvgChildren(tree, false);
}

function stripUnsafeSvgChildren(node: HastNode, insideSvg: boolean) {
  if (!node.children) return;

  const nextInsideSvg = insideSvg || node.tagName === "svg";
  node.children = node.children.filter((child) => {
    if (child.type !== "element") return true;

    const childTagName = child.tagName?.toLowerCase();
    if (nextInsideSvg && childTagName && !svgTagNamesLowercase.has(childTagName)) {
      return false;
    }

    stripUnsafeSvgChildren(child, nextInsideSvg);
    return true;
  });
}
const handoutSanitizeSchema: RehypeSanitizeOptions = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), ...svgTagNames],
  attributes: {
    ...defaultSchema.attributes,
    "*": [...(defaultSchema.attributes?.["*"] ?? []), "data*", "role", "aria-hidden"],
    a: [...(defaultSchema.attributes?.a ?? []), "href", "title", "target", "rel"],
    section: [["className", "handout-callout", /^handout-callout-/], "data*"],
    strong: [...(defaultSchema.attributes?.strong ?? []), ["className", "handout-callout-title"]],
    div: [...(defaultSchema.attributes?.div ?? []), ["className", "handout-callout-body"]],
    svg: svgAttributes,
    g: svgAttributes,
    path: svgAttributes,
    circle: svgAttributes,
    ellipse: svgAttributes,
    line: svgAttributes,
    rect: svgAttributes,
    polygon: svgAttributes,
    polyline: svgAttributes,
    text: svgAttributes,
    tspan: svgAttributes,
    defs: svgAttributes,
    marker: svgAttributes,
    linearGradient: svgAttributes,
    radialGradient: svgAttributes,
    stop: svgAttributes,
    title: ["id", "className"],
    desc: ["id", "className"],
  },
  strip: [...(defaultSchema.strip ?? []), "script", "iframe", "object", "embed", "foreignObject", "foreignobject", "style"],
  protocols: {
    ...defaultSchema.protocols,
    href: ["http", "https", "mailto"],
    xlinkHref: ["http", "https", "mailto"],
  },
};
export function HandoutMarkdownRenderer({ markdown }: { markdown: string }) {
  return (
    <article className="handout-markdown">
      <MarkdownContent>{markdown}</MarkdownContent>
    </article>
  );
}

function MarkdownContent({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        blockquote: HandoutBlockquote,
        h3: HandoutH3,
        pre: HandoutPre,
        table: HandoutTable,
      }}
      rehypePlugins={[rehypeRaw, [rehypeSanitize, handoutSanitizeSchema], rehypeStripUnsafeSvgChildren, rehypeKatex]}
      remarkPlugins={[remarkGfm, remarkMath, remarkHandoutCallouts]}
    >
      {children}
    </ReactMarkdown>
  );
}

function HandoutPre({ children }: { children?: ReactNode }) {
  const nodes = Children.toArray(children);
  const child = nodes[0];

  if (nodes.length === 1 && isValidElement(child)) {
    const props = child.props as { className?: string; children?: ReactNode };
    const languages = props.className?.split(/\s+/) ?? [];
    if (languages.includes("language-mermaid")) {
      const chart = String(props.children ?? "").replace(/\n$/, "");
      return <MermaidDiagram chart={chart} />;
    }
  }

  return <pre>{children}</pre>;
}

function HandoutBlockquote({ children }: { children?: ReactNode }) {
  return <blockquote className="handout-blockquote">{children}</blockquote>;
}

function HandoutH3({ children }: { children?: ReactNode }) {
  const nodes = Children.toArray(children);
  const firstNode = nodes[0];
  if (typeof firstNode !== "string") return <h3>{children}</h3>;

  const match = /^(\d+(?:\.\d+)*)\s+/.exec(firstNode);
  if (!match) return <h3>{children}</h3>;

  return (
    <h3>
      <span className="handout-heading-number">{match[1]}</span>
      {firstNode.slice(match[0].length)}
      {nodes.slice(1)}
    </h3>
  );
}

function HandoutTable({ children }: { children?: ReactNode }) {
  return (
    <div className="handout-table-wrap">
      <table className="handout-table">{children}</table>
    </div>
  );
}
