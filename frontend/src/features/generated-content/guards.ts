import type { Flashcard, KnowledgeItem, MindmapContent, OutlineSection, QuizQuestion } from "./types";

export function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const number = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
function arrayAt(value: unknown, key: string): unknown[] | null { return isRecord(value) && Array.isArray(value[key]) ? value[key] : null; }

export function quizQuestions(value: unknown): QuizQuestion[] | null {
  const list = arrayAt(value, "questions"); if (!list) return null;
  const valid = list.filter((item): item is Record<string, unknown> => isRecord(item) && text(item.id) && number(item.sort_order) && text(item.question_text) && Array.isArray(item.options) && item.options.length === 4 && text(item.correct_answer) && text(item.explanation));
  return valid.length === list.length && valid.length ? valid as unknown as QuizQuestion[] : null;
}
export function flashcards(value: unknown): Flashcard[] | null { const list = arrayAt(value, "cards"); if (!list) return null; const valid = list.filter((i) => isRecord(i) && text(i.id) && number(i.sort_order) && text(i.front) && text(i.back)); return valid.length === list.length && valid.length ? valid as Flashcard[] : null; }
export function outlineSections(value: unknown): OutlineSection[] | null { const list = arrayAt(value, "sections"); if (!list) return null; const valid = list.filter((i) => isRecord(i) && text(i.id) && number(i.sort_order) && text(i.title) && text(i.summary) && text(i.review_suggestion)); return valid.length === list.length && valid.length ? valid as OutlineSection[] : null; }
export function knowledgeItems(value: unknown): KnowledgeItem[] | null { const list = arrayAt(value, "items"); if (!list) return null; const valid = list.filter((i) => isRecord(i) && text(i.id) && number(i.sort_order) && text(i.name) && text(i.definition) && text(i.importance) && text(i.related_section)); return valid.length === list.length && valid.length ? valid as KnowledgeItem[] : null; }
export function mindmapContent(value: unknown): MindmapContent | null { if (!isRecord(value) || !text(value.root_node_id) || !Array.isArray(value.nodes) || !Array.isArray(value.edges) || !isRecord(value.markmap_data) || !isRecord(value.markmap_data.root)) return null; return value as unknown as MindmapContent; }
