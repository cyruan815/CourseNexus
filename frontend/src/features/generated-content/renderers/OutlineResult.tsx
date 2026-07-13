import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import type { OutlineSection } from "../types";

export function OutlineResult({ sections }: { sections: OutlineSection[] }) {
  const ordered = [...sections].sort((a, b) => a.sort_order - b.sort_order);
  const [active, setActive] = useState(0);
  const section = ordered[active];
  if (!section) return <Text>暂无提纲章节</Text>;
  return <div className="gc-outline"><nav aria-label="提纲章节"><Stack gap="xs">{ordered.map((item, index) => <Button key={item.id} onClick={() => setActive(index)} variant={index === active ? "light" : "subtle"}>{item.title}</Button>)}</Stack></nav><Stack><Group justify="space-between"><Text size="sm">第 {active + 1} / {ordered.length} 节</Text></Group><Title order={3}>{section.title}</Title><Text>{section.summary}</Text><Text c="dimmed"><strong>复习建议：</strong>{section.review_suggestion}</Text></Stack></div>;
}
