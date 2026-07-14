import { Stack, Text } from "@mantine/core";

interface DescriptionPart {
  label: string;
  content: string;
}

const sectionPattern = /(^|[\n。；;]\s*)([\p{Script=Han}A-Za-z0-9]{2,8})[：:]/gu;

function markerStart(match: RegExpMatchArray): number {
  return (match.index ?? 0) + (match[1]?.length ?? 0);
}

function splitTaskDescription(description: string): DescriptionPart[] {
  const matches = [...description.matchAll(sectionPattern)];
  if (matches.length === 0) {
    return [];
  }

  const firstMarkerIndex = markerStart(matches[0] as RegExpMatchArray);
  if (firstMarkerIndex < 0 || firstMarkerIndex > 8) {
    return [];
  }

  return matches
    .map((match, index) => {
      const label = match[2] ?? "";
      const contentStart = markerStart(match) + label.length + 1;
      const nextMatch = matches[index + 1];
      const contentEnd = nextMatch ? markerStart(nextMatch) : description.length;

      return {
        label,
        content: description.slice(contentStart, contentEnd).trim(),
      };
    })
    .filter((part) => part.label && part.content);
}

export function StudyPlanTaskDescription({ description }: { description: string | null | undefined }) {
  if (!description) {
    return null;
  }

  const parts = splitTaskDescription(description);
  if (parts.length === 0) {
    return (
      <Text c="dimmed" className="study-plan-task-description" size="sm">
        {description}
      </Text>
    );
  }

  return (
    <Stack className="study-plan-description-parts" gap={6}>
      {parts.map((part, index) => (
        <div className="study-plan-description-part" key={`${part.label}-${index}`}>
          <Text className="study-plan-description-label" component="span" fw={700} size="sm">
            {part.label}
          </Text>
          <Text c="dimmed" className="study-plan-description-content" component="span" size="sm">
            {part.content}
          </Text>
        </div>
      ))}
    </Stack>
  );
}
