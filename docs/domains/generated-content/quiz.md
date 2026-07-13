# Quiz Generation

Quiz uses the complete selected material context in one structured model call. The POC supports single-choice questions only. Each model question contains A-D options, one correct option, a concise explanation, and difficulty.

The backend limits the result to `question_count`, validates nonblank text and ordered A-D options, rejects duplicate question text, and adds `q_001...` plus continuous `sort_order`. Final questions contain no source or citation fields.
