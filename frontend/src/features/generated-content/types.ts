export type ChoiceId = "A" | "B" | "C" | "D";

export interface QuizQuestion {
  id: string; sort_order: number; question_text: string;
  options: Array<{ id: ChoiceId; text: string; explanation?: string | null }>;
  correct_answer: ChoiceId; explanation: string; difficulty: string; hint?: string | null;
}

export interface Flashcard {
  id: string; sort_order: number; front: string; back: string; tags: string[];
  mastery_status: "unknown"; explanation?: string | null;
}

export interface OutlineSection {
  id: string; sort_order: number; title: string; summary: string; review_suggestion: string;
}

export interface KnowledgeItem {
  id: string; sort_order: number; name: string; definition: string;
  importance: "low" | "medium" | "high"; related_section: string; learned?: boolean;
}

export type TaskTestQuestionType = "single_choice" | "multiple_choice" | "true_false" | "short_answer";
export type TaskTestAnswer = string | boolean | string[];

export interface TaskTestQuestion {
  id: string;
  sort_order: number;
  question_text: string;
  question_type: TaskTestQuestionType;
  options: Array<{ id: string; text: string }>;
  correct_answer: TaskTestAnswer;
  explanation?: string | null;
  source_citation_ids?: string[];
}

export interface SerializedMarkmapAssets {
  styles?: unknown[];
  scripts?: unknown[];
}

export interface MindmapContent {
  root_node_id: string;
  nodes: Array<{ id: string; label: string; summary?: string; level: number }>;
  edges: Array<{ from: string; to: string; relation: "child" | "related" }>;
  markmap_data: { root: Record<string, unknown>; features?: Record<string, unknown>; assets?: SerializedMarkmapAssets };
}
