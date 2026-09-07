# S06 任务讲义与任务测试题实现

## 范围

S06 为计划学习模式的二级任务提供按需生成内容：

- `learn` / `review` 二级任务只能生成 `handout` 任务讲义。
- `quiz` / `test` 二级任务只能生成 `task_test` 任务测试题。
- `learn` 表示学习讲义和新内容；`review` 表示复习讲义，只回顾计划中此前已经安排学习过的内容；只有 `quiz` / `test` 可以携带 `generation_parameters.task_test` 和明确题量要求。
- `learn` 讲义使用计划阶段清理后的正文 chunk 引用；目录页、版权页、感谢页和章节小结页不得与正文 chunk 混合作为普通 `learn` 范围，避免提前混入后续主题。
- 生成内容统一写入 `ai_generated_contents`，通过 `study_subtask_id` 绑定二级任务。
- 任务讲义只在学习计划执行上下文中展示；课程详情的课程级生成内容列表排除 `content_type=handout` 且 `study_subtask_id` 非空的记录，但不删除讲义，也不影响详情、重新生成或 PDF 导出。
- 不新增 `handouts`、`task_tests` 或其他业务表，不修改 migration；前端接入任务内容的生成、任务讲义只读展示、任务测试题本地逐题交互与导出入口。
- 当前只保存二级任务级 `related_material_ids_json`；P0 不新增 chunk 级任务范围字段，引用范围由当次材料上下文批次校验保证。

## 代码入口

- Handout schema：`backend/app/modules/generation/generators/handout/schemas.py`
- Handout generator：`backend/app/modules/generation/generators/handout/generator.py`
- Task test schema：`backend/app/modules/generation/generators/task_test/schemas.py`
- Task test generator：`backend/app/modules/generation/generators/task_test/generator.py`
- API：`backend/app/modules/learning_execution/router.py`
- Service：`backend/app/modules/learning_execution/service.py`
- Repository：`backend/app/modules/learning_execution/repository.py`
- Export API：`backend/app/modules/exports/router.py`
- Export service / renderer：`backend/app/modules/exports/service.py`、`backend/app/modules/exports/renderer.py`
- 前端 API：`frontend/src/features/study-plans/api.ts`
- 前端类型：`frontend/src/features/study-plans/types.ts`
- 前端页面：`frontend/src/pages/StudyTaskExecutionPage.tsx`
- 测试入口：`backend/tests/modules/generation/test_handout_generator.py`、`backend/tests/modules/generation/test_task_test_generator.py`、`backend/tests/modules/learning_execution/test_task_content_api.py`、`backend/tests/modules/exports/test_exports_api.py`、`backend/tests/integration/test_task_content_generation_flow.py`
- 前端测试入口：`frontend/tests/features/study-plans/api.test.ts`、`frontend/tests/features/generated-content/task-test-result.test.tsx`、`frontend/tests/features/generated-content/generated-content-renderer.test.tsx`、`frontend/tests/pages/generated-content-detail.test.tsx`、`frontend/tests/pages/study-plan-pages.test.tsx`

## API

- `POST /api/v1/study-subtasks/{subtask_id}/handouts`
- `POST /api/v1/study-subtasks/{subtask_id}/task-tests`
- `GET /api/v1/study-subtasks/{subtask_id}/execution-context`
- `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown`
- `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf`

两个 POST 接口都返回统一成功 envelope，`data` 为 `GeneratedContentRead`。默认重复请求是幂等的：同一个 `study_subtask_id + content_type` 已存在未删除且 `generation_status=success` 的内容时，接口直接返回最近一次成功内容，不调用模型、不新增 `AIGeneratedContent`。请求体可传 `force_regenerate=true` 显式重新生成新内容；failed 记录不会作为幂等命中结果。执行上下文会返回最近一次成功生成的 `handout_content_id` 或 `task_test_content_id`；失败记录不会作为执行页内容 ID 返回。

前端 C9 只接入执行页中的按需生成入口：

- `learn` / `review` 二级任务显示“任务讲义”，默认调用 `POST /api/v1/study-subtasks/{subtask_id}/handouts`，请求 `{ "force_regenerate": false }`。
- `quiz` / `test` 二级任务显示“任务测试题”，默认调用 `POST /api/v1/study-subtasks/{subtask_id}/task-tests`，请求 `{ "force_regenerate": false }`；不传 `parameters` 时由后端读取计划快照中的默认测试题参数。
- 若 execution-context 已返回 `handout_content_id` 或 `task_test_content_id`，前端不自动重新生成，只显示查看入口和“重新生成”按钮。
- “重新生成”显式传 `force_regenerate=true`，由后端创建新的成功内容或失败记录。
- 生成成功后，执行页用返回的 `GeneratedContentRead.id/title/status` 局部更新内容面板，并通过 `/generated-contents/{id}` 跳转到生成内容详情页。2026-07-15 前端为 `task_test` 接入本地逐题交互：执行页和生成内容详情页都读取 `GeneratedContentRead.content_json.questions`，用户提交单道题后才显示正确答案 / 参考答案和解析；选择题与判断题只做浏览器内存内即时判断，简答题不自动判分。该视图不保存 attempt 历史。
- 生成失败只展示错误提示，不修改二级任务完成状态，不触发 completion，也不写打卡。
- C9/C11 不接入测试题作答持久化、后端判分、attempt 历史或反馈闭环；当前逐题提交反馈只存在浏览器内存，刷新后可以丢失。
- 前端 C11 已接入执行页导出入口：`handout` 只显示“导出PDF”，调用 `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf`；`task_test` 只显示“导出Markdown”，调用 `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown`。导出入口只在 execution-context 或本次生成成功返回已有内容 ID 后显示；未生成、生成失败或内容类型不匹配时不展示假导出按钮。2026-07-14 前端展示文案已从“今日讲义”调整为“任务讲义”，避免误解为全局今日唯一讲义；后端 `handout` 内容类型和导出文件名保持不变。
- 2026-07-15 执行页已在“任务讲义”内容区内直接渲染成功 `handout` 的 Markdown 正文：页面通过 `GET /api/v1/generated-contents/{generated_content_id}` 读取 `GeneratedContentRead.content`，复用 `frontend/src/features/generated-content/renderers/handout/HandoutMarkdownRenderer.tsx` 展示标题、段落、列表、加粗、代码块、GFM 表格、`$...$` / `$$...$$` 数学公式和 GitHub alert 风格 callout；不读取旧 `content_json.sections`，不展示空引用面板，也不伪造逐条来源。已有成功讲义、本次生成成功讲义和生成内容详情页复用同一讲义渲染组件。

