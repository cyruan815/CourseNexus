import { Alert, Badge, Box, Checkbox, Group, SegmentedControl, Stack, Text } from "@mantine/core";

import type { Material, MaterialScope } from "../../materials/types";

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
  const parsedMaterials = materials.filter((material) => material.parse_status === "parsed");
  const parsedIds = parsedMaterials.map((material) => material.id);
  const selectedIds = materialScope.include_all_parsed_materials
    ? parsedIds
    : materialScope.material_ids.filter((id) => parsedIds.includes(id));
  const mode = materialScope.include_all_parsed_materials ? "all" : "specific";

  function changeMode(nextMode: string) {
    if (nextMode === "all") {
      onMaterialScopeChange({ include_all_parsed_materials: true, material_ids: [] });
      return;
    }

    onMaterialScopeChange({
      include_all_parsed_materials: false,
      material_ids: [],
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
          {materialScope.include_all_parsed_materials ? "全部已解析" : `已选 ${selectedIds.length}`}
        </Badge>
      </Group>

      <SegmentedControl
        data={[
          { label: <span data-testid="scope-mode-all">全部已解析资料</span>, value: "all" },
          {
            disabled: parsedIds.length === 0,
            label: <span data-testid="scope-mode-specific">指定资料</span>,
            value: "specific",
          },
        ]}
        onChange={changeMode}
        value={mode}
      />

      {error ? (
        <Alert color="red" role="alert" variant="light">
          {error}
        </Alert>
      ) : null}

      {!isLoading && mode === "specific" && selectedIds.length === 0 ? (
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
            const isParsed = material.parse_status === "parsed";
            const isChecked = materialScope.include_all_parsed_materials
              ? isParsed
              : selectedIds.includes(material.id);

            return (
              <Group className="study-plan-scope-row" key={material.id} justify="space-between" wrap="nowrap">
                <Checkbox
                  checked={isChecked}
                  disabled={!isParsed || materialScope.include_all_parsed_materials}
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
          还没有可用于 Agent 的已解析资料，后续 preview 可能会由后端返回无可用资料提示。
        </Alert>
      ) : null}
    </Box>
  );
}
