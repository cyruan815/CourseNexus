import { Select, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import type { KnowledgeItem } from "../types";

const importanceLabel = { high: "高", medium: "中", low: "低" };

export function KnowledgeListResult({ items }: { items: KnowledgeItem[] }) {
  const [query, setQuery] = useState(""); const [importance, setImportance] = useState<string | null>("all");
  const filtered = [...items].sort((a, b) => a.sort_order - b.sort_order).filter((item) => (importance === "all" || item.importance === importance) && `${item.name} ${item.definition} ${item.related_section}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="gc-knowledge-glossary"><div className="gc-knowledge-heading"><div><span>CourseNexus · 核心概念</span><h2>知识点清单</h2></div><small>{filtered.length} 个知识点</small></div><div className="gc-knowledge-toolbar"><TextInput onChange={(event) => setQuery(event.currentTarget.value)} placeholder="搜索知识点" value={query} /><Select data={[{ value: "all", label: "全部重要程度" }, { value: "high", label: "高" }, { value: "medium", label: "中" }, { value: "low", label: "低" }]} onChange={setImportance} value={importance} /></div>{filtered.length ? <div className="gc-knowledge-terms">{filtered.map((item) => <article key={item.id}><h3>{item.name}</h3><p>{item.definition}</p><span aria-label={`重要程度：${importanceLabel[item.importance]}`} className={`gc-knowledge-importance is-${item.importance}`}>{importanceLabel[item.importance]}</span></article>)}</div> : <Text c="dimmed">没有符合条件的知识点</Text>}</section>;
}
