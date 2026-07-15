import { describe, expect, it } from "vitest";

import {
  createPendingGeneration,
  formatGeneratedContentAge,
  generatedContentTitle,
  generationLoadingMessage,
} from "../../../src/features/course-workspace/generated-content-list";

describe("generated content list helpers", () => {
  it("maps the five generated content types to titles without counts", () => {
    expect(generatedContentTitle("quiz")).toBe("Quiz");
    expect(generatedContentTitle("flashcard")).toBe("知识闪卡");
    expect(generatedContentTitle("mindmap")).toBe("思维导图");
    expect(generatedContentTitle("outline")).toBe("复习提纲");
    expect(generatedContentTitle("knowledge_list")).toBe("知识点清单");
  });

  it("appends new semantic topic titles after the canonical feature name", () => {
    expect(generatedContentTitle("quiz", "第七章 物理层")).toBe("Quiz · 第七章 物理层");
    expect(generatedContentTitle("flashcard", "物理层与数据链路层")).toBe("知识闪卡 · 物理层与数据链路层");
  });

  it("extracts useful topics from legacy generated titles", () => {
    expect(generatedContentTitle("mindmap", "Knowledge Mindmap: 物理层")).toBe("思维导图 · 物理层");
    expect(generatedContentTitle("outline", "第七章 物理层复习提纲")).toBe("复习提纲 · 第七章 物理层");
  });

  it("does not treat legacy generic names or counts as chapter topics", () => {
    expect(generatedContentTitle("quiz", "Course Quiz (10 questions)")).toBe("Quiz");
    expect(generatedContentTitle("quiz", "Quiz（共 10 道）")).toBe("Quiz");
    expect(generatedContentTitle("flashcard", "记忆卡片（20张）")).toBe("知识闪卡");
    expect(generatedContentTitle("knowledge_list", "知识点清单（12项）")).toBe("知识点清单");
  });

  it("provides specific progress copy for every generated content type", () => {
    expect(generationLoadingMessage("quiz")).toBe("正在生成题目与逐项解析");
    expect(generationLoadingMessage("flashcard")).toBe("正在整理记忆卡片");
    expect(generationLoadingMessage("mindmap")).toBe("正在梳理概念关系");
    expect(generationLoadingMessage("outline")).toBe("正在整理复习结构");
    expect(generationLoadingMessage("knowledge_list")).toBe("正在提取关键概念");
  });

  it("creates independently identifiable pending generations", () => {
    const now = new Date("2026-07-15T09:00:00.000Z");
    const first = createPendingGeneration("quiz", now);
    const second = createPendingGeneration("quiz", now);

    expect(first).toMatchObject({ content_type: "quiz", created_at: now.toISOString() });
    expect(second.id).not.toBe(first.id);
  });

  it.each([
    ["2026-07-15T08:59:31.000Z", "刚刚"],
    ["2026-07-15T08:59:00.000Z", "1 分钟前"],
    ["2026-07-15T08:01:00.000Z", "59 分钟前"],
    ["2026-07-15T07:00:00.000Z", "2 小时前"],
    ["2026-07-14T09:00:00.000Z", "1 天前"],
    ["2026-07-11T08:00:00.000Z", "4 天前"],
  ])("formats %s as %s", (createdAt, expected) => {
    expect(formatGeneratedContentAge(createdAt, new Date("2026-07-15T09:00:00.000Z"))).toBe(expected);
  });

  it("treats legacy timezone-less generated timestamps as UTC", () => {
    expect(
      formatGeneratedContentAge(
        "2026-07-15T14:18:10",
        new Date("2026-07-15T16:49:45.000Z"),
      ),
    ).toBe("2 小时前");
  });
});