任务测试题 Markdown 导出接口返回文件流，不包成功 envelope。它复用 `GeneratedContentRead` 的用户归属校验，只支持当前用户自己的成功 `task_test`；非 `task_test` 返回 `EXPORT_UNSUPPORTED_CONTENT_TYPE`，非 success 返回 `EXPORT_CONTENT_NOT_READY`，畸形 `content_json` 返回 `EXPORT_CONTENT_INVALID`。renderer 会把题目、选项、答案、解析和引用来源写入 Markdown；`source_citation_ids` 只和 `source_citations[].id` 匹配，缺失时写 `Sources: unavailable`，不伪造来源。

任务讲义 PDF 导出接口同样返回文件流，不包成功 envelope。它只支持当前用户自己的成功 `handout`，生成文件名为 `handout-{generated_content_id}.pdf`；非 `handout` 返回 `EXPORT_UNSUPPORTED_CONTENT_TYPE`，非 success 返回 `EXPORT_CONTENT_NOT_READY`，畸形 `content_json` 返回 `EXPORT_CONTENT_INVALID`。PDF renderer 使用 `markdown-it-py` + Jinja2 生成语义化 HTML，注入本地 KaTeX CSS/JS 对 `$...$` 与 `$$...$$` 数学公式做浏览器端排版，再通过 Playwright Chromium 按 A4 打印为 PDF；不保存导出历史，渲染异常返回 `EXPORT_FAILED`，不影响原 generated content。

## 幂等与重新生成

生成入口在完成用户、课程、计划、任务层级和二级任务类型校验后，先查询当前用户下同一 `study_subtask_id + content_type` 最近一次未删除成功内容：

- `force_regenerate=false` 或省略时，命中 success 直接返回该 `GeneratedContentRead`，不会创建新的 `gen_...` 记录，也不会调用 handout / task-test generator 或模型 provider。
- `force_regenerate=true` 时跳过幂等命中，按正常生成流程创建新的 `AIGeneratedContent(generation_status=success)` 和引用。
- `generation_status=failed` 只保留失败审计和错误码，不会阻止下一次请求重新生成，也不会被 execution-context 当作内容 ID。
- execution-context 通过相同的“最近未删除 success”查询返回内容 ID；如果最新记录是 failed，仍返回最近一次 success，若没有 success 则返回 `null`。

幂等命中路径只做一次生成内容查询，模型调用次数为 0。真正生成路径中，handout 仍按材料批次 map/reduce；task_test 会把当前二级任务允许的全部材料批次汇总为一次候选上下文，只调用一次 task-test generator 生成固定题量。

## 数据流

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant LE as learning-execution
    participant MC as material-context
    participant GEN as handout/task-test generator
    participant MP as ModelProvider
    participant DB as ai_generated_contents / source_citations

    FE->>LE: POST /api/v1/study-subtasks/{id}/handouts or /api/v1/study-subtasks/{id}/task-tests
    LE->>LE: verify user, course, plan, task, subtask
    LE->>LE: verify subtask_type matches content_type
    LE->>MC: iter_material_context_batches(MaterialScope from related_material_ids_json)
    MC-->>LE: MaterialContextBatch list
    alt handout
        LE->>GEN: run_material_coverage(map each batch)
        GEN->>MP: generate_text(Markdown prompt)
        GEN-->>LE: Markdown GeneratorOutput
    else task_test
        LE->>GEN: generate once with all current subtask batches
        GEN->>GEN: internally summarize candidate points from all chunks
        GEN->>MP: generate_structured(TaskTestContent schema)
        GEN->>GEN: validate count/type/id/options/duplicates/citations
        GEN-->>LE: fixed-size GeneratorOutput
    end
    LE->>DB: save AIGeneratedContent; task_test also saves SourceCitation
    LE-->>FE: GeneratedContentRead
