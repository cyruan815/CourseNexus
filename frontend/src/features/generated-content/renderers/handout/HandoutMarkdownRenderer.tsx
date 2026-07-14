import { isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";
import "./handout-markdown.css";

type CalloutType = "note" | "example" | "summary" | "warning" | "tip";

const calloutDefaults: Record<CalloutType, string> = {
  note: "注意",
  example: "例题",
  summary: "核心结论",
  warning: "易错点",
  tip: "解题提示",
};

const calloutTypes: Record<string, CalloutType> = {
  EXAMPLE: "example",
  NOTE: "note",
  SUMMARY: "summary",
  TIP: "tip",
  WARNING: "warning",
};

const calloutPattern = /^\[!(NOTE|EXAMPLE|SUMMARY|WARNING|TIP)\]\s*([^\n]*)\n?/;

export function HandoutMarkdownRenderer({ markdown }: { markdown: string }) {
  return (
    <article className="handout-markdown">
      <ReactMarkdown
        components={{
          blockquote: HandoutBlockquote,
          h3: HandoutH3,
          table: HandoutTable,
        }}
        rehypePlugins={[rehypeKatex]}
        remarkPlugins={[remarkGfm, remarkMath]}
      >
        {markdown}
      </ReactMarkdown>
    </article>
  );
}

function HandoutBlockquote({ children }: { children?: ReactNode }) {
  const text = textContent(children).trimStart();
  const match = calloutPattern.exec(text);
  if (!match) return <blockquote className="handout-blockquote">{children}</blockquote>;

  const calloutType = calloutTypes[match[1]];
  const title = match[2].trim() || calloutDefaults[calloutType];
  const bodyMarkdown = text.replace(calloutPattern, "").trim();

  return (
    <section className={`handout-callout handout-callout-${calloutType}`} data-testid={`handout-callout-${calloutType}`}>
      <strong>{title}</strong>
      <div className="handout-callout-body">
        <ReactMarkdown rehypePlugins={[rehypeKatex]} remarkPlugins={[remarkGfm, remarkMath]}>
          {bodyMarkdown}
        </ReactMarkdown>
      </div>
    </section>
  );
}

function HandoutH3({ children }: { children?: ReactNode }) {
  const text = textContent(children).trim();
  const match = /^(\d+(?:\.\d+)*)\s+(.+)$/.exec(text);
  if (!match) return <h3>{children}</h3>;
  return (
    <h3>
      <span>{match[1]}</span>
      {match[2]}
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

function textContent(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textContent).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return textContent(node.props.children);
  return "";
}
