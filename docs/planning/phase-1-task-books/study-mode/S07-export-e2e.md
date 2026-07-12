# S07 PDF 导出与子系统端到端验收

## 0. 业务功能说明

- **业务场景**：学生希望把已经生成的今日讲义或任务测试题保存为便于离线查看、打印或复习的 PDF。
- **用户能力**：从成功的讲义或任务测试题详情发起 PDF 导出，并在导出失败时继续正常查看页面内容和重试。
- **业务结果**：计划学习模式形成“制定计划 -> 日历查看 -> 执行任务 -> 生成内容 -> 完成打卡 -> 导出”的完整可验证闭环。
- **业务边界**：本任务只导出已成功生成的讲义和任务测试题，不重新生成正文、不保存导出历史，也不扩展到五类课程生成内容。

## 1. 任务信息
- 编号与名称：`S07` PDF 导出与子系统端到端验收。
- 负责人角色：计划学习模式后端开发者。
- 目标：把成功的讲义/任务测试题安全渲染为 PDF，并验证计划学习模式从生成计划到导出和打卡的完整闭环。
- 前置依赖：S02-S06 全部合并；G01 公共生成协议稳定；S01 无 migration 结论保持有效。
- 范围外：不导出其他 content_type、不保存导出历史、不做异步队列、不实现前端下载 UI。

## 2. 实现范围
### 2.1 PDF 适配层
- 定义项目内部 `PdfRenderer` Protocol，输入经过 Pydantic 校验的标题、内容和引用，输出 `bytes`。
- 使用 `reportlab>=4.2,<5` 实现 `ReportLabPdfRenderer`；这是新增核心运行依赖，必须新增 ADR 并更新依赖文档。
- 中文使用 ReportLab CID 字体 `STSong-Light`；标题、正文、选项、答案、解析和引用支持自动分页。
- handout 按 overview/objectives/sections/summary 渲染；task_test 按 instructions/questions/answer/explanation 渲染。
- 引用页统一展示 `material_name`、`page` 或 `page_index`、`hit_text`，不输出本地文件路径、用户 ID 或原始完整材料。
- renderer 不访问数据库、HTTP、文件系统或业务 service。

### 2.2 导出 service
- 仅允许 `content_type=handout|task_test` 且 `generation_status=success`、未软删除、属于当前用户的内容。
- `content_json` 必须通过 S06 对应 schema 二次校验；无效返回 `GENERATION_SCHEMA_INVALID`，不渲染部分 PDF。
- 查询关联 `SourceCitation`，按 `sort_order` 稳定排列；无引用允许导出，但 PDF 标注“本内容无可用引用”，不能生成伪来源。
- 成功直接流式返回 bytes，不创建 `export_records`，不在本地留下临时文件。
- 文件名使用清洗后的标题和 `.pdf`；header 同时提供 ASCII fallback 与 RFC 5987 `filename*`。
- 渲染异常记录 request ID/content ID/error code，返回 `PDF_EXPORT_FAILED`；不改变生成内容和任务状态。

### 2.3 精确文件边界
创建：
- `backend/app/integrations/pdf/__init__.py`
- `backend/app/integrations/pdf/base.py`
- `backend/app/integrations/pdf/reportlab_renderer.py`
- `backend/app/modules/exports/schemas.py`
- `backend/app/modules/exports/service.py`
- `backend/app/modules/exports/router.py`
- `backend/tests/integrations/test_reportlab_pdf_renderer.py`
- `backend/tests/modules/exports/test_exports_service.py`
- `backend/tests/modules/exports/test_exports_api.py`
- `backend/tests/e2e/test_study_mode_closed_loop.py`

修改：`backend/app/modules/exports/__init__.py`、`backend/app/api/router.py`、`backend/pyproject.toml`、`backend/environment.yml`（仅依赖同步需要时）、ADR index。

禁止修改：migration、数据库 models、五类生成器、S06 内容语义、前端。

## 3. 字段与接口
### 3.1 migration 判断
- 不新增表、列、索引或 migration。PDF 为请求派生文件，不持久化导出记录。

### 3.2 当前 API
- 当前 generated-content detail 可读取内容；`exports` 仅空模块，无导出 API。

### 3.3 新增 API
`GET /api/v1/generated-contents/{generated_content_id}/exports/pdf`

