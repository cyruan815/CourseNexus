import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Divider,
  Group,
  Modal,
  PasswordInput,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { ApiError } from "../../api/errors";
import {
  fetchModelRuntimeConfig,
  updateModelRuntimeConfig,
} from "./api";
import type {
  ModelEndpointConfigRead,
  ModelEndpointConfigUpdate,
  ModelRuntimeConfigRead,
} from "./api";

interface ModelConfigModalProps {
  opened: boolean;
  onClose: () => void;
}

interface EndpointDraft {
  model: string;
  baseUrl: string;
  apiKey: string;
}

const emptyDraft: EndpointDraft = { model: "", baseUrl: "", apiKey: "" };

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return fallback;
}

function toDraft(config: ModelEndpointConfigRead): EndpointDraft {
  return {
    model: config.model,
    baseUrl: config.base_url ?? "",
    apiKey: "",
  };
}

function buildUpdate(draft: EndpointDraft): ModelEndpointConfigUpdate {
  const apiKey = draft.apiKey.trim();
  return {
    model: draft.model.trim(),
    base_url: draft.baseUrl.trim(),
    ...(apiKey ? { api_key: apiKey } : {}),
  };
}

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function keyDescription(config: ModelEndpointConfigRead | null): string {
  if (!config?.api_key_configured) {
    return "尚未配置，首次保存时必须填写";
  }
  return `当前 Key：${config.api_key_hint ?? "已配置"}；留空则保留`;
}

