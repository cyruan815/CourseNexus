import { Badge, Group, Select, Stack, Text, TextInput, Title } from "@mantine/core";
import { useState } from "react";
import type { KnowledgeItem } from "../types";

export function KnowledgeListResult({ items }: { items: KnowledgeItem[] }) {
  const [query, setQuery] = useState(""); const [importance, setImportance] = useState<string | null>("all");
  const filtered = [...items].sort((a, b) => a.sort_order - b.sort_order).filter((item) => (importance === "all" || item.importance === importance) && `${item.name} ${item.definition} ${item.related_section}`.toLowerCase().includes(query.toLowerCase()));
  return <Stack><Group grow><TextInput onChange={(event) => setQuery(event.currentTarget.value)} placeholder="搜索知识点" value={query} /><Select data={[{ value: "all", label: "全部重要程度" }, { value: "high", label: "高" }, { value: "medium", label: "中" }, { value: "low", label: "低" }]} onChange={setImportance} value={importance} /></Group>{filtered.length ? filtered.map((item) => <section className="gc-knowledge-item" key={item.id}><Group justify="space-between"><Title order={3}>{item.name}</Title><Badge>{item.importance}</Badge></Group><Text>{item.definition}</Text><Text c="dimmed" size="sm">{item.related_section}</Text></section>) : <Text c="dimmed">没有符合条件的知识点</Text>}</Stack>;
}