```

关键约束：

- 材料范围只能来自 `StudySubTask.related_material_ids_json`。
- `MaterialScope.include_all_parsed_materials = false`，`material_ids` 为二级任务关联资料 ID。
- S06 使用 `iter_material_context_batches()` 读取当前二级任务的全材料上下文，不使用 Top-K 检索，也不调用旧的 `resolve_context()`。
- Handout 使用当前二级任务允许的材料范围生成一整篇 Markdown 讲义；上下文可放入单次 prompt 时优先一次生成，必须分批时由 reducer 重新合成为最终整篇 Markdown，不把多个 batch 草稿硬拼成最终稿。
- Task test 不再“每个 batch 各生成一整套题再拼接”；它把当前二级任务的所有批次一次性传给 task-test generator，由 prompt 要求先在内部汇总候选考点，再只输出最终 `question_count` 道题。
- Task test 的 `question_count` 是最终硬约束；当参数包含 `question_type_counts` 时，每种 `question_type` 的输出数量也是硬约束。输出多题、少题、每种题型数量不匹配、题型越界、`id` / `sort_order` 不连续、选项答案不自洽、重复或高度相似题干都会返回 `GENERATION_SCHEMA_INVALID`。
- Handout 不保存逐条 `source_citations`；来源说明放在 Markdown 顶部。Task test 的题目引用必须来自本次材料上下文的 chunk id，且必须落在当前二级任务允许的材料批次内，不允许伪造 fallback 引用。

## 内容结构

`handout` 采用 Markdown-first 存储：

- `AIGeneratedContent.title` 使用当前二级任务标题派生，通常为 `{subtask.title}讲义`。
- `AIGeneratedContent.content` 保存一整篇可导出的 Markdown 讲义正文。
- `handout.content_json` 只保存轻量元信息：`{"format":"markdown","schema_version":1}`；不再保存旧版 `sections/blocks` 结构，也不兼容旧结构化 handout 历史导出。
- Handout 不生成逐条 `SourceCitation`。Markdown 一级标题下方写来源说明，例如 `本讲义基于《资料名》中“二级任务标题”相关内容生成。`，前端详情页不展示引用侧栏。
- 后端保存前不正则改写数学公式内容；Handout prompt 负责约束模型输出 `$...$` / `$$...$$`，PDF 导出在临时 HTML 中通过本地 KaTeX 完成数学排版。
- Handout prompt 明确要求块级公式使用 `$$...$$`、行内公式使用 `$...$`，禁止 `\[...\]`、`\(...\)` 和单独一行 `[` / `]` 包公式；公式不要放进代码块，变量解释使用普通 Markdown 列表；自测题或填空题的空格线使用全角低线 `＿＿＿＿`，不要使用连续 ASCII 下划线 `______`，避免 Markdown 渲染吞掉填空线。

`task_test` 仍采用结构化 JSON 存储。`task_test.content_json` 包含 `instructions` 和 `questions`。每道题包含 `id`、`question_type`、`question_text`、`options`、`correct_answer`、`explanation`、`source_citation_ids` 和 `sort_order`。题型支持 `single_choice`、`multiple_choice`、`true_false` 和 `short_answer`。
任务测试题结构不变量：

- `questions.length == request.parameters.question_count`。
- `question_type` 必须属于请求的 `question_types` 白名单。`question_type_counts` 存在时，实际输出中每种题型数量必须与请求分布完全一致。
- 题目 `id` 必须为 `q_1..q_N`，`sort_order` 必须为 `1..N`，二者都按最终题目顺序连续且唯一。
- `single_choice` / `multiple_choice` 必须恰好有 4 个 options；生成器按每道题自己的 options 顺序将 option id 归一化为 `A`、`B`、`C`、`D`，并同步映射 `correct_answer`。
- 单选答案必须是命中 option id 的字符串；多选答案必须是无重复字符串数组，且所有值命中 option id。
- `true_false` 答案必须是 boolean；`short_answer` 不要求 options，答案为非空字符串。
- 题干经空白折叠和小写归一后不得重复；长度不少于 8 的归一化题干使用相似度阈值拒绝高度相似题。

## 失败与补偿

权限失败、任务不存在和二级任务类型不匹配发生在生成流程前，不创建生成记录。

进入生成流程后，材料缺失、材料覆盖失败、schema 校验失败、测试题硬约束不满足和模型调用失败都会保存一条 `AIGeneratedContent`：

- `generation_status = failed`
- `study_subtask_id = 当前二级任务`
- `content_type = handout` 或 `task_test`
- `error_code = 稳定错误码`

保存失败记录后，接口仍返回统一错误 envelope。失败记录只作为审计和重试依据，不参与幂等命中；下一次默认请求如果没有 success 会重新尝试生成。生成失败不修改二级任务完成状态，不汇总一级任务状态，也不写 `checkin_records`。

如果 task_test 模型输出无法同时满足总题量、每种题型数量、题型白名单、结构、去重和引用约束，后端返回 `GENERATION_SCHEMA_INVALID` 并保存 failed 记录，不做静默截断、不用部分题目成功落库。

## 错误码

- `UNAUTHORIZED`：未登录。
- `NOT_FOUND`：二级任务、课程、计划或资料不可访问。
- `STATE_CONFLICT`：任务层级或课程归属不一致，或任务类型不允许生成该内容。
- `NO_PARSED_MATERIAL`：二级任务没有关联资料，或关联资料没有可用解析上下文。
- `MATERIAL_COVERAGE_INCOMPLETE`：全材料覆盖未完成。
- `GENERATION_SCHEMA_INVALID`：模型输出结构、测试题硬约束或引用不符合契约。
- `GENERATION_FAILED`：模型调用或未知生成失败。
- `EXPORT_UNSUPPORTED_CONTENT_TYPE`：导出格式不支持当前生成内容类型。
- `EXPORT_CONTENT_NOT_READY`：生成内容尚未成功，不能导出。
- `EXPORT_CONTENT_INVALID`：历史生成内容结构畸形，不能安全导出。
- `EXPORT_FAILED`：PDF 渲染失败，不影响原 generated content。

## 复杂度与资源预算

材料读取按 `material_batch_max_tokens` 分批。时间复杂度约为 O(b + c)，其中 b 为材料批次数，c 为生成内容中的引用数量；引用保存按去重后的 chunk 数线性处理。

Handout 模型调用次数等于材料批次数。Task test 模型调用次数固定为 1，prompt 包含当前二级任务允许材料批次中的所有候选 chunk；因此它适合当前 POC 的二级任务范围，后续若要支持更大的测试范围，应先评审候选考点摘要、chunk 级范围追溯或后台任务机制。Task test 结构校验最多处理 20 道题，题干相似度比较为 O(q²)，q 上限由 `question_count <= 20` 控制。导出接口不调用模型、不写数据库；Markdown 渲染复杂度约为 O(q + c)，PDF 渲染复杂度约为 O(s + c + p)，其中 q 为题目数，s 为讲义 section 和文本行数，c 为引用数，p 为分页后的页数。

## 与执行页任务级问答的边界

轻量化 T3 新增的 `POST /api/v1/study-subtasks/{subtask_id}/qa/questions` 属于 S04 执行页问答能力，不属于 S06 任务内容生成。它复用 Course QA 的 `conversations`、`messages` 和 `source_citations`，资料范围同样来自当前二级任务的 `related_material_ids_json`，但不会创建或更新 `AIGeneratedContent`，也不参与 `handout_content_id` / `task_test_content_id` 的最近成功内容选择。

因此任务内容生成、Markdown/PDF 导出和执行页问答之间的边界是：生成与导出围绕 `ai_generated_contents`；任务级问答围绕对话消息。两者都不得修改二级任务完成状态，也不得写 `checkin_records`。

- 不持久化学生作答；浏览器内逐题提交状态可以丢失，作答记录和后端 attempt 已拆到后续任务。
- 不实现任务测试题 PDF 导出；轻量阶段任务测试题只提供 Markdown 导出，任务讲义支持 PDF 导出。
- 不新增 chunk 级任务范围持久化字段；当前只保证生成时引用来自当前二级任务相关资料的当次 material-context 批次。
- 自动化测试使用 `MockModelProvider` / 测试 provider，不调用真实模型。

## 2026-07-14 前端 C11 导出与最终硬化接入

`frontend/src/features/study-plans/api.ts` 新增文件流导出 adapter：

- `exportGeneratedContentPdf(generatedContentId)`：读取 `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf`，用于成功的 `handout`。
- `exportGeneratedContentMarkdown(generatedContentId)`：读取 `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown`，用于成功的 `task_test`。
- 文件流接口不使用统一 success envelope。前端 adapter 只在错误响应中解析统一 error envelope；成功时读取 `Blob` 和 `Content-Disposition` 文件名，并在浏览器端触发下载。
- `401` 仍清理登录态；`EXPORT_UNSUPPORTED_CONTENT_TYPE`、`EXPORT_CONTENT_NOT_READY`、`EXPORT_CONTENT_INVALID` 和 `EXPORT_FAILED` 在执行页展示可恢复错误，不修改生成内容状态，也不影响二级任务完成状态。

执行页 `frontend/src/pages/StudyTaskExecutionPage.tsx` 的导出规则：

- `learn` / `review` 当前内容类型是 `handout`，已有成功内容 ID 时显示“导出PDF”。
- `quiz` / `test` 当前内容类型是 `task_test`，已有成功内容 ID 时显示“导出Markdown”。
- 生成成功后使用返回的 `GeneratedContentRead.id` 立即启用对应导出入口；execution-context 返回已有 ID 时不自动重新生成。
- “重新生成”仍只调用 S06 生成接口，不自动触发导出。
- 学习计划详情页的“导出计划”继续保持 disabled，因为后端没有学习计划自身导出接口；前端不伪造 PDF/Markdown。

手测清单：

1. 打开 learn/review 二级任务执行页，若已有 `handout_content_id`，应看到“查看任务讲义”“导出PDF”“重新生成”。
2. 点击“导出PDF”，浏览器下载 `handout-{generated_content_id}.pdf`；失败时页面显示导出错误 alert，任务完成状态不变。
3. 打开 quiz/test 二级任务执行页，若已有 `task_test_content_id`，应看到“查看任务测试题”“导出Markdown”“重新生成”。
4. 点击“导出Markdown”，浏览器下载 `task-test-{generated_content_id}.md`；失败时页面显示导出错误 alert，任务完成状态不变。
5. 未生成内容的二级任务只显示生成按钮，不显示导出按钮。
6. 计划详情页顶部“导出计划（待接入）”保持禁用。

前端测试入口：

- `frontend/tests/features/study-plans/api.test.ts` 覆盖 PDF / Markdown 导出 adapter 路径。
- `frontend/tests/pages/study-plan-pages.test.tsx` 覆盖执行页已有内容时的导出按钮和文件流请求。
- `frontend/tests/features/generated-content/task-test-result.test.tsx` 覆盖 `task_test` 本地逐题作答、单选、多选、判断和简答提交反馈。
- `frontend/tests/features/generated-content/generated-content-renderer.test.tsx` 和 `frontend/tests/pages/generated-content-detail.test.tsx` 覆盖 `task_test` 生成内容详情页提交后反馈，不展示引用侧栏。

## 2026-07-13 引用、PDF 和默认参数修复补充

Handout prompt 要求行内公式只使用 `$...$`，块级公式只使用独立的 `$$...$$`，禁止 `\(...\)`、`\[...\]` 和单独一行 `[` / `]` 包公式，公式不要放进代码块，变量解释使用普通 Markdown 列表；自测题或填空题的空格线使用全角低线 `＿＿＿＿`，不要使用连续 ASCII 下划线 `______`，避免 Markdown 渲染吞掉填空线。后端生成阶段不做公式分隔符自动转换，PDF renderer 负责数学排版；前端执行页讲义预览已接入 GFM 表格和 KaTeX 数学渲染，生成内容详情页仍归同学 B 边界，不在本轮修改。

`ensure_handout_header()` 只负责清理最外层 `markdown` 代码围栏、校验正文非空、删除模型返回的首个一级标题，并写入统一的 `# {StudySubTask.title}讲义` 和来源说明。它保留模型正文原样，不正则改写代码块、普通方括号或数学公式内容。

