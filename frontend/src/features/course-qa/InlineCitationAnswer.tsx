import { Box, Divider, HoverCard, Stack, Text } from "@mantine/core";
import ReactMarkdown from "react-markdown";

import "./inline-citation-answer.css";

export interface InlineAnswerCitation {
  chunk_id: string | null;
  hit_text: string;
  material_id: string | null;
  material_name: string;
  page: string | number | null;
  page_index: number | null;
}

function citationLocation(citation: InlineAnswerCitation): string {
  if (citation.page !== null) {
    return `第 ${citation.page} 页`;
  }
  return citation.page_index !== null ? `第 ${citation.page_index + 1} 页` : "位置待定位";
}

function answerWithCitationLinks(content: string, citations: InlineAnswerCitation[]): string {
  let validMarkerCount = 0;
  const normalized = content.replace(/\[\[cite:(\d+)\]\]/g, (_marker, rawOrdinal: string) => {
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
    <HoverCard closeDelay={100} openDelay={120} position="bottom" shadow="md" width={360} withArrow withinPortal>
      <HoverCard.Target>
        <button
          aria-label={`查看引用 ${ordinal}：${citation.material_name}`}
          className="inline-citation-marker"
          type="button"
        >
          {ordinal}
        </button>
      </HoverCard.Target>
      <HoverCard.Dropdown aria-label={`引用 ${ordinal} 详情`} className="inline-citation-popover" role="tooltip">
        <Stack gap="xs">
          <Box>
            <Text fw={700} lineClamp={2}>{citation.material_name}</Text>
            <Text c="dimmed" size="xs">{citationLocation(citation)}</Text>
          </Box>
          <Divider />
          <Text className="inline-citation-snippet" size="sm">{citation.hit_text}</Text>
        </Stack>
      </HoverCard.Dropdown>
    </HoverCard>
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
