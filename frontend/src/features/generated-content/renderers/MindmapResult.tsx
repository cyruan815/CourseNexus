import { Alert, Button, Group, Stack, Text, Title } from "@mantine/core";
import { Markmap } from "markmap-view";
import { useEffect, useRef, useState } from "react";
import type { MindmapContent } from "../types";

type MarkmapInstance = {
  fit: () => void | Promise<void>;
  rescale: (scale: number) => void;
  setData: (data: unknown) => void | Promise<void>;
  destroy?: () => void;
};

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
    try {
      const instance = Markmap.create(svgRef.current) as unknown as MarkmapInstance;
      instanceRef.current = instance;
      void Promise.resolve(instance.setData(withFold(content.markmap_data.root, true, false))).then(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))).then(() => {
        if (!cancelled) { void instance.fit(); setFailed(false); }
      }).catch((error: unknown) => { if (!cancelled) { setFailureDetail(error instanceof Error ? error.message : "unknown error"); setFailed(true); } });
    } catch (error: unknown) {
      setFailureDetail(error instanceof Error ? error.message : "unknown error"); setFailed(true);
    }
    return () => { cancelled = true; instanceRef.current?.destroy?.(); instanceRef.current = null; };
  }, [content]);

  if (failed) return <Stack><Alert color="yellow">图形视图暂不可用，已显示结构化内容。{failureDetail ? ` (${failureDetail})` : ""}</Alert>{content.nodes.map((node) => <section className="gc-mindmap-fallback" key={node.id}><Title order={3}>{node.label}</Title>{node.summary ? <Text>{node.summary}</Text> : null}</section>)}</Stack>;

  return <Stack>
    <Group gap="xs"><Button aria-label="适配画布" onClick={() => void instanceRef.current?.fit()} variant="default">适配</Button><Button aria-label="放大" onClick={() => instanceRef.current?.rescale(1.2)} variant="default">+</Button><Button aria-label="缩小" onClick={() => instanceRef.current?.rescale(0.8)} variant="default">-</Button><Button onClick={() => instanceRef.current?.setData(withFold(content.markmap_data.root, false))} variant="default">全部展开</Button><Button onClick={() => instanceRef.current?.setData(withFold(content.markmap_data.root, true, false))} variant="default">全部收起</Button></Group>
    <div className="gc-mindmap-canvas"><svg aria-label="思维导图" ref={svgRef} /></div>
  </Stack>;
}