Handout 仍只读取当前二级任务关联资料。若计划快照中存在当前 subtask 的 `citation_chunk_ids`，仅 handout 专用分支过滤 material-context batch；公共 material-context 查询保持当前用户、当前课程、未删除资料、`parse_status == "parsed"` 和 chunk 顺序等基础边界。

若当前二级任务上下文在 token 限制内，handout 应尽量一次 prompt 生成整篇 Markdown；若必须分 batch，reducer 必须通过模型合成为一整篇连贯最终稿，不把 batch Markdown 硬拼接作为最终讲义。

### PDF renderer 契约

Handout PDF 导出读取 `ai_generated_contents.content` Markdown，经 Markdown -> HTML -> KaTeX auto-render -> Playwright PDF renderer 输出文件流。renderer 可以处理标题、列表、表格、代码块和数学公式排版；代码块和 inline code 中的 `$...$` 由 KaTeX ignoredTags 忽略。导出层不创建数据库记录、不修正生成内容语义、不恢复历史结构化 handout。

### 本地 POC 数据重置

本 PR 不修改运行时幂等复用逻辑，也不提供旧结构化 handout 迁移或兼容导出；旧 `content_json.sections/blocks` handout 通过一次性本地 POC 数据重置处理。合并后所有开发者必须先确认没有需要保留的本地资料、学习计划和生成内容，再删除本地 SQLite 数据库 `backend/course_nexus.db`，并在 `backend/` 下重新运行数据库初始化：`uv run alembic upgrade head`。需要演示数据时，再运行更新后的 Markdown-first seed，例如 `uv run python -m app.commands.seed_generated_content_demo`。

