import { Stack, Text } from "@mantine/core";

interface DescriptionPart {
  label: string;
  content: string;
}

const sectionPattern = /(含义|条件|步骤|练习检查)：/g;

function splitTaskDescription(description: string): DescriptionPart[] {
  const matches = [...description.matchAll(sectionPattern)];
  if (matches.length === 0) {
    return [];
  }

  const firstMarkerIndex = matches[0]?.index ?? -1;
  if (firstMarkerIndex < 0 || firstMarkerIndex > 8) {
    return [];
  }

  return matches
    .map((match, index) => {
      const label = match[1] ?? "";
      const contentStart = (match.index ?? 0) + match[0].length;
      const nextMatch = matches[index + 1];
      const contentEnd = nextMatch?.index ?? description.length;

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
