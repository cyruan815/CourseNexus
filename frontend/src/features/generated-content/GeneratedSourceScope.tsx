import { Badge, Box, Group, Paper, Stack, Text } from "@mantine/core";
import { IconBooks, IconFileDescription } from "@tabler/icons-react";

interface SourceMaterialSnapshot {
  material_id: string;
  material_name: string;
}

function sourceMaterials(value: unknown): SourceMaterialSnapshot[] {
  if (typeof value !== "object" || value === null || !("source_materials" in value)) {
    return [];
  }
  const rawSources = (value as { source_materials?: unknown }).source_materials;
  if (!Array.isArray(rawSources)) {
    return [];
  }
  return rawSources.filter((source): source is SourceMaterialSnapshot => (
    typeof source === "object"
    && source !== null
    && typeof (source as SourceMaterialSnapshot).material_id === "string"
    && typeof (source as SourceMaterialSnapshot).material_name === "string"
    && (source as SourceMaterialSnapshot).material_name.trim().length > 0
  ));
}

export function GeneratedSourceScope({ materialScope }: { materialScope: unknown }) {
  const sources = sourceMaterials(materialScope);
  if (sources.length === 0) {
    return null;
  }

  return (
    <Paper aria-label="生成使用的资料" className="generated-source-scope" radius="md" withBorder>
      <Stack gap="sm">
        <Group justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Box aria-hidden="true" className="generated-source-scope__icon">
              <IconBooks size={20} stroke={1.8} />
            </Box>
            <Box>
              <Text className="generated-source-scope__title">生成使用的资料</Text>
              <Text className="generated-source-scope__caption">本内容综合以下课程资料生成</Text>
            </Box>
          </Group>
          <Badge className="generated-source-scope__count" color="gray" size="sm" variant="light">
            {sources.length} 份
          </Badge>
        </Group>
        <Group className="generated-source-scope__list" gap="xs">
          {sources.map((source) => (
            <Badge
              className="generated-source-scope__item"
              color="blue"
              key={source.material_id}
              leftSection={<IconFileDescription size={13} stroke={2} />}
              variant="light"
            >
              {source.material_name}
            </Badge>
          ))}
        </Group>
      </Stack>
    </Paper>
  );
}