这个口径只成立于当前阶段同时满足以下条件：只有本地 POC 数据；没有共享测试库、演示库或部署环境；所有开发者都能统一重置本地 SQLite。满足这些条件后，旧讲义被幂等命中并复用不再作为本 PR 的阻塞代码问题。

### task-test 默认参数

计划保存时会在 `parsed_config_json.task_snapshot[].subtasks[].generation_parameters.task_test` 保存 quiz/test 默认生成参数。模型或前端给出的 `{ "single_choice": 10, "short_answer": 3 }`、数组格式、`items` / `questions` / `types` / `question_types` / `question_type_counts` 内嵌 `{type,count}` 或 `{question_type,question_count}` 对象，以及 `{"10道选择题": "single_choice", "3道计算题": "short_answer"}` 这类题量文案映射，都会归一化为规范测试题参数；`task_test: "single_choice"` 搭配同级 `question_count` 这类模型 shorthand 会归一化为总题数 + 题型白名单。因此真实 E2E 可以传 `{ "force_regenerate": true, "parameters": {} }` 来验证计划中“10 道选择题和 3 道计算题”最终生成 13 题且分布为 10/3。

合并计划默认参数和本次请求时以计划默认值为底：本次请求显式传 per-type counts 时，用本次题数和分布完整覆盖 stored 题数与分布；本次请求只传 `difficulty` 时保留 stored 题数和分布；本次请求只传字符串数组形式的 `types` / `question_types`、没有传 per-type counts 时，保留 stored `question_count`，用请求题型替换 stored `question_types`，并清掉 stored `question_type_counts`，退回“原总题数 + 新题型白名单”契约。若计划没有 stored `question_count`，才使用 schema 默认的 5 道题；本次请求显式传 `question_count` 时，以请求题数覆盖 stored 总题数。

Task-test prompt 在 `question_type_counts` 存在时必须明确写出每种题型数量，例如 `single_choice 10 道，short_answer 3 道`；没有 `question_type_counts` 时只写总题数和题型白名单，不凭空平均分配。真正非法默认参数在保存/替换阶段返回 `VALIDATION_ERROR`；旧计划中若存在脏默认参数，运行 task-test 生成时返回 `GENERATION_SCHEMA_INVALID` 并保存 failed 记录。

### task-test 选择题选项字母契约

Task-test prompt 要求 `single_choice` / `multiple_choice` 恰好输出 4 个选项。模型可以临时输出 `opt_1`、`opt_5` 等局部或全局选项 id，但 generator 会在校验前按每道题自己的 options 顺序归一化为 `A`、`B`、`C`、`D`，并同步映射单选字符串答案和多选字符串数组答案。归一化后新生成的 `content_json.questions[].options[].id` 和 choice `correct_answer` 不应再出现 `opt_*`。若选择题不是 4 个选项，或答案无法命中该题原始 options id，生成返回 `GENERATION_SCHEMA_INVALID`。`short_answer` 和 `true_false` 不参与 A-D 归一化；Markdown 导出会对历史 `opt_*` 四选项内容按同样顺序做展示层兜底，避免用户继续看到 `opt_*`。

### 术语质量校验

物理层讲义生成后会扫描已知术语误拼，当前包括 `Nyquest -> Nyquist`、`Shanon -> Shannon`、`bandwith -> bandwidth`。命中明显错拼时返回 `GENERATION_SCHEMA_INVALID`，不静默落库，后续可扩展为课程领域 glossary。

## 2026-07-13 任务讲义前端展示与引用脱敏契约（历史）

本节原先描述结构化 handout 的 `content_json.sections` 展示和 section citation 绑定。该方案已被 2026-07-14 Markdown-first 方案取代：新生成 handout 的权威正文是 `GeneratedContentRead.content` Markdown，来源说明在正文顶部，前端详情页不展示引用侧栏。旧结构化 handout 不作为新数据兼容目标。

任务测试题 Markdown 导出以及 task-test 的内部引用追溯仍需隐藏不适合用户可见的 parser/OCR 残留；但该引用脱敏规则不要求新 handout 保存逐条 citation，生成内容详情页也不展示引用侧栏。

## 2026-07-14 Handout Markdown-first 简化

本节为新生成 `handout` 的当前权威口径；前文中关于 `HandoutContent` v2、section/block/formula_cards 级 `source_citation_ids`、引用侧栏和历史结构化 handout 导出的描述均视为历史方案，不再适用于新生成讲义。

新生成讲义的持久化口径：

