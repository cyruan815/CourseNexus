import { Alert, Button, Group, Stack, Text, Title } from "@mantine/core";
import { loadCSS, loadJS, Markmap } from "markmap-view";
import { useEffect, useRef, useState } from "react";
import type { MindmapContent } from "../types";

type MarkmapInstance = {
  fit: () => void | Promise<void>;
  rescale: (scale: number) => void;
  setData: (data: unknown) => void | Promise<void>;
  destroy?: () => void;
};

type LoadableStyles = Parameters<typeof loadCSS>[0];
type LoadableScripts = Parameters<typeof loadJS>[0];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isHttpsUrl(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try { return new URL(value).protocol === "https:"; } catch { return false; }
}

function loadableAssets(value: unknown): { styles: LoadableStyles; scripts: LoadableScripts } {
  const styles: LoadableStyles = [];
  const scripts: LoadableScripts = [];
  if (!isRecord(value)) return { styles, scripts };
  const rawStyles = Array.isArray(value.styles) ? value.styles : [];
  const rawScripts = Array.isArray(value.scripts) ? value.scripts : [];
  for (const item of rawStyles) {
    if (!isRecord(item)) continue;
    if (item.type === "style" && typeof item.data === "string") styles.push({ type: "style", data: item.data });
    if (item.type === "stylesheet" && isRecord(item.data) && isHttpsUrl(item.data.href)) styles.push({ type: "stylesheet", data: { href: item.data.href } });
  }
  for (const item of rawScripts) {
    if (!isRecord(item) || item.type !== "script" || !isRecord(item.data) || !isHttpsUrl(item.data.src)) continue;
    const data: { src: string; async?: boolean; defer?: boolean } = { src: item.data.src };
    if (typeof item.data.async === "boolean") data.async = item.data.async;
    if (typeof item.data.defer === "boolean") data.defer = item.data.defer;
    scripts.push({ type: "script", data });
  }
  return { styles, scripts };
}

function withFold(value: unknown, collapsed: boolean, isRoot = true): unknown {
  if (!value || typeof value !== "object") return value;
  const node = value as Record<string, unknown>;
  return {
    ...node,
    payload: { ...(node.payload as Record<string, unknown> | undefined), fold: collapsed && !isRoot ? 1 : 0 },
    children: Array.isArray(node.children) ? node.children.map((child) => withFold(child, collapsed, false)) : undefined,
  };
}

export function MindmapResult({ content }: { content: MindmapContent }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const instanceRef = useRef<MarkmapInstance | null>(null);
  const [failed, setFailed] = useState(false);
  const [failureDetail, setFailureDetail] = useState("");

  useEffect(() => {
    if (!svgRef.current || !content.markmap_data?.root) { setFailed(true); return; }
    let cancelled = false;
    const initialize = async () => {
      try {
        const assets = loadableAssets(content.markmap_data.assets);
        await loadCSS(assets.styles);
        await loadJS(assets.scripts);
        if (cancelled || !svgRef.current) return;
        const instance = Markmap.create(svgRef.current) as unknown as MarkmapInstance;
        instanceRef.current = instance;
        await Promise.resolve(instance.setData(withFold(content.markmap_data.root, true, false)));
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        if (cancelled) return;
        await Promise.resolve(instance.fit());
        if (!cancelled) { setFailureDetail(""); setFailed(false); }
      } catch (error: unknown) {
        if (!cancelled) { setFailureDetail(error instanceof Error ? error.message : "unknown error"); setFailed(true); }
      }
    };
    void initialize();
    return () => { cancelled = true; instanceRef.current?.destroy?.(); instanceRef.current = null; };
  }, [content]);

  if (failed) return <Stack><Alert color="yellow">图形视图暂不可用，已显示结构化内容。{failureDetail ? ` (${failureDetail})` : ""}</Alert>{content.nodes.map((node) => <section className="gc-mindmap-fallback" key={node.id}><Title order={3}>{node.label}</Title>{node.summary ? <Text>{node.summary}</Text> : null}</section>)}</Stack>;

  return <Stack>
    <Group gap="xs"><Button aria-label="适配画布" onClick={() => void instanceRef.current?.fit()} variant="default">适配</Button><Button aria-label="放大" onClick={() => instanceRef.current?.rescale(1.2)} variant="default">+</Button><Button aria-label="缩小" onClick={() => instanceRef.current?.rescale(0.8)} variant="default">-</Button><Button onClick={() => instanceRef.current?.setData(withFold(content.markmap_data.root, false))} variant="default">全部展开</Button><Button onClick={() => instanceRef.current?.setData(withFold(content.markmap_data.root, true, false))} variant="default">全部收起</Button></Group>
    <div className="gc-mindmap-canvas"><svg aria-label="思维导图" ref={svgRef} /></div>
  </Stack>;
}
