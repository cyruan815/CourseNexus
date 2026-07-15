import { Alert, Select, Text, TextInput } from "@mantine/core";
import { useMemo, useState } from "react";
import { updateKnowledgeItemLearningState } from "../../course-workspace/api";
import { knowledgeItems } from "../guards";
import type { KnowledgeItem } from "../types";

const importanceLabel = { high: "高", medium: "中", low: "低" };

interface KnowledgeListResultProps {
  items: KnowledgeItem[];
  generatedContentId: string;
}

export function KnowledgeListResult({
  items: sourceItems,
  generatedContentId,
}: KnowledgeListResultProps) {
  const initialItems = useMemo(
    () => [...sourceItems]
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({ ...item, learned: item.learned === true })),
    [sourceItems],
  );
  const [items, setItems] = useState<KnowledgeItem[]>(initialItems);
  const [query, setQuery] = useState("");
  const [importance, setImportance] = useState<string | null>("all");
  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const filtered = items.filter((item) => (
    (importance === "all" || item.importance === importance)
    && `${item.name} ${item.definition} ${item.related_section}`.toLowerCase().includes(query.toLowerCase())
  ));
  const learnedCount = items.filter((item) => item.learned === true).length;
  const percentage = items.length ? Math.round((learnedCount / items.length) * 100) : 0;

  const toggleLearned = async (item: KnowledgeItem) => {
    if (savingItemId !== null) return;
    const previousItems = items;
    const nextLearned = item.learned !== true;
    const optimisticItems = items.map((candidate) => (
      candidate.id === item.id ? { ...candidate, learned: nextLearned } : candidate
    ));
    setItems(optimisticItems);
    setSavingItemId(item.id);
    setSaveError(null);
    try {
      const updated = await updateKnowledgeItemLearningState(
        generatedContentId,
        item.id,
        nextLearned,
      );
      const savedItems = knowledgeItems(updated.content_json);
      if (!savedItems) throw new Error("保存后的知识点清单不可读取");
      setItems([...savedItems].sort((a, b) => a.sort_order - b.sort_order));
    } catch (error) {
      setItems(previousItems);
      setSaveError(error instanceof Error ? error.message : "学习状态保存失败，请重试");
    } finally {
      setSavingItemId(null);
    }
  };

  return (
    <section className="gc-knowledge-glossary">
      <div className="gc-knowledge-heading">
        <div>
          <span>CourseNexus · 核心概念</span>
          <h2>知识点清单</h2>
        </div>
        <small>{items.length} 个知识点</small>
      </div>

      <div className="gc-knowledge-progress-summary">
        <div className="gc-knowledge-progress-copy">
          <div><strong>学习进度</strong><span>已学习 {learnedCount} / {items.length}</span></div>
          <b>{percentage}%</b>
        </div>
        <div
          aria-label={`学习进度 ${percentage}%`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={percentage}
          className="gc-knowledge-progress-track"
          role="progressbar"
        >
          <span style={{ width: `${percentage}%` }} />
        </div>
      </div>

      {saveError ? <Alert color="red" mb="md" role="alert">{saveError}</Alert> : null}

      <div className="gc-knowledge-toolbar">
        <TextInput
          onChange={(event) => setQuery(event.currentTarget.value)}
          placeholder="搜索知识点"
          value={query}
        />
        <Select
          data={[
            { value: "all", label: "全部重要程度" },
            { value: "high", label: "高" },
            { value: "medium", label: "中" },
            { value: "low", label: "低" },
          ]}
          onChange={setImportance}
          value={importance}
        />
      </div>

      {filtered.length ? (
        <div className="gc-knowledge-terms">
          {filtered.map((item) => {
            const learned = item.learned === true;
            const saving = savingItemId === item.id;
            return (
              <article className={learned ? "is-learned" : undefined} key={item.id}>
                <button
                  aria-label={learned ? `取消${item.name}的已学习状态` : `标记${item.name}为已学习`}
                  className="gc-knowledge-learned-toggle"
                  disabled={savingItemId !== null}
                  onClick={() => void toggleLearned(item)}
                  type="button"
                >
                  <span aria-hidden="true" className={saving ? "is-saving" : undefined}>
                    {saving ? "" : learned ? "✓" : ""}
                  </span>
                </button>
                <h3>{item.name}</h3>
                <p>{item.definition}</p>
                <span
                  aria-label={`重要程度：${importanceLabel[item.importance]}`}
                  className={`gc-knowledge-importance is-${item.importance}`}
                >
                  {importanceLabel[item.importance]}
                </span>
              </article>
            );
          })}
        </div>
      ) : <Text c="dimmed">没有符合条件的知识点</Text>}
    </section>
  );
}