- `ai_generated_contents.title` 使用当前二级任务标题派生，格式为 `{StudySubTask.title}讲义`，不再固定为“今日讲义”。
- `ai_generated_contents.content` 保存完整 Markdown 正文，正文顶部在一级标题后保留来源说明句，格式为 `本讲义基于《资料名1》《资料名2》中“二级任务标题”相关内容生成。`。
- 来源说明中的资料名来自本次 handout 实际使用的 material-context batch 资料名去重；知识点优先使用当前 `StudySubTask.title`。
- `ai_generated_contents.content_json` 只保存轻量格式元信息：`{"format":"markdown","schema_version":1}`。
- `ai_generated_contents.material_scope_json` 继续保存本次资料范围，用于说明讲义基于哪些资料生成。
- 新生成 handout 不写 `source_citations`，不做 section / block / formula card 级引用回绑，不兼容历史结构化 handout 导出。

生成流程仍只读取当前二级任务关联资料：`StudySubTask.related_material_ids_json -> MaterialScope(include_all_parsed_materials=false)`。若计划快照中存在当前 subtask 的 `citation_chunk_ids`，handout 专用分支会用该 chunk 范围过滤 material-context batch；公共 `material_context.repository.list_parsed_context_chunks_for_scope()` 只保留当前用户、当前课程、未删除资料、`parse_status == "parsed"` 和 chunk 顺序这些基础边界，不承载任务级 chunk 范围规则。

Handout 生成优先在当前二级任务上下文可放入 token 限制时一次 prompt 产出整篇 Markdown。若资料必须分 batch，单 batch 先产出局部草稿，reducer 再调用模型把多个草稿合成为一整篇上下连贯、去重后的最终 Markdown；不得把多个 batch Markdown 用分隔线硬拼为最终稿。

导出和前端展示口径：

- Markdown 导出：`GET /api/v1/generated-contents/{generated_content_id}/exports/markdown` 对成功 `handout` 直接返回 `content`。
- PDF 导出：`GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` 对成功 `handout` 读取 `content`，复用 Markdown -> HTML -> KaTeX auto-render -> Playwright PDF renderer。
- 前端 handout 详情页只渲染 `GeneratedContentRead.content` Markdown，不展示引用侧栏或逐条 citation 列表；来源说明已经在 Markdown 顶部。
- 导出不写数据库、不修改任务状态、不写打卡记录。

任务测试题 `task_test` 暂时仍保留结构化 JSON、逐题引用和 Markdown 导出逻辑，不随 handout Markdown-first 改造为 Markdown 直存；本轮只同步标题规则，`ai_generated_contents.title` 使用 `{StudySubTask.title}测试题`，不再固定为“任务测试题”。

## 2026-07-15 任务讲义前端预览渲染切片

前端新增隔离的讲义 Markdown 预览组件入口，先用于验证视觉方向和 Markdown callout 契约，不替换生产详情页渲染，也不改变 PDF 导出链路。

代码入口：

- 组件：`frontend/src/features/generated-content/renderers/handout/HandoutMarkdownRenderer.tsx`
- 样式：`frontend/src/features/generated-content/renderers/handout/handout-markdown.css`
- Mock 内容：`frontend/src/features/generated-content/renderers/handout/handoutMock.ts`
- 开发预览页：`frontend/src/pages/HandoutPreviewPage.tsx`
- 开发路由：`/dev/handout-preview`，仅 `import.meta.env.DEV` 下挂载。
- 测试：`frontend/tests/features/generated-content/handout-markdown-renderer.test.tsx`

第一版预览组件支持标题、段落、列表、Markdown 表格、`$$...$$` 块级公式展示，以及 GitHub alert 风格的 blockquote callout。当前没有新增前端依赖；公式先以讲义公式区文本形式预览，后续若接入 `remark-math` / `rehype-katex`，外部组件 API 仍保持 `HandoutMarkdownRenderer({ markdown })`。

Callout Markdown 约定：

```md
> [!NOTE] 注意
> 概念边界、重要提醒或补充说明。

> [!EXAMPLE] 例题 1
> 题目、应用场景或演算入口。

> [!SUMMARY] 核心结论
> 结论卡片或阶段小结。

> [!WARNING] 易错点
> 错误判断、限制条件或不要混淆的内容。

> [!TIP] 解题提示
> 步骤提示、记忆提示或计算提醒。
```

视觉约定沿用“雾霾蓝 × 鼠尾草绿”讲义方向：保留整片柔和背景色，不使用左侧强调线；callout 使用 14px 圆角和浅边框。普通 `>` 引用若不包含受支持的 `[!TYPE]` 标记，仍按普通引用块展示，不强行转为 callout。

本切片不要求后端 handout prompt 立即输出上述 callout 语法，也不要求后端 PDF renderer 立即适配；若后续将该契约用于真实生成内容，必须同步更新 handout prompt、PDF renderer 和相关测试。
## 2026-07-14 测试任务范围来自计划阶段

每日唯一测试规则属于 Study Plan 层。任务内容生成层不重新计算“今天学了什么”或“全计划学了什么”，只消费当前二级任务已经保存的范围。

- `learn` / `review` 仍然只能生成 `handout`。
- `quiz` / `test` 仍然只能生成 `task_test`。
- 非最后一天测试的 `related_material_ids_json` / `citation_chunk_ids` 在计划阶段已覆盖当天前置学习任务。
- 最后一天综合测试的 `related_material_ids_json` / `citation_chunk_ids` 在计划阶段已覆盖全计划所有非测试任务。
- `task_test` 生成继续读取当前测试二级任务的 `related_material_ids_json` 和默认 `generation_parameters.task_test`；请求只提供字符串数组形式的 `types` / `question_types` 时保留计划默认总题数，只替换题型白名单并清除旧的精确题型分布；请求通过 `questions`、`items`、`question_type_counts` 或中文题量映射显式提供每种题型数量时，用请求题数和分布完整覆盖计划默认值；只覆盖 `difficulty` 时保留计划默认题数与分布。

