# F06 AI 生成内容工作区

## 1. 任务信息
- 编号：`F06`；负责人：前端开发者。
- 目标：右栏接入五类统一生成入口、历史、详情和防御性结构化渲染。
- 前置：F01-F04/F03 scope；generation 与 generated-content 三个现有接口。
- 当前基线：后端五类 generator 已注册但当前为 deterministic placeholder；前端无 UI。
- 范围外：真实生成质量、保存笔记、删除、PDF、掌握度持久化、异步轮询。

## 2. 实现范围
1. 先写生成 API、入口、历史、详情、五渲染器和未知结构测试。
2. 工具入口固定 `quiz,flashcard,mindmap,outline,knowledge_list`；显式空 scope 禁用。
3. POST 同步返回 `GeneratedContentRead`；请求中仅当前 scope、type、该类型 parameters；防重。
4. 成功将真实记录插入/刷新列表并打开详情；failed 响应展示 error_code 与“重新生成”（新 POST）。
5. 历史 list 四态；点击按 id GET 详情，不依赖列表对象完整。
6. 详情按 content_type 分发；解析预期 `questions/cards/nodes+edges/sections/items`，缺失时展示安全 JSON/正文兜底，不崩溃。
7. 当前 placeholder 结构不当作最终协议；渲染器容忍缺失可选字段、未知枚举/节点引用。
8. list/detail 当前不返回 citation 列表；只显示引用暂不可用，不伪造或从 `source_citation_ids` 反推正文。
9. 删除、PDF、Flashcard 掌握持久化为后端未实现仅占位：disabled、零请求。
10. 单个详情/生成失败不影响资料和问答栏；401 交 F01。

### 精确文件边界
- 创建：`features/generated-content/{api,types,GenerationTools,GeneratedContentHistory,GeneratedContentDetail,contentAdapters,generationErrors}.ts(x)`。
- 创建渲染：`renderers/{Quiz,Flashcard,Mindmap,Outline,KnowledgeList}View.tsx`、`UnknownContentView.tsx`。
- 修改：`features/course-workspace/CourseWorkspaceSlots.tsx` 右栏工具/历史 slot；相关 CSS。
- 测试：`tests/features/generated-content/{api,generation-tools,history,detail,renderers}.test.ts(x)`。
- 修改 course detail test；创建 `tests/manual/F06-generated-content.md`。
- 禁止：修改 generator/后端；引入图形库；写任务/计划状态。

## 3. 字段与接口
### 当前已实现 API
- `GET /api/v1/courses/{course_id}/generated-contents` -> `GeneratedContentRead[]`。
- `GET /api/v1/generated-contents/{generated_content_id}` -> `GeneratedContentRead`。
- `POST /api/v1/courses/{course_id}/generations`：`content_type,material_scope,parameters` -> `GeneratedContentRead`。
- GeneratedContent：`id,user_id,course_id,study_subtask_id,source_message_id,content_type,title,content,content_json,generation_status,material_scope_json,error_code,created_at,updated_at,deleted_at`。
- 状态：`pending,generating,success,failed`；类型为五类注册值，未知值兜底。
- 主要错误：`VALIDATION_ERROR,NO_PARSED_MATERIAL,GENERATION_FAILED`。
### 本任务新增前端接口
- `listGeneratedContents,fetchGeneratedContent,generateContent`；`content_json` 先按 `unknown` 接收，经 adapter 校验。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；无 delete/retry-by-id/citation list/PDF/mastery endpoint；“重试”是新 generation 请求。

## 4. 测试计划
- `api.test.ts`：三路径、body、scope、parameters、拆包。
- `generation-tools.test.tsx`：五类型、空 scope/无 parsed 禁用、防重、success/failed/NO_PARSED_MATERIAL。
- `history.test.tsx`：四态、排序、未知 status/type、点击 GET detail、401。
- `detail.test.tsx`：五分发、正文/JSON 兜底、缺字段、未知 type、failed record。
- `renderers.test.tsx`：题目/卡片/图节点边/章节/items 的交互与畸形 JSON 不崩溃。
- 占位测试：citation/delete/PDF/mastery disabled 且零请求。
- 命令：`pnpm --dir frontend test -- --run tests/features/generated-content tests/features/material-scope tests/pages/course-detail.test.tsx`。
- 预期：退出码 0、无 live network；全量测试/build 成功。

## 5. 验收标准
### 自动化
- [ ] 五类入口、历史/详情、成功/失败/空/未知均有行为测试。
- [ ] content_json 未校验前不直接索引；畸形结构不白屏；占位零请求。
### 人工
- [ ] 用 parsed scope 逐类生成，真实记录进入历史并可重开详情。
- [ ] failed 记录保留错误；重新生成产生新真实记录。
- [ ] placeholder 和未知 JSON 可读但不被标成最终高质量内容。
- [ ] 1440/390 下工具、历史、卡片/题目/长 JSON 不重叠。

## 6. 交付物
- 三 API、工具/历史/详情、五 renderer、adapter、错误映射、测试和 F06 人工记录。
- 建议按入口、历史详情、渲染器、测试小提交。

## 7. 文档同步
- 更新 frontend-integration：五类型、placeholder 状态、content_json 防御策略、缺失 API。
- 生成团队稳定结构后同步 contracts/table-schema；前端不得单方面改契约；更新 current-state。

## 8. 冲突与注意事项
- 跨团队依赖 G01-G06 稳定五类 schema/引用读取；现阶段 placeholder 不可写死为最终格式。
- 严格遵循：全材料覆盖由后端；统一 AIGeneratedContent；scope 硬过滤；失败记录不假成功。
- 一定不能做：直调 OpenAI；猜 delete/PDF/citation API；新建前端同义类型；生成器互调假象。

## 9. 完成检查表
- [ ] 范围、测试、回归/build、双视口验收、docs/diff/所有权完成。
- [ ] 仅接注册 API，未知结构安全；小功能独立提交。
