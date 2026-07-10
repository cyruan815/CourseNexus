# F05 课程 Agent 问答

## 0. 业务功能说明

- **业务场景**：学生在学习某门课程时，希望针对当前选择的课件或笔记提问，并追溯回答来自哪份资料。
- **用户能力**：选择资料范围、发送问题、查看带引用的回答、继续追问、切换和回看课程内会话。
- **业务结果**：回答尽量基于课程资料并展示资料名、页码或页序号和命中文本；没有资料依据时明确显示无来源状态。
- **业务边界**：历史消息引用查询、点击引用打开原文和保存回答为笔记尚无完整后端接口，本任务只提供明确占位，不伪造历史引用或笔记保存成功。

## 1. 任务信息
- 编号：`F05`；负责人：前端开发者。
- 目标：中栏支持会话列表、历史消息、首次提问、连续追问、回答类型和当前回答引用。
- 前置：F01-F04；course-qa 三个现有接口；共享 MaterialScope。
- 当前基线：问答 slot 空；后端已保存会话/消息/引用。
- 范围外：任务执行问答、流式输出、会话删除/改名、保存笔记、资料预览定位。

## 2. 实现范围
1. 先写 QA API、会话切换、提问、引用和占位失败测试。
2. 加载课程会话列表；空态可新建对话，点击会话加载消息。
3. 首问传 `conversation_id:null`；响应后保存 ID 并刷新会话；追问复用同课程 ID。
4. 每次提交读取 F03 当前 scope；显式空范围或问题空白时禁用。
5. 发送中只显示本地 pending 项；成功用真实消息 IDs 对齐，失败不伪造已保存消息并保留输入重试。
6. 展示 grounded/no_source/partial_grounded 与未知兜底；no_source 不渲染伪引用。
7. 当前提问响应中的 citations 展示资料名、page/page_index、hit_text；缺页显示页码未知。
8. 历史消息接口不返回 citations，刷新后只展示消息正文；明确显示“历史引用暂不可用”而非伪造。
9. 保存为笔记和引用预览均为后端未实现仅占位：按钮 disabled、零请求。
10. 会话/消息/发送错误局部隔离；401 交 F01，NOT_FOUND 刷新会话并阻止跨课程复用。

### 精确文件边界
- 创建：`features/course-qa/{api,types,CourseQaWorkspace,ConversationList,MessageList,QuestionComposer,CitationList,qaErrors}.ts(x)`。
- 修改：`features/course-workspace/CourseWorkspaceSlots.tsx`，只替换中栏 slot；相关 CSS。
- 测试：`tests/features/course-qa/{api,course-qa-workspace,question-composer,citation-list}.test.ts(x)`。
- 修改：`tests/pages/course-detail.test.tsx`；创建 `tests/manual/F05-course-qa.md`。
- 禁止：后端、MaterialScope、生成内容写 API、预览假数据。

## 3. 字段与接口
### 当前已实现 API
- `GET /api/v1/courses/{course_id}/conversations` -> `ConversationRead[]`。
- `GET /api/v1/conversations/{conversation_id}/messages` -> `MessageRead[]`。
- `POST /api/v1/courses/{course_id}/qa/questions`：`conversation_id,question,material_scope,source_page:"course_detail"` -> `QaAnswer`。
- Conversation：`id,user_id,course_id,title,source_page,status,created_at,updated_at,deleted_at`。
- Message：`id,conversation_id,course_id,role,content,answer_type,generation_status,error_code,material_scope_json,created_at`。
- QaAnswer：`conversation_id,user_message_id,assistant_message_id,answer_text,answer_type,source_citations`。
- Citation：`material_id,chunk_id,material_name,page,page_index,hit_text`。
### 本任务新增前端接口
- `listConversations,listMessages,askCourseQuestion`；类型容忍未知 role/status/answer_type。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；没有保存 note endpoint、历史消息引用字段/查询、资料预览/定位 endpoint。

## 4. 测试计划
- `api.test.ts`：三路径、首问 null、追问 ID、source_page、scope 精确 body。
- `course-qa-workspace.test.tsx`：会话/消息四态、切换、首问建会话、追问复用、NOT_FOUND、401。
- `question-composer.test.tsx`：空问题/显式空 scope disabled、发送防重、失败保留输入、scope 每次取当前值。
- `citation-list.test.tsx`：page 优先/page_index/未知页、空引用、no_source、未知 answer_type、禁用预览零请求。
- 历史消息测试：不造 citations；保存笔记按钮 disabled 且零请求。
- 命令：`pnpm --dir frontend test -- --run tests/features/course-qa tests/features/material-scope tests/pages/course-detail.test.tsx`。
- 预期：退出码 0、无 live network；全量测试和 build 成功。

## 5. 验收标准
### 自动化
- [ ] 首问/追问、会话切换、当前引用、无来源、失败重试均有行为测试。
- [ ] scope 无同义字段；no_source/历史消息不造引用；未知枚举兜底。
### 人工
- [ ] parsed 资料全选提问得到会话和真实引用；追问复用会话。
- [ ] 显式空范围不能发送；无命中明确 no_source。
- [ ] 刷新历史正文可见但引用标明不可用；保存笔记/预览 disabled。
- [ ] 1440/390 下长回答、hit_text、输入和按钮不重叠。

## 6. 交付物
- QA API/types、会话/消息/输入/引用组件、错误映射、测试和 F05 人工记录。
- 建议按 API/会话、提问/引用、占位/测试小提交。

## 7. 文档同步
- 新建或更新 `docs/domains/course-qa/frontend.md`，记录会话、提问、追问和引用组件边界，loading/grounded/partial/no_source/error 状态，API 数据流、防御性渲染、降级路径和测试入口。
- 更新 frontend-integration：三接口、当前引用与历史引用缺口、note/preview 未接。
- 更新 current-state；不修改 PRD 的长期 note/预览目标。

## 8. 冲突与注意事项
- 依赖后端补历史 citations 和 note 写接口；F06 不能把通用 generation 伪装成 note。
- 严格遵循：retrieve 语义由后端；引用必须真实 material_id；跨课程会话 NOT_FOUND。
- 一定不能做：缓存伪装持久历史；猜 note/preview API；no_source 配引用；直接调用模型。

## 9. 完成检查表
- [ ] 范围、测试、回归/build、双视口验收、docs/diff/所有权完成。
- [ ] 仅接注册 API，未造引用/note 成功；小功能独立提交。