这保证了测试题生成链路仍按原有二级任务范围运行，同时让“当天测试 / 全计划综合测试”的语义在计划数据里可追溯。


## 2026-07-15 任务测试题逐题交互

前端将 `task_test` 从只读答案展示升级为浏览器内存内的逐题交互。执行页和生成内容详情页共用 `frontend/src/features/generated-content/renderers/TaskTestResult.tsx`，并通过 `frontend/src/features/generated-content/guards.ts` 校验 `GeneratedContentRead.content_json.questions`。本功能不新增后端接口、attempt 记录、错题本或打卡副作用。

交互规则：

- `single_choice` 显示“单选”标签，用户选择一个选项后提交，提交后本地判断正确 / 错误，并显示正确答案和解析。
- `multiple_choice` 显示“多选”标签，用户可勾选多个选项，提交后按选项集合完全一致判断正确 / 错误，并显示正确答案和解析。
- `true_false` 显示“判断”标签，用户选择“正确 / 错误”，提交后本地判断并显示正确答案和解析。
- `short_answer` 显示“简答”标签和文本框，提交后不自动判分，只显示参考答案和解析。
- 每道题独立提交；未提交题目不显示正确答案或解析。刷新页面后本地作答状态可以丢失。
- 前端 `TaskTestResult` 通过调用方传入的 `attemptKey` 隔离浏览器内作答状态；生成内容详情页使用 `GeneratedContent.id`，执行页优先使用当前 `GeneratedContentRead.id`。当重新生成的新内容复用同一题目 `id` 时，旧 answers / submitted 状态不得继承。

验证入口：

- `pnpm --dir frontend exec vitest --run tests/features/generated-content/task-test-result.test.tsx --maxWorkers=1`
- `pnpm --dir frontend exec vitest --run tests/features/generated-content/generated-content-renderer.test.tsx tests/pages/generated-content-detail.test.tsx --maxWorkers=1`
- `pnpm --dir frontend exec vitest --run tests/pages/study-plan-pages.test.tsx --maxWorkers=1`
## 2026-07-15 任务讲义正式 Markdown 渲染契约

本节更新 2026-07-15 预览切片后的当前权威口径：讲义详情页、后端生成 prompt 和 PDF 导出均使用同一套 Markdown-first / callout 契约。前文仍提到“今日讲义”、结构化 handout 或仅预览的描述时，以本节为准。

代码入口：

- 前端讲义 renderer：`frontend/src/features/generated-content/renderers/handout/HandoutMarkdownRenderer.tsx`
- 前端 callout AST 转换：`frontend/src/features/generated-content/renderers/handout/remarkHandoutCallouts.ts`
- 前端讲义样式：`frontend/src/features/generated-content/renderers/handout/handout-markdown.css`
- 生成内容详情分发：`frontend/src/features/generated-content/GeneratedContentRenderer.tsx`
- 开发预览页：`frontend/src/pages/HandoutPreviewPage.tsx`，仅 DEV 路由 `/dev/handout-preview`
- 后端 handout prompt：`backend/app/modules/generation/generators/handout/generator.py`
- PDF renderer：`backend/app/modules/exports/renderer.py`

前端正式依赖 `react-markdown + remark-gfm + remark-math + rehype-katex + rehype-raw + rehype-sanitize + mermaid` 渲染 handout Markdown。`handout` 详情页不再使用通用 `ReactMarkdown` 分支，而是复用 `HandoutMarkdownRenderer({ markdown })`，因此 dev preview 和真实详情页共享公式、表格、列表、callout、原始 SVG 和 Mermaid 行为。KaTeX CSS 由 renderer 引入；长公式和图表允许横向滚动，避免正文布局被撑坏。

图形渲染契约：

- 原始 `<svg>...</svg>` 由 `rehype-raw` 解析，再由 `rehype-sanitize` 的 SVG 白名单净化后转入 React 渲染树；Markdown 图片语法引用的 SVG 文件继续按普通 `<img>` 展示。
- ```mermaid` fenced code block 由 `HandoutPre` 分流给 `MermaidDiagram`，后者动态导入 Mermaid 并把源码异步渲染为内联 SVG。
- Mermaid 初始化参数为 `startOnLoad: false`、`securityLevel: "strict"`、根级 `htmlLabels: false`；最终 SVG 在注入前再次净化。渲染期间显示稳定占位，失败后显示原始代码，不影响正文其余内容。
- 非 Mermaid fenced code block 仍输出普通 `<pre><code>`，不会参与图表解析。
- 原始 SVG、SVG 图片和 Mermaid 生成 SVG 均受讲义容器的响应式宽度约束。
- 安全边界明确禁止 `script`、`iframe`、`object`、`embed`、`foreignObject`、`style`、事件属性和危险 URL scheme；扩展 SVG 白名单时必须同步补安全测试。前端 Mermaid 能力不改变后端 PDF renderer，PDF 中的 Mermaid 支持需要单独实现。
- 测试入口：`frontend/tests/features/generated-content/handout-markdown-renderer.test.tsx`，覆盖 Mermaid 成功、失败、原生 SVG 文本标签、原始 SVG、恶意 HTML/SVG 和普通代码块回归。

前端把完整讲义交给单个 `ReactMarkdown` 实例解析，不在渲染前按行切割 Markdown。`remarkHandoutCallouts` 只在 Markdown AST 中把首段以受支持 `[!TYPE]` 开头的 blockquote 转换为带类型 class 的 callout；代码围栏中的同形文本仍是 code 节点，不参与转换。三级标题若以 `1.1` 这类编号开头，只单独包装首个文本节点中的编号，其余加粗、链接、行内代码和 KaTeX React 节点保持原结构，禁止把已经渲染的 children 转回纯文本。

