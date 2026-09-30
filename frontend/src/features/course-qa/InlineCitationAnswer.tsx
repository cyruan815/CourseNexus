import { Box } from "@mantine/core";
import ReactMarkdown from "react-markdown";

import { CitationLocator, type CitationLocatorData } from "./CitationLocator";
import "./inline-citation-answer.css";

export type InlineAnswerCitation = CitationLocatorData;

function answerWithCitationLinks(content: string, citations: InlineAnswerCitation[]): string {
  let validMarkerCount = 0;
  const normalized = content.replace(/\[\[cite:(\d+)\]\]|\[cite:(\d+)\]/g, (
    _marker,
    standardOrdinal: string | undefined,
    singleBracketOrdinal: string | undefined,
  ) => {
    const rawOrdinal = standardOrdinal ?? singleBracketOrdinal;
    const ordinal = Number(rawOrdinal);
    if (!Number.isInteger(ordinal) || ordinal < 1 || ordinal > citations.length) {
      return "";
    }
    validMarkerCount += 1;
    return `[${ordinal}](#course-citation-${ordinal})`;
  });

  if (citations.length === 0 || validMarkerCount > 0) {
    return normalized;
  }
  const legacyMarkers = citations.map((_citation, index) => `[${index + 1}](#course-citation-${index + 1})`).join(" ");
  return `${normalized.trimEnd()} ${legacyMarkers}`;
}

function CitationMarker({ citation, ordinal }: { citation: InlineAnswerCitation; ordinal: number }) {
  return (
    <CitationLocator
      ariaLabel={`查看引用 ${ordinal}：${citation.material_name}`}
      citation={citation}
      className="inline-citation-marker"
      detailsAriaLabel={`引用 ${ordinal} 详情`}
      label={ordinal}
    />
  );
}

export function InlineCitationAnswer({
  citations,
  content,
}: {
  citations: InlineAnswerCitation[];
  content: string;
}) {
  return (
    <Box className="inline-citation-answer">
      <ReactMarkdown
        components={{
          a: ({ children, href }) => {
            const match = href?.match(/^#course-citation-(\d+)$/);
            if (match) {
              const ordinal = Number(match[1]);
              const citation = citations[ordinal - 1];
              return citation ? <CitationMarker citation={citation} ordinal={ordinal} /> : <>{children}</>;
            }
            return <a href={href}>{children}</a>;
          },
        }}
      >
        {answerWithCitationLinks(content, citations)}
      </ReactMarkdown>
    </Box>
  );
}
