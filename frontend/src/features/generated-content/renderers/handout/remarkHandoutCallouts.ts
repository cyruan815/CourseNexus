type CalloutType = "note" | "example" | "summary" | "warning" | "tip";

type MarkdownNode = {
  type: string;
  value?: string;
  children?: MarkdownNode[];
  data?: {
    hName?: string;
    hProperties?: Record<string, unknown>;
  };
};

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

const calloutMarkerPattern = /^\[!(NOTE|EXAMPLE|SUMMARY|WARNING|TIP)\][ \t]*([^\r\n]*)(?:\r?\n|$)/;

export function remarkHandoutCallouts() {
  return (tree: MarkdownNode) => transformCallouts(tree);
}

function transformCallouts(node: MarkdownNode) {
  if (!node.children) return;

  for (const child of node.children) {
    if (child.type === "blockquote") transformBlockquote(child);
    transformCallouts(child);
  }
}

function transformBlockquote(blockquote: MarkdownNode) {
  const firstBlock = blockquote.children?.[0];
  const firstInline = firstBlock?.type === "paragraph" ? firstBlock.children?.[0] : undefined;
  if (firstInline?.type !== "text" || typeof firstInline.value !== "string") return;

  const match = calloutMarkerPattern.exec(firstInline.value);
  if (!match) return;

  const calloutType = calloutTypes[match[1]];
  const title = match[2].trim() || calloutDefaults[calloutType];
  const remainingText = firstInline.value.slice(match[0].length);
  const remainingInline = [...(firstBlock?.children ?? [])];

  if (remainingText) {
    remainingInline[0] = { ...firstInline, value: remainingText };
  } else {
    remainingInline.shift();
  }

  const bodyBlocks = [...(blockquote.children ?? []).slice(1)];
  if (remainingInline.length > 0 && firstBlock) {
    bodyBlocks.unshift({ ...firstBlock, children: remainingInline });
  }

  blockquote.data = {
    hName: "section",
    hProperties: {
      className: ["handout-callout", `handout-callout-${calloutType}`],
      "data-testid": `handout-callout-${calloutType}`,
    },
  };
  blockquote.children = [
    {
      type: "paragraph",
      data: {
        hName: "strong",
        hProperties: { className: ["handout-callout-title"] },
      },
      children: [{ type: "text", value: title }],
    },
    {
      type: "blockquote",
      data: {
        hName: "div",
        hProperties: { className: ["handout-callout-body"] },
      },
      children: bodyBlocks,
    },
  ];
}