Handout prompt 必须只输出 Markdown，不输出 HTML callout。重要教学块使用 GitHub alert 风格 blockquote，支持类型固定为：

| Markdown 类型 | 中文标题 | 用途 | 颜色 |
| --- | --- | --- | --- |
| `[!NOTE]` | 注意 / 补充说明 | 概念边界、重要提醒 | 暖米色 `#fbf7f3`，标题 `#8c725e` |
| `[!EXAMPLE]` | 例题 / 例题 1 | 题目、应用场景、演算入口 | 鼠尾草绿 `#f6f9f5`，标题 `#667c69` |
| `[!SUMMARY]` | 核心结论 / 总结 | 结论卡片、阶段小结 | 淡紫灰 `#f8f6fb`，标题 `#706982` |
| `[!WARNING]` | 易错点 / 常见误区 | 错误判断、限制条件、不要混淆 | 暖米色加深 `#fbf3ee`，标题 `#9b6048` |
| `[!TIP]` | 解题提示 / 记忆提示 | 步骤提示、记忆口诀、计算提醒 | 雾霾蓝 `#f3f7fa`，标题 `#597089` |

Markdown 约束：

```md
> [!NOTE] 注意
> 正文每一行都继续以 > 开头。

> [!EXAMPLE] 例题 1
> 已知带宽 $B = 3$ kHz，求最大传输速率。
```

普通解释仍使用段落、列表、表格和标题；不要把整篇正文都写成 callout。普通 `>` 引用如果不包含上述 `[!TYPE]` 标记，仍按普通引用展示。

视觉约束：callout 保留整片柔和背景色，去掉左侧强调线，使用圆角；前端为 14px 圆角并带浅边框，PDF 为 8px 圆角以适配打印密度。颜色和标题色与上表保持一致。

PDF 导出同步支持相同 callout 契约。`render_markdown_pdf_html()` 会在 Markdown-it 生成 HTML 后，把首段为 `[!NOTE]` / `[!EXAMPLE]` / `[!SUMMARY]` / `[!WARNING]` / `[!TIP]` 的 blockquote 转换为 `.pdf-callout` 容器；其他 blockquote 不转换。PDF CSS 不使用 callout 左侧强调线，并保留 KaTeX 对 `$...$` / `$$...$$` 的公式排版。

验证入口：

- `pnpm --dir frontend test -- --run tests/features/generated-content/handout-markdown-renderer.test.tsx`
- `pnpm --dir frontend test -- --run tests/features/generated-content/generated-content-renderer.test.tsx`
- `pnpm --dir frontend test -- --run tests/pages/generated-content-detail.test.tsx`
- `pnpm frontend:build`
- `uv run pytest tests/modules/generation/test_handout_generator.py`
- `uv run pytest tests/modules/exports/test_exports_api.py -q`

## 2026-07-15 任务讲义图示生成契约

新生成的 `handout` 仍采用 Markdown-first 存储，但生成器现在要求每份成功讲义至少包含一张可视化图示，用于降低理解性内容的阅读负担。

后端生成规则：

- `backend/app/modules/generation/generators/handout/generator.py` 的 handout prompt 明确要求每份讲义至少包含 one safe inline SVG visual diagram。
- 新生成讲义禁止输出 Mermaid fenced code block、`graph` / `flowchart` / `sequenceDiagram` / `mindmap` 等 Mermaid 语法；prompt 和保存前校验都会拦截。
- 概念层级、知识结构、章节关系、流程、步骤、状态变化、系统链路、物理过程、网络拓扑、编码过程、信号波形和空间布局等图示均使用安全内联 SVG 表达。
- SVG 只允许表达性元素和属性；prompt 禁止 `script`、`iframe`、`object`、`embed`、`foreignObject`、`style`、`onload`、`onclick`、`onerror`、`javascript:`、`data:`、外部图片、外部字体和外链资源。
- 后端保存前使用 `_handout_has_visual()` 检查正文是否包含 `<svg>...</svg>`，并使用 `_assert_no_mermaid()` 拒绝 Mermaid code block。第一次模型输出缺 SVG 时，后端追加 retry feedback 最多重试一次；第二次仍缺图则返回 `GENERATION_SCHEMA_INVALID`，不保存成功讲义。
- 多批次讲义合成 prompt 同样要求最终稿保留或重画至少一张安全内联 SVG，并禁止 Mermaid，避免 reducer 阶段重新引入 Mermaid。
- 历史结构化 `MermaidBlock.diagram_type` 仍兼容 `mindmap`，但不再作为新生成 handout 的输出目标。

当前前端讲义 renderer 仍保留 Mermaid 渲染能力，用于历史或手写 Markdown 兜底；新生成讲义的图示契约只依赖安全内联 SVG。PDF 中 Mermaid 的完整渲染仍属于独立能力，当前契约主要保证 Web 讲义详情页的新内容可视化展示。

验证入口：`backend/tests/modules/generation/test_handout_generator.py` 覆盖 prompt 约束、SVG 通过、Mermaid 拒绝、缺图重试和 `MermaidBlock` schema 兼容。

## 2026-08-25 任务之间并发生成（阶段一）

执行页允许不同二级任务同时发起讲义或测试题生成。前端在 `StudyTaskExecutionPage.tsx` 中按 `subtask_id` 记录生成状态和错误，并使用任务级 in-flight 集合防止同一个二级任务重复点击；生成结果继续写入 `generatedContentBySubtask`，因此请求完成顺序不影响任务归属。

本阶段不修改后端接口、数据库或生成服务。后端仍使用同步 HTTP 生成接口，但不同请求可并行执行；页面刷新、关闭页面后的任务恢复、持久化 job 状态、后端队列、重试和统一并发限流不属于本阶段，后续如需可靠后台任务应单独设计异步 job 方案。
