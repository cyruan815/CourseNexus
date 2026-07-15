import { Children, isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";
import "./handout-markdown.css";
import { MermaidDiagram } from "./MermaidDiagram";
import { remarkHandoutCallouts } from "./remarkHandoutCallouts";

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
      rehypePlugins={[rehypeRaw, rehypeKatex]}
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
