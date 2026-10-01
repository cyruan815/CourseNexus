import { Alert, Badge, Box, Divider, Group, HoverCard, Modal, Paper, Stack, Text } from "@mantine/core";
import { IconFileDescription, IconMapPin, IconQuote } from "@tabler/icons-react";
import { type ReactNode, useRef, useState } from "react";

import { ApiError } from "../../api/errors";
import { UniversalFilePreview } from "../../components/file-preview";
import { getMaterial, getMaterialFile } from "../materials/api";
import type { Material } from "../materials/types";
import "./citation-locator.css";

export interface CitationLocatorData {
  id?: string;
  chunk_id: string | null;
  hit_text: string;
  material_id: string | null;
  material_name: string;
  page: string | number | null;
  page_index: number | null;
}

export function citationLocation(citation: CitationLocatorData): string {
  if (citation.page !== null && String(citation.page).trim()) {
    return `第 ${citation.page} 页`;
  }
  return citation.page_index !== null && citation.page_index > 0
    ? `第 ${citation.page_index + 1} 页`
    : "页码未知";
}

function pdfPageNumber(citation: CitationLocatorData): number | null {
  const explicitPage = Number(citation.page);
  if (citation.page !== null && Number.isInteger(explicitPage) && explicitPage >= 1) {
    return explicitPage;
  }
  return citation.page_index !== null && citation.page_index > 0 ? citation.page_index + 1 : null;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return "原资料已删除或当前不可访问";
}

export function CitationLocator({
  ariaLabel,
  citation,
  className,
  detailsAriaLabel,
  label,
}: {
  ariaLabel: string;
  citation: CitationLocatorData;
  className?: string;
  detailsAriaLabel?: string;
  label: ReactNode;
}) {
  const [opened, setOpened] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [material, setMaterial] = useState<Material | null>(null);
  const [previewFile, setPreviewFile] = useState<Blob | null>(null);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null);
  const requestId = useRef(0);
  const targetPage = pdfPageNumber(citation);

  async function openCitation() {
    const nextRequestId = requestId.current + 1;
    requestId.current = nextRequestId;
    setOpened(true);
    setIsLoading(false);
    setMaterial(null);
    setUnavailableReason(null);
    setPreviewFile(null);

    if (!citation.material_id) {
      setUnavailableReason("原资料已删除或当前不可访问");
      return;
    }

    setIsLoading(true);
    try {
      const nextMaterial = await getMaterial(citation.material_id);
      if (requestId.current !== nextRequestId) {
        return;
      }
      setMaterial(nextMaterial);

      if (nextMaterial.source_type === "file" && nextMaterial.material_type === "pdf" && targetPage !== null) {
        const blob = await getMaterialFile(nextMaterial.id);
        if (requestId.current !== nextRequestId) {
          return;
        }
        setPreviewFile(blob);
      }
    } catch (error) {
      if (requestId.current === nextRequestId) {
        setUnavailableReason(errorMessage(error));
      }
    } finally {
      if (requestId.current === nextRequestId) {
        setIsLoading(false);
      }
    }
  }

  function closeCitation() {
    requestId.current += 1;
    setOpened(false);
    setIsLoading(false);
    setMaterial(null);
    setUnavailableReason(null);
    setPreviewFile(null);
  }

  const previewMode = previewFile
    ? "PDF 原文"
    : material?.material_type === "markdown" || material?.material_type === "text"
      ? "解析文本"
      : "引用快照";

  return (
    <>
      <HoverCard closeDelay={100} openDelay={120} position="bottom" shadow="md" width={360} withArrow withinPortal>
        <HoverCard.Target>
          <button aria-label={ariaLabel} className={className} onClick={() => void openCitation()} type="button">
            {label}
          </button>
        </HoverCard.Target>
        <HoverCard.Dropdown
          aria-label={detailsAriaLabel ?? `${citation.material_name} 引用详情`}
          className="inline-citation-popover"
          role="tooltip"
        >
          <Stack gap="xs">
            <Box>
              <Text fw={700} lineClamp={2}>{citation.material_name}</Text>
              <Text c="dimmed" size="xs">{citationLocation(citation)}</Text>
            </Box>
            <Divider />
            <Text className="inline-citation-snippet" size="sm">{citation.hit_text}</Text>
            <Text c="blue" fw={650} size="xs">点击查看来源</Text>
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>

      <Modal
        centered
        classNames={{
          body: "citation-locator-modal__body",
          close: "citation-locator-modal__close",
          content: "citation-locator-modal",
          header: "citation-locator-modal__header",
          overlay: "citation-locator-modal__overlay",
          title: "citation-locator-modal__title-wrap",
        }}
        closeButtonProps={{ "aria-label": "关闭引用来源" }}
        onClose={closeCitation}
        opened={opened}
        size={previewFile ? "min(1080px, calc(100vw - 32px))" : "min(760px, calc(100vw - 32px))"}
        title={(
          <Group gap="sm" wrap="nowrap">
            <Box className="citation-locator-modal__title-icon" aria-hidden="true">
              <IconFileDescription size={21} stroke={1.8} />
            </Box>
            <Box className="citation-locator-modal__title-copy">
              <Text className="citation-locator-modal__eyebrow">引用来源</Text>
              <Text className="citation-locator-modal__material-name" lineClamp={1}>{citation.material_name}</Text>
            </Box>
          </Group>
        )}
        transitionProps={{ duration: 0 }}
      >
        <Stack gap="lg">
          <Group className="citation-locator-modal__meta" gap="sm">
            <Badge
              className="citation-locator-modal__mode"
              leftSection={<IconFileDescription size={13} stroke={2} />}
              variant="light"
            >
              {previewMode}
            </Badge>
            <span className="citation-locator-modal__location">
              <IconMapPin aria-hidden="true" size={14} stroke={2} />
              {citationLocation(citation)}
            </span>
          </Group>

          {isLoading ? <Text role="status">正在加载引用来源...</Text> : null}
          {unavailableReason ? (
            <Alert color="yellow" role="alert" title="来源不可用" variant="light">
              {unavailableReason}。以下仍展示回答生成时保存的合法引用快照。
            </Alert>
          ) : null}
          {material?.material_type === "pdf" && targetPage === null && !unavailableReason ? (
            <Alert color="blue" title="未打开 PDF" variant="light">
              该引用没有可验证页码，因此不会默认跳到第一页；以下展示保存的引用片段。
            </Alert>
          ) : null}

          {previewFile && material && targetPage !== null ? (
            <div className="citation-locator-modal__file-preview">
              <UniversalFilePreview
                file={previewFile}
                fileName={material.name}
                initialPage={targetPage}
                materialType={material.material_type}
                mimeType={material.mime_type}
              />
            </div>
          ) : (
            <Paper className="citation-locator-modal__snippet" radius="md" withBorder>
              <Group className="citation-locator-modal__snippet-heading" gap="sm" wrap="nowrap">
                <Box className="citation-locator-modal__quote-icon" aria-hidden="true">
                  <IconQuote size={18} stroke={2} />
                </Box>
                <Box>
                  <Text className="citation-locator-modal__snippet-kicker">回答依据</Text>
                  <Text className="citation-locator-modal__snippet-title">保存的引用片段</Text>
                </Box>
              </Group>
              <blockquote className="citation-locator-modal__quote">
                {citation.hit_text || "该历史引用没有保存可展示的文本片段。"}
              </blockquote>
              <Text className="citation-locator-modal__snapshot-note">
                这是生成回答时保存的内容快照，可用于核对回答出处。
              </Text>
            </Paper>
          )}
        </Stack>
      </Modal>
    </>
  );
}
