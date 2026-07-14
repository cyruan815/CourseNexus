import "./handout-markdown.css";

type CalloutType = "note" | "example" | "summary" | "warning" | "tip";

type Block =
  | { type: "blockquote"; lines: string[] }
  | { type: "callout"; calloutType: CalloutType; title: string; lines: string[] }
  | { type: "formula"; text: string }
  | { type: "heading"; level: 1 | 2 | 3 | 4; text: string }
  | { type: "hr" }
  | { type: "list"; items: string[] }
  | { type: "orderedList"; items: string[] }
  | { type: "paragraph"; text: string }
  | { type: "table"; headers: string[]; rows: string[][] };

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

export function HandoutMarkdownRenderer({ markdown }: { markdown: string }) {
  const blocks = parseHandoutMarkdown(markdown);

  return (
    <article className="handout-markdown">
      {blocks.map((block, index) => (
        <HandoutBlock block={block} key={`${block.type}-${index}`} />
      ))}
    </article>
  );
}

function HandoutBlock({ block }: { block: Block }) {
  if (block.type === "heading") {
    const Tag = `h${block.level}` as "h1" | "h2" | "h3" | "h4";
    return <Tag>{formatHeadingText(block.text, block.level)}</Tag>;
  }
  if (block.type === "hr") return <hr />;
  if (block.type === "paragraph") return <p>{renderInline(block.text)}</p>;
  if (block.type === "list") {
    return (
      <ul>
        {block.items.map((item, index) => (
          <li key={`${item}-${index}`}>{renderInline(item)}</li>
        ))}
      </ul>
    );
  }
  if (block.type === "orderedList") {
    return (
      <ol>
        {block.items.map((item, index) => (
          <li key={`${item}-${index}`}>{renderInline(item)}</li>
        ))}
      </ol>
    );
  }
  if (block.type === "formula") {
    return (
      <div className="handout-formula" role="math">
        <span className="handout-formula-text">{block.text}</span>
      </div>
    );
  }
  if (block.type === "table") {
    return (
      <div className="handout-table-wrap">
        <table className="handout-table">
          <thead>
            <tr>
              {block.headers.map((header) => (
                <th key={header}>{renderInline(header)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`}>{renderInline(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (block.type === "blockquote") {
    return (
      <blockquote className="handout-blockquote">
        {block.lines.map((line, index) => (
          <p key={`${line}-${index}`}>{renderInline(line)}</p>
        ))}
      </blockquote>
    );
  }
  return (
    <section className={`handout-callout handout-callout-${block.calloutType}`} data-testid={`handout-callout-${block.calloutType}`}>
      <strong>{block.title}</strong>
      {block.lines.map((line, index) => (
        <p key={`${line}-${index}`}>{renderInline(line)}</p>
      ))}
    </section>
  );
}

export function parseHandoutMarkdown(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const singleLineFormula = /^\$\$\s*(.+?)\s*\$\$$/.exec(line.trim());
    if (singleLineFormula) {
      blocks.push({ type: "formula", text: singleLineFormula[1].trim() });
      index += 1;
      continue;
    }

    if (line.trim() === "$$") {
      const formulaLines: string[] = [];
      index += 1;
      while (index < lines.length && lines[index]?.trim() !== "$$") {
        formulaLines.push(lines[index] ?? "");
        index += 1;
      }
      blocks.push({ type: "formula", text: formulaLines.join("\n").trim() });
      index += lines[index]?.trim() === "$$" ? 1 : 0;
      continue;
    }

    if (line.startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index]?.startsWith(">")) {
        quoteLines.push((lines[index] ?? "").replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(parseQuoteBlock(quoteLines));
      continue;
    }

    if (isTableStart(lines, index)) {
      const tableLines: string[] = [];
      while (index < lines.length && isTableRow(lines[index] ?? "")) {
        tableLines.push(lines[index] ?? "");
        index += 1;
      }
      blocks.push(parseTable(tableLines));
      continue;
    }

    const heading = parseHeading(line);
    if (heading) {
      blocks.push(heading);
      index += 1;
      continue;
    }

    if (/^\s*-{3,}\s*$/.test(line)) {
      blocks.push({ type: "hr" });
      index += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index] ?? "")) {
        items.push((lines[index] ?? "").replace(/^\s*[-*]\s+/, "").trim());
        index += 1;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index] ?? "")) {
        items.push((lines[index] ?? "").replace(/^\s*\d+\.\s+/, "").trim());
        index += 1;
      }
      blocks.push({ type: "orderedList", items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      index < lines.length &&
      lines[index]?.trim() &&
      !lines[index]?.startsWith(">") &&
      lines[index]?.trim() !== "$$" &&
      !/^\$\$\s*(.+?)\s*\$\$$/.test(lines[index]?.trim() ?? "") &&
      !parseHeading(lines[index] ?? "") &&
      !isTableStart(lines, index) &&
      !/^\s*[-*]\s+/.test(lines[index] ?? "") &&
      !/^\s*\d+\.\s+/.test(lines[index] ?? "") &&
      !/^\s*-{3,}\s*$/.test(lines[index] ?? "")
    ) {
      paragraphLines.push((lines[index] ?? "").trim());
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
  }

  return blocks;
}

function parseHeading(line: string): Block | null {
  const match = /^(#{1,4})\s+(.+)$/.exec(line);
  if (!match) return null;
  return { type: "heading", level: match[1].length as 1 | 2 | 3 | 4, text: match[2].trim() };
}

function parseQuoteBlock(lines: string[]): Block {
  const firstLine = lines[0] ?? "";
  const match = /^\[!(?<type>[A-Z]+)\]\s*(?<title>.*)$/.exec(firstLine.trim());
  if (!match?.groups) return { type: "blockquote", lines: lines.filter(Boolean) };

  const calloutType = calloutTypes[match.groups.type];
  if (!calloutType) return { type: "blockquote", lines: lines.filter(Boolean) };

  const title = match.groups.title.trim() || calloutDefaults[calloutType];
  return { type: "callout", calloutType, title, lines: lines.slice(1).filter(Boolean) };
}

function isTableStart(lines: string[], index: number): boolean {
  return isTableRow(lines[index] ?? "") && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1] ?? "");
}

function isTableRow(line: string): boolean {
  return line.trim().includes("|");
}

function parseTable(lines: string[]): Block {
  const headers = splitTableRow(lines[0] ?? "");
  const rows = lines.slice(2).map(splitTableRow).filter((row) => row.length > 0);
  return { type: "table", headers, rows };
}

function splitTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function formatHeadingText(text: string, level: 1 | 2 | 3 | 4) {
  if (level !== 3) return text;
  const match = /^(\d+(?:\.\d+)*)\s+(.+)$/.exec(text);
  if (!match) return text;
  return (
    <>
      <span>{match[1]}</span>
      {match[2]}
    </>
  );
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    const bold = /^\*\*([^*]+)\*\*$/.exec(part);
    if (bold) return <strong key={`${part}-${index}`}>{bold[1]}</strong>;
    return part;
  });
}
