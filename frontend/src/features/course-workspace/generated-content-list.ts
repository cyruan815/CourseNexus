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

const loadingMessages: Record<string, string> = {
  flashcard: "正在整理记忆卡片",
  knowledge_list: "正在提取关键概念",
  mindmap: "正在梳理概念关系",
  outline: "正在整理复习结构",
  quiz: "正在生成题目与逐项解析",
};

let pendingGenerationSequence = 0;

export function generatedContentTitle(contentType: string): string {
  return contentTitles[contentType] ?? contentType;
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
  const elapsedMilliseconds = Math.max(0, now.getTime() - Date.parse(createdAt));
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
