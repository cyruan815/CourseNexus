export interface PendingGeneration {
  id: string;
  content_type: string;
  created_at: string;
}

const contentTitles: Record<string, string> = {
  flashcard: "知识闪卡",
  knowledge_list: "知识点清单",
  mindmap: "思维导图",
  outline: "复习提纲",
  quiz: "Quiz",
};

const legacyTitleAliases: Record<string, string[]> = {
  flashcard: ["Flashcards", "记忆卡片", "知识闪卡"],
  knowledge_list: ["Knowledge List", "知识点清单"],
  mindmap: ["Knowledge Mindmap", "Mind Map", "思维导图"],
  outline: ["Review Outline", "Generated Outline Demo", "复习提纲"],
  quiz: ["Course Quiz", "课程自测", "Quiz"],
};

const loadingMessages: Record<string, string> = {
  flashcard: "正在整理记忆卡片",
  knowledge_list: "正在提取关键概念",
  mindmap: "正在梳理概念关系",
  outline: "正在整理复习结构",
  quiz: "正在生成题目与逐项解析",
};

let pendingGenerationSequence = 0;

function semanticTopic(contentType: string, storedTitle: string | null | undefined): string | null {
  if (!storedTitle?.trim()) {
    return null;
  }

  let candidate = storedTitle
    .trim()
    .replace(/\s*[（(]\s*(?:共\s*)?\d+\s*(?:questions?|cards?|sections?|items?|道(?:题)?|题|张|节|项|个节点)\s*[）)]\s*$/i, "")
    .trim();
  const aliases = legacyTitleAliases[contentType] ?? [];

  for (const alias of aliases) {
    if (candidate.localeCompare(alias, undefined, { sensitivity: "accent" }) === 0) {
      return null;
    }

    const prefixed = candidate.match(new RegExp(`^${alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*[:：·—-]\\s*(.+)$`, "i"));
    if (prefixed?.[1]) {
      candidate = prefixed[1].trim();
      break;
    }

    if (candidate.endsWith(alias) && candidate.length > alias.length) {
      candidate = candidate.slice(0, -alias.length).trim();
      break;
    }
  }

  return /[\u3400-\u4dbf\u4e00-\u9fff]/.test(candidate) ? candidate : null;
}

export function generatedContentTitle(contentType: string, storedTitle?: string | null): string {
  const featureTitle = contentTitles[contentType] ?? contentType;
  const topic = semanticTopic(contentType, storedTitle);
  return topic ? `${featureTitle} · ${topic}` : featureTitle;
}

export function generationLoadingMessage(contentType: string): string {
  return loadingMessages[contentType] ?? "正在生成内容";
}

export function createPendingGeneration(contentType: string, now = new Date()): PendingGeneration {
  pendingGenerationSequence += 1;
  return {
    id: `pending-${now.getTime()}-${pendingGenerationSequence}`,
    content_type: contentType,
    created_at: now.toISOString(),
  };
}

export function formatGeneratedContentAge(createdAt: string, now = new Date()): string {
  const hasExplicitTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(createdAt);
  const normalizedCreatedAt = hasExplicitTimezone ? createdAt : `${createdAt}Z`;
  const elapsedMilliseconds = Math.max(0, now.getTime() - Date.parse(normalizedCreatedAt));
  const elapsedMinutes = Math.floor(elapsedMilliseconds / 60_000);

  if (elapsedMinutes < 1) {
    return "刚刚";
  }
  if (elapsedMinutes < 60) {
    return `${elapsedMinutes} 分钟前`;
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) {
    return `${elapsedHours} 小时前`;
  }

  return `${Math.floor(elapsedHours / 24)} 天前`;
}