export function ModelConfigModal({ opened, onClose }: ModelConfigModalProps) {
  const [config, setConfig] = useState<ModelRuntimeConfigRead | null>(null);
  const [embedding, setEmbedding] = useState<EndpointDraft>(emptyDraft);
  const [general, setGeneral] = useState<EndpointDraft>(emptyDraft);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!opened) {
      return;
    }
    let ignore = false;
    setIsLoading(true);
    setLoadError(null);
    setSaveError(null);
    setSaved(false);

    fetchModelRuntimeConfig()
      .then((nextConfig) => {
        if (ignore) return;
        setConfig(nextConfig);
        setEmbedding(toDraft(nextConfig.embedding));
        setGeneral(toDraft(nextConfig.general));
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setLoadError(errorMessage(error, "模型配置加载失败"));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [opened, reloadKey]);

  function closeModal() {
    if (!isSaving) {
      onClose();
    }
  }

  function updateEmbedding(patch: Partial<EndpointDraft>) {
    setEmbedding((current) => ({ ...current, ...patch }));
    setSaved(false);
    setSaveError(null);
  }

  function updateGeneral(patch: Partial<EndpointDraft>) {
    setGeneral((current) => ({ ...current, ...patch }));
    setSaved(false);
    setSaveError(null);
  }

  function validate(): string | null {
    if (!embedding.model.trim() || !embedding.baseUrl.trim()) {
      return "请完整填写 Embedding 模型和 Base URL";
    }
    if (!general.model.trim() || !general.baseUrl.trim()) {
      return "请完整填写其他模型和 Base URL";
    }
    if (!isHttpUrl(embedding.baseUrl.trim()) || !isHttpUrl(general.baseUrl.trim())) {
      return "Base URL 必须是有效的 HTTP(S) 地址";
    }
    if (!config?.embedding.api_key_configured && !embedding.apiKey.trim()) {
      return "首次配置时必须填写 Embedding API Key";
    }
    if (!config?.general.api_key_configured && !general.apiKey.trim()) {
      return "首次配置时必须填写其他模型 API Key";
    }
    return null;
  }

  async function saveConfig() {
    const validationError = validate();
    if (validationError) {
      setSaveError(validationError);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const nextConfig = await updateModelRuntimeConfig({
        embedding: buildUpdate(embedding),
        general: buildUpdate(general),
      });
      setConfig(nextConfig);
      setEmbedding(toDraft(nextConfig.embedding));
      setGeneral(toDraft(nextConfig.general));
      setSaved(true);
    } catch (error: unknown) {
      setSaveError(errorMessage(error, "模型配置保存失败"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal
      centered
      closeButtonProps={{ "aria-label": "关闭模型配置弹窗" }}
      closeOnClickOutside={!isSaving}
      closeOnEscape={!isSaving}
      onClose={closeModal}
      opened={opened}
      size="lg"
      title="模型配置"
      transitionProps={{ duration: 0 }}
    >
      {isLoading ? (
        <Stack aria-label="正在加载模型配置" gap="md">
          <Skeleton height={110} radius="md" />
          <Skeleton height={110} radius="md" />
        </Stack>
      ) : loadError ? (
        <Stack gap="md">
          <Alert color="red" role="alert" title="加载失败" variant="light">
            {loadError}
          </Alert>
          <Group justify="flex-end">
            <Button onClick={() => setReloadKey((value) => value + 1)} variant="light">
              重试
            </Button>
          </Group>
        </Stack>
      ) : config ? (
        <Stack gap="lg">
          <Text c="dimmed" size="sm">
            配置会同步到服务端 .env。API Key 保存后仅显示前几位，留空不会覆盖已有 Key。
          </Text>

          {saved ? (
            <Alert color="green" title="配置已保存" variant="light">
              新配置已写入并用于后续模型请求。
            </Alert>
          ) : null}
          {saveError ? (
            <Alert color="red" role="alert" title="保存失败" variant="light">
              {saveError}
            </Alert>
          ) : null}
          {!config.general_config_consistent ? (
            <Alert color="yellow" title="检测到历史配置不一致" variant="light">
              当前各通用模型用途使用了不同配置；本页以课程问答配置回填，保存后会统一覆盖所有非 Embedding 用途。
            </Alert>
          ) : null}

          <Stack className="profile-model-config-section" gap="sm">
            <Title order={3}>Embedding 模型</Title>
            <TextInput
              disabled={isSaving}
              label="Embedding 模型名称"
              onChange={(event) => updateEmbedding({ model: event.currentTarget.value })}
              required
              value={embedding.model}
            />
            <TextInput
              disabled={isSaving}
              label="Embedding Base URL"
              onChange={(event) => updateEmbedding({ baseUrl: event.currentTarget.value })}
              placeholder="https://example.com/v1"
              required
              value={embedding.baseUrl}
            />
            <PasswordInput
              autoComplete="off"
              description={keyDescription(config.embedding)}
              disabled={isSaving}
              label="Embedding API Key"
              onChange={(event) => updateEmbedding({ apiKey: event.currentTarget.value })}
              placeholder={config.embedding.api_key_configured ? "留空以保留当前 Key" : "请输入 API Key"}
              value={embedding.apiKey}
            />
          </Stack>

          <Divider />

          <Stack className="profile-model-config-section" gap="sm">
            <Title order={3}>其他模型</Title>
            <Text c="dimmed" size="sm">
              此配置统一用于课程问答、内容生成、学习计划、讲义和任务测试等非 Embedding 能力。
            </Text>
            <TextInput
              disabled={isSaving}
              label="其他模型名称"
              onChange={(event) => updateGeneral({ model: event.currentTarget.value })}
              required
              value={general.model}
            />
            <TextInput
              disabled={isSaving}
              label="其他模型 Base URL"
              onChange={(event) => updateGeneral({ baseUrl: event.currentTarget.value })}
              placeholder="https://example.com/v1"
              required
              value={general.baseUrl}
            />
            <PasswordInput
              autoComplete="off"
              description={keyDescription(config.general)}
              disabled={isSaving}
              label="其他模型 API Key"
              onChange={(event) => updateGeneral({ apiKey: event.currentTarget.value })}
              placeholder={config.general.api_key_configured ? "留空以保留当前 Key" : "请输入 API Key"}
              value={general.apiKey}
            />
          </Stack>

          <Group justify="flex-end">
            <Button disabled={isSaving} onClick={closeModal} variant="default">
              取消
            </Button>
            <Button loading={isSaving} onClick={() => void saveConfig()}>
              保存配置
            </Button>
          </Group>
        </Stack>
      ) : null}
    </Modal>
  );
}
