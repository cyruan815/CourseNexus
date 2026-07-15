import { Accordion, Text } from "@mantine/core";
import { useState } from "react";
import type { OutlineSection } from "../types";

export function OutlineResult({ sections }: { sections: OutlineSection[] }) {
  const ordered = [...sections].sort((a, b) => a.sort_order - b.sort_order);
  const [active, setActive] = useState<string | null>(null);
  if (!ordered.length) return <Text>暂无提纲章节</Text>;
  return <section className="gc-outline-timeline"><div className="gc-outline-heading"><div><span>CourseNexus · 复习材料</span><h2>复习提纲</h2></div><small>共 {ordered.length} 个章节</small></div><Accordion className="gc-outline-line" onChange={setActive} value={active} variant="separated">{ordered.map((item, itemIndex) => <Accordion.Item className={`gc-outline-section ${active === item.id ? "is-open" : ""}`} key={item.id} value={item.id}><Accordion.Control aria-label={item.title}><span>{String(itemIndex + 1).padStart(2, "0")}</span><strong>{item.title}</strong></Accordion.Control><Accordion.Panel><div className="gc-outline-details"><div><p>{item.summary}</p><aside><b>复习建议</b>{item.review_suggestion}</aside></div></div></Accordion.Panel></Accordion.Item>)}</Accordion></section>;
}
