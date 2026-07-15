import { Text } from "@mantine/core";
import { useState } from "react";
import type { OutlineSection } from "../types";

export function OutlineResult({ sections }: { sections: OutlineSection[] }) {
  const ordered = [...sections].sort((a, b) => a.sort_order - b.sort_order);
  const [active, setActive] = useState<number | null>(null);
  if (!ordered.length) return <Text>暂无提纲章节</Text>;
  return <section className="gc-outline-timeline"><div className="gc-outline-heading"><div><span>CourseNexus · 复习材料</span><h2>复习提纲</h2></div><small>共 {ordered.length} 个章节</small></div><div className="gc-outline-line">{ordered.map((item, itemIndex) => { const open = active === itemIndex; return <article className={`gc-outline-section ${open ? "is-open" : ""}`} key={item.id}><button aria-expanded={open} aria-label={item.title} onClick={() => setActive(open ? null : itemIndex)} type="button"><span>{String(itemIndex + 1).padStart(2, "0")}</span><strong>{item.title}</strong><i>⌄</i></button><div className="gc-outline-details"><div>{open ? <><p>{item.summary}</p><aside><b>复习建议</b>{item.review_suggestion}</aside></> : null}</div></div></article>; })}</div></section>;
}
