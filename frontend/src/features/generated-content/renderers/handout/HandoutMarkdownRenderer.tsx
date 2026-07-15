import { isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";
import "./handout-markdown.css";

type CalloutType = "note" | "example" | "summary" | "warning" | "tip";

type MarkdownSegment =
  | { kind: "markdown"; markdown: string }
  | { kind: "callout"; calloutType: CalloutType; title: string; markdown: string };

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

const calloutLinePattern = /^>\s*\[!(NOTE|EXAMPLE|SUMMARY|WARNING|TIP)\]\s*(.*)$/;

export function HandoutMarkdownRenderer({ markdown }: { markdown: string }) {
  const segments = splitHandoutMarkdown(markdown);

  return (
    <article className="handout-markdown">
      {segments.map((segment, index) =>
        segment.kind === "callout" ? (
          <HandoutCallout key={index} calloutType={segment.calloutType} title={segment.title} markdown={segment.markdown} />
        ) : (
          <MarkdownContent key={index}>{segment.markdown}</MarkdownContent>
        ),
      )}
    </article>
  );
}

function MarkdownContent({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        blockquote: HandoutBlockquote,
        h3: HandoutH3,
        table: HandoutTable,
      }}
      rehypePlugins={[rehypeKatex]}
      remarkPlugins={[remarkGfm, remarkMath]}
    >
      {children}
    </ReactMarkdown>
  );
}

function HandoutCallout({ calloutType, title, markdown }: { calloutType: CalloutType; title: string; markdown: string }) {
  return (
    <section className={`handout-callout handout-callout-${calloutType}`} data-testid={`handout-callout-${calloutType}`}>
      <strong className="handout-callout-title">{title}</strong>
      <div className="handout-callout-body">
        <MarkdownContent>{markdown}</MarkdownContent>
      </div>
    </section>
  );
}

function HandoutBlockquote({ children }: { children?: ReactNode }) {
  return <blockquote className="handout-blockquote">{children}</blockquote>;
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

function splitHandoutMarkdown(markdown: string): MarkdownSegment[] {
  const lines = markdown.split(/\r?\n/);
  const segments: MarkdownSegment[] = [];
  let markdownBuffer: string[] = [];

  const flushMarkdown = () => {
    const chunk = markdownBuffer.join("\n").trim();
    if (chunk) segments.push({ kind: "markdown", markdown: chunk });
    markdownBuffer = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const match = calloutLinePattern.exec(lines[index]);
    if (!match) {
      markdownBuffer.push(lines[index]);
      continue;
    }

    flushMarkdown();
    const calloutType = calloutTypes[match[1]];
    const title = match[2].trim() || calloutDefaults[calloutType];
    const calloutLines: string[] = [];

    index += 1;
    while (index < lines.length) {
      const line = lines[index];
      if (!line.startsWith(">")) break;
      calloutLines.push(line.replace(/^>\s?/, ""));
      index += 1;
    }
    index -= 1;

    segments.push({ kind: "callout", calloutType, title, markdown: calloutLines.join("\n").trim() });
  }

  flushMarkdown();
  return segments;
}
