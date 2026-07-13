# Quiz Generation

Quiz uses the complete selected material context in one structured model call. The POC supports single-choice questions only. Each model question contains A-D options, one correct option, a concise explanation, and difficulty.

The backend limits the result to `question_count`, validates nonblank text and ordered A-D options, rejects duplicate question text, and adds `q_001...` plus continuous `sort_order`. Final questions contain no source or citation fields.
# 2026-07-13 质量与渲染更新

- `QuizDraft.hint` 是可选兼容字段；未生成提示的旧记录保持原 JSON 形态。
- Schema 拒绝重复选项文本，Prompt 强调概念理解、辨析、简单应用、可信干扰项和唯一答案。
- `QuizResult.tsx` 一次展示一题，选择后立即判题并显示答案与解析，完成后显示当前会话正确率；不保存 attempt。