成功响应不是 JSON envelope，而是二进制流：
- HTTP 200
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="content.pdf"; filename*=UTF-8''...`
- `X-Request-ID: req_...`
- body 以 `%PDF-` 开头且非空。

该二进制成功响应是 API convention 的明确例外；错误仍使用统一 JSON envelope。

错误：401 `UNAUTHORIZED`；404 `NOT_FOUND`；409 `STATE_CONFLICT`（失败、生成中或不支持类型）；500 `GENERATION_SCHEMA_INVALID`、`PDF_EXPORT_FAILED`。

前端必须等该例外契约和响应 header 合并后再接；不得把 JSON client 的自动拆包逻辑用于 PDF body。

## 4. 测试计划
### 4.1 renderer 与 service
`test_reportlab_pdf_renderer.py`：中文标题、长段落分页、四类题型、答案解析、引用、无引用、特殊字符；用 `pypdf` 读取页数与提取文本，断言 `%PDF-`。

`test_exports_service.py`：两类成功、跨用户、软删除、pending/generating/failed、不支持类型、schema 损坏、renderer 异常；断言失败不修改数据库。

`test_exports_api.py`：200 headers/body、401/404/409/500 JSON envelope、中文文件名编码、重复导出结果可用。

### 4.2 全闭环 E2E
`test_study_mode_closed_loop.py` 使用 SQLite 临时库、Fake RagIndex、Fake ModelProvider、真实 ReportLab，依次：
1. 注册并创建两门课程，上传解析多份材料。
2. 自然语言回填、全材料预览、调整并保存两个单课程计划。
3. 查询今日待办、全局月历/当日分组和课程日历。
4. 加载执行上下文，完成/取消/再完成二级任务，核对一级任务、计划和打卡。
5. 为 learn 任务生成 handout，为 test 任务生成 task_test；核对统一存储和引用。
6. 导出两个 PDF，断言可解析、内容类型正确。
7. 以第二用户访问计划、任务、内容和 PDF，全部拒绝。
8. 删除计划后聚合与执行隐藏，历史数据库记录未物理删除。

### 4.3 命令与预期
```powershell
cd backend
conda run -n course-nexus python -m pytest tests/integrations/test_reportlab_pdf_renderer.py -q
conda run -n course-nexus python -m pytest tests/modules/exports -q
conda run -n course-nexus python -m pytest tests/e2e/test_study_mode_closed_loop.py -q
cd ..
pnpm backend:test
```
预期：全部退出码 0；PDF 可由 pypdf 打开且至少一页；E2E 无 live OpenAI；完整后端回归通过。

## 5. 验收标准
### 自动化
- [ ] 两类 PDF 结构、中文、分页、引用和 header 测试通过。
- [ ] 权限、状态、schema、renderer 失败均返回稳定错误码。
- [ ] 全闭环 E2E 覆盖两课程、两用户和删除降级。
- [ ] 导出失败不修改内容、任务或打卡。

### 人工
- [ ] 使用真实中文讲义和 5 题测试导出 PDF，浏览器可打开，文字不乱码、不截断。
- [ ] 长内容跨页后标题、题号、答案与引用顺序正确。
- [ ] 生成失败时内容页仍可查看，导出可重试。
- [ ] 从计划生成到打卡和两个 PDF 的完整演示成功，并记录 request ID。

## 6. 交付物
- PDF integration、exports module、依赖与四组测试。
- ADR `docs/architecture/adr/0004-reportlab-pdf-export.md` 及 index 更新。
- API/架构/工程/当前状态/技术债文档。
- `docs/domains/study-mode/validation/S07-study-mode-e2e.md` 中文闭环记录。
- 建议提交：`build(pdf): 引入 ReportLab 导出依赖`；`feat(exports): 支持任务内容 PDF 导出`；`test(study-mode): 覆盖计划学习完整闭环`。

## 7. 文档同步
- 新建或更新 `docs/domains/study-mode/exports.md`：记录导出模块分层和代码入口、授权查询到 HTML/模板再到 PDF 响应的数据流、渲染与分页算法、时间/空间复杂度、字体/图片/临时资源管理、时间和内存预算、输入安全、失败清理与降级策略、端到端测试证据及已知限制。
- 更新 `docs/architecture/runtime-flows.md`、ADR index 与新 ADR。
- 更新 `docs/api-data/contracts.md`、`api-conventions.md`：二进制例外、headers、错误码。
- 更新 `docs/engineering/development-conventions.md`：PDF 测试命令和依赖。
- 更新 `docs/planning/current-state.md`、`tech-debt-tracker.md`；不改 PRD 原意。
- 不直接修改 `frontend-integration.md`，由前端负责人接收二进制契约。

## 8. 冲突与注意事项
### 严格遵循
- PDF 只消费成功的持久化内容和引用，不调用生成器。
- renderer 隔离于业务和数据库；测试使用真实 renderer。
- 新核心依赖必须有 ADR，自动化不得访问 live network。

### 一定不能做
- 不能新增导出表、保存临时 PDF、导出五类其他内容或泄露本地路径。
- 不能把失败内容当成功导出、吞掉 schema 错误或返回空 PDF。
- 不能修改五类生成器、前端、migration 或任务状态。

## 9. 完成检查表
- [ ] 实现、依赖 ADR、测试、E2E、人工验收和 docs 全部完成。
- [ ] PDF 二进制契约与 JSON 错误 envelope 均验证。
- [ ] `pnpm backend:test`、`git diff --check` 通过。
- [ ] 未越权修改且每个小功能独立提交。
