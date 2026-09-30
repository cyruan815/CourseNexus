import { Alert, Badge, Box, Checkbox, Group, Stack, Text } from "@mantine/core";

import { isMaterialLearningReady, type Material, type MaterialScope } from "../../materials/types";

interface StudyPlanMaterialScopeSelectorProps {
  error: string | null;
  isLoading: boolean;
  materialScope: MaterialScope;
  materials: Material[];
  onMaterialScopeChange: (scope: MaterialScope) => void;
}

const statusLabels: Record<string, string> = {
  uploaded: "待解析",
  parsing: "解析中",
  parsed: "可使用",
  parse_failed: "解析失败",
};

export function StudyPlanMaterialScopeSelector({
  error,
  isLoading,
  materialScope,
  materials,
  onMaterialScopeChange,
}: StudyPlanMaterialScopeSelectorProps) {
  const parsedMaterials = materials.filter(isMaterialLearningReady);
  const parsedIds = parsedMaterials.map((material) => material.id);
  const selectedIds = materialScope.material_ids.filter((id) => parsedIds.includes(id));
  const hasSelectedAll = parsedIds.length > 0 && selectedIds.length === parsedIds.length;

  function toggleAll() {
    onMaterialScopeChange({
      include_all_parsed_materials: false,
      material_ids: hasSelectedAll ? [] : parsedIds,
    });
  }

  function toggleMaterial(materialId: string) {
    const nextSelectedIds = selectedIds.includes(materialId)
      ? selectedIds.filter((id) => id !== materialId)
      : [...selectedIds, materialId];
    onMaterialScopeChange({
      include_all_parsed_materials: false,
      material_ids: nextSelectedIds,
    });
  }

  return (
    <Box className="study-plan-scope" data-testid="study-plan-material-scope">
      <Group justify="space-between" wrap="nowrap">
        <Stack gap={2}>
          <Text fw={750}>资料范围</Text>
          <Text c="dimmed" size="sm">
            选择本次计划生成要使用的已解析资料。
          </Text>
        </Stack>
        <Badge color="teal" variant="light">
          已选 {selectedIds.length} / {parsedIds.length}
        </Badge>
      </Group>

      <Checkbox
        checked={hasSelectedAll}
        disabled={parsedIds.length === 0}
        indeterminate={selectedIds.length > 0 && !hasSelectedAll}
        label="全选当前可用资料"
        onChange={toggleAll}
      />

      {error ? (
        <Alert color="red" role="alert" variant="light">
          {error}
        </Alert>
      ) : null}

      {!isLoading && selectedIds.length === 0 ? (
        <Alert color="yellow" role="status" variant="light">
          请选择至少一份已解析资料。
        </Alert>
      ) : null}

      {isLoading ? (
        <Text c="dimmed" size="sm">正在加载课程资料...</Text>
      ) : null}

      {!isLoading && materials.length === 0 ? (
        <Text c="dimmed" size="sm">当前课程还没有资料。</Text>
      ) : null}

      {!isLoading && materials.length > 0 ? (
        <Stack className="study-plan-scope-list" gap={8}>
          {materials.map((material) => {
            const isParsed = isMaterialLearningReady(material);
            const isChecked = isParsed && selectedIds.includes(material.id);

            return (
              <Group className="study-plan-scope-row" key={material.id} justify="space-between" wrap="nowrap">
                <Checkbox
                  checked={isChecked}
                  disabled={!isParsed}
                  label={material.name}
                  onChange={() => toggleMaterial(material.id)}
                />
                <Badge color={isParsed ? "teal" : "gray"} variant="light">
                  {statusLabels[material.parse_status] ?? material.parse_status}
                </Badge>
              </Group>
            );
          })}
        </Stack>
      ) : null}

      {!isLoading && parsedIds.length === 0 ? (
        <Alert color="yellow" variant="light">
          还没有可用于 Agent 的已解析资料，请先完成资料解析。
        </Alert>
      ) : null}
    </Box>
  );
}
