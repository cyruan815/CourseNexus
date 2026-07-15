# Materials 资料领域实现

## 1. 业务定位

`materials` 负责把用户资料绑定到课程，完成上传、重命名、一级文件夹归类、解析、切片、索引和删除，并向 Agent 消费者提供可追溯的逐文件资料范围。

一级文件夹只帮助用户整理和浏览资料，不代表 Agent 上下文。用户可以使用课程全部已解析资料，或选择一个、多个具体资料；不能选择整个文件夹。

当前非目标包括嵌套目录、非 PDF 资料正文预览、下载、后台解析队列和链接内容抓取。

## 2. 所有权与代码地图

- 后端入口：`backend/app/modules/materials/{router,schemas,service,repository,models}.py`。
- 历史引用脱钩边界：`backend/app/modules/course_qa/citations.py`，只允许资料删除流程清空引用外键，不删除问答或生成内容。
- 解析和索引：`backend/app/integrations/parsers/`、`backend/app/integrations/rag/`。
- 资料范围：`backend/app/modules/material_context/`。
- 基础前端：`frontend/src/features/materials/`，由第一阶段前端负责人继续完善。`MaterialWorkspace` 支持课程详情页传入创建后上传提示开关，用于课程创建成功后引导用户上传资料；当前提供资源管理器式资料区，并支持点击 PDF 资料名称在页面悬浮弹窗中预览原文。
- 后端测试：`backend/tests/modules/materials/`、`backend/tests/modules/material_context/`、`backend/tests/integrations/test_llama_index_chroma.py`。
- 前端测试：`frontend/tests/features/materials/`。

`materials` 拥有 `MaterialFolder`、`CourseMaterial` 和 `MaterialChunk`。问答、生成和计划模块只能通过 `material-context` 使用资料，不得直接写这些对象。P5a 后，`material-context` 还提供同一资料范围内 parsed 资料的只读解析质量摘要，用于下游展示 warning；下游不得直接读取 parser 或 materials 表。

Parser 只向 materials 返回项目内部的 `ParsedDocument`、`ParsedChunk` 和 `ParseDiagnostics`，不得把 Docling 类型暴露到业务模块。诊断页码统一使用一基页码；非分页文本的 `page_count = null` 是正常结果，不表示解析不完整。

## 3. 实现架构

```mermaid
flowchart LR
    FE["资料工作区"] --> API["materials router"]
    API --> SVC["materials service"]
    SVC --> DB["SQLite: folder / material / chunk"]
    SVC --> FS["LocalFileStorage"]
    SVC --> PARSER["RoutingParser / Docling"]
    SVC --> RAG["RagIndex / Chroma"]
    QA["问答 / 生成 / 计划"] --> CTX["material-context"]
    CTX --> DB
    CTX --> RAG
```

文件夹和资料 API 同步执行。上传先写文件和 `CourseMaterial`；解析接口同步写 chunk 与向量。移动已解析资料时，只更新 Chroma 的 `folder_id` metadata，不重新计算 embedding。删除资料或文件夹时，原始文件目录先移入同盘暂存区，后端从 SQLite chunk 构造 RAG 补偿快照，再物理删除数据库记录和向量；失败时恢复数据库、文件和向量，成功后清空暂存文件。

## 4. 数据、状态与接口

- `MaterialFolder`：课程内一级文件夹，`sort_order` 从 1 开始；用户确认删除后物理移除。
- `CourseMaterial.folder_id`：可空，`null` 表示未分类。
- `CourseMaterial.name`：用户可见展示名，可以重命名；`file_url` 是不可由重命名改变的内部存储路径。
- PDF 原文通过受 Bearer token 保护的 `GET /api/v1/materials/{material_id}/content` 读取；接口校验资料所有权、PDF 类型、实际文件存在性和解析后路径仍在存储根目录内。
- 删除文件夹会级联物理删除其中全部资料、`MaterialChunk`、RAG 向量和原始上传目录，不提供回收站或恢复能力。
- 问答、生成内容和学习结果不随资料删除；其 `SourceCitation.material_id`、`chunk_id` 置空，继续使用 `material_name`、页码和 `hit_text` 快照展示历史引用。
- 资料状态：`uploaded -> parsing -> parsed`，失败进入 `parse_failed`，删除进入 `deleted`。
- `material_context.summarize_material_quality_for_scope()` 只读取当前 scope 内 `parse_status = parsed` 的资料，把 `parse_quality` 和 `parse_diagnostics_json` 规整为 `MaterialQualitySummary.warnings`；`severity = "info"` 的 parser 诊断不升级为 warning。
- `parse_quality` 是全局解析质量信号：`complete` 表示本轮未观察到失败，`partial` 表示有可用 chunk 但存在失败页或 warning，`unknown` 表示证据不足。
- `parse_status = parsed` 与 `parse_quality = partial` 可以同时存在；下游仍可读取 chunk，但不能把它解释为完整覆盖。
- 文件夹、资料和课程必须属于当前用户；跨用户或跨课程统一返回 `NOT_FOUND`。
- 公开接口和请求字段见 [../../api-data/frontend-integration.md](../../api-data/frontend-integration.md)。

`MaterialScope` 仅包含：

```json
{
  "include_all_parsed_materials": false,
  "material_ids": ["mat_1", "mat_2"]
}
```

额外传入文件夹范围字段会被 schema 拒绝。

## 5. 核心算法

### 5.1 输入、输出与不变量

- 文件夹 ID 必须属于资料所在课程和当前用户。
- 只有 `parsed` 且未删除资料可以进入 Agent 范围。
- 文件夹创建、重命名和排序不得隐式改变当前选中的 `material_ids`；删除文件夹后，前端必须从当前 `MaterialScope` 移除已删除资料 ID。
- 资料重命名不得改变文件路径、解析状态、chunk、向量或历史引用快照。
- SQLite 的 `folder_id` 与 Chroma metadata 保持一致，但检索硬范围始终使用具体 `material_ids`。

### 5.2 算法步骤

PDF 解析：

1. 使用 `pdf_text_first` profile，关闭 OCR 并强制读取 PDF 文本层。
2. 把 OCR、layout、table batch 限制为 1，队列限制为 4，CPU thread 限制为 1。
3. 首轮存在有效 chunk 时直接返回，不初始化 OCR converter。
4. 首轮零 chunk 时使用 `pdf_ocr_fallback` profile 整份重试，并记录 `OCR_FALLBACK_USED` info。
5. Docling 返回 `partial_success` 时保留有效 chunk，同时记录失败页和 warning；零 chunk 才映射为 `PARSE_FAILED`。
6. SQLite chunk 和向量索引都成功后，才把 diagnostics、`page_count` 和 `parse_quality` 与 `parsed` 状态一起提交。
7. 重解析开始时清空上一轮诊断；解析或索引整体失败时清空 chunk、向量和诊断，quality 回到 `unknown`。

创建文件夹：

1. 校验课程所有权。
2. 未提供 `sort_order` 时查询当前最大值并加 1。
3. 写入 `MaterialFolder` 并返回完整对象。

移动资料：

1. 校验资料所有权及目标文件夹同课程归属。
2. 如果资料已解析，调用 `RagIndex.update_material_folder()` 原位更新 metadata。
3. 更新 SQLite `CourseMaterial.folder_id` 和 `updated_at`。

删除文件夹：

1. 校验文件夹属于当前用户，并查询其中全部资料。
2. 读取已解析资料的 SQLite chunk，构造可重新索引的 `RagChunk` 补偿快照。
3. 把文件型资料目录原子移动到同盘 `.trash` 暂存区；链接资料没有本地文件。
4. 将历史 `SourceCitation.material_id`、`chunk_id` 置空，并在同一 SQLite 事务中删除 chunk、资料和文件夹记录。
5. 调用 `RagIndex.delete_materials()` 批量清理全部派生向量，随后提交 SQLite。
6. RAG 清理或数据库提交失败时执行 `rollback()`，恢复暂存文件并用步骤 2 的快照重新索引；补偿失败返回 `DELETE_COMPENSATION_FAILED`。
7. 数据库成功后彻底清空暂存文件；前端移除文件夹及资料并清理 scope。问答与生成内容及其引用快照不删除。

重命名资料：

1. 按当前用户读取未删除资料，跨用户或不存在统一返回 `NOT_FOUND`。
2. schema 去除名称首尾空格并校验长度为 1-255。
3. 只更新 `CourseMaterial.name` 和 `updated_at`，不调用文件存储、Parser 或 RagIndex。
4. 历史 `SourceCitation.material_name` 作为生成时快照保留原值，新问答使用重命名后的资料名。

PDF 原文预览：

1. 按当前用户读取未删除资料，先完成所有权隔离，再校验 `source_type = file`、`material_type = pdf` 和 PDF MIME 类型。
2. 将内部 `file_url` 拼接到存储根目录并解析真实路径；路径逃逸存储根目录或文件不存在时返回 `PREVIEW_FILE_UNAVAILABLE`。
3. 后端以 `application/pdf`、`inline` 和 `private, no-store` 流式返回原文件；该只读链路不修改数据库、解析状态或索引，因此失败时不需要补偿。
4. 前端带 Bearer token 拉取完整 Blob，创建临时 object URL 交给弹窗内浏览器 PDF 查看器；关闭、替换预览或组件卸载时释放 URL，过期异步请求的结果也会立即释放。

### 5.3 复杂度与资源预算

- 创建目录、重命名资料或目录、移动单份资料为常数次查询；目录列表排序由数据库索引辅助。
- 删除文件夹读取 `n` 份资料和 `c` 个 chunk，数据库与应用层工作量为 `O(n + c)`；RAG 使用一次批量 material-id 删除。文件目录使用同盘重命名暂存，正常路径不把文件内容载入内存。
- metadata 更新不重新调用 Embedding 服务，不产生模型 token 成本。
- 正常级联删除不调用 Embedding；只有 RAG 或数据库失败后的补偿恢复才会重新计算被恢复 chunk 的 embedding。补偿仍失败时必须使用 `rebuild_rag_index` 运维命令恢复派生索引。
- 上传文件大小上限由 `MAX_UPLOAD_FILE_SIZE_BYTES` 控制，默认 50 MiB。
- PDF parser 同时只让每个模型阶段处理 1 个 batch，空间预算以单页 layout/OCR 推理为主，不随磁盘压缩体积线性变化。
- 预览大小为 `s` 字节的 PDF 时，后端按文件响应流传输，应用层不主动读取整份文件；前端 Blob 和浏览器查看器的时间、网络和内存预算均为 `O(s)`。上传上限使单份预览原文件当前不超过 50 MiB，不调用 Parser、RAG、Embedding 或模型。

## 6. 测试与验收

- 文件夹 CRUD、资料重命名、资料移动、级联物理删除、历史引用脱钩、文件/RAG 清理、数据库回滚、索引与文件补偿和权限：`backend/tests/modules/materials/`。
- metadata 原位更新：`backend/tests/integrations/test_llama_index_chroma.py`。
- 文件夹范围字段拒绝和逐文件范围：`backend/tests/modules/material_context/`。
- 基础前端归类与逐文件复选、PDF 名称点击预览、创建后上传提示、文件夹折叠、右键菜单关闭、删除文件夹及其资料后立即移除、删除资料后立即移除、删除失败保留列表并展示错误、链接资料创建、资料重命名和拖拽移动的前端状态回归：`frontend/tests/features/materials/`。
- 计网第七章 59 页 PDF 真实回归：[validation/net-chap7-pdf-parser-regression-2026-07-12.md](validation/net-chap7-pdf-parser-regression-2026-07-12.md)。
- 真实 PDF 从上传、Docling 解析、Chroma 写入到资料/文件夹物理删除的端到端验证：[validation/real-pdf-permanent-deletion-e2e-2026-07-13.md](validation/real-pdf-permanent-deletion-e2e-2026-07-13.md)。

验证命令：

```powershell
pnpm backend:test
pnpm frontend:test
pnpm frontend:build
```

## 7. 决策、限制与演进

- 2026-07-10 确认文件夹只用于归类，不作为 Agent 范围；该规则覆盖早期文档中的目录选择设计。
- 2026-07-12 前端确认课程创建成功后由课程详情页资料区弹出可关闭的上传提示；创建课程弹窗本身不承载资料上传。
- 2026-07-12 前端补齐资料区资源管理器式交互：页面不再同时展示旧侧栏和资料下拉视图，改为单一文件夹树列表；资料区底部空白区域右键可新建文件夹、上传资料或添加链接；资料右键可重命名、解析或删除；文件夹右键可重命名、上传到此文件夹或删除；资料可拖拽到文件夹或未分类完成移动；左键点击其他位置会关闭右键菜单。当前新建文件夹、添加链接、重命名和删除均使用 Mantine 弹窗，不使用浏览器原生 confirm / prompt；接口失败时保留现有列表并展示后端错误。
- 2026-07-13 资料删除统一为不可恢复的物理删除：删除资料记录、SQLite chunk、RAG 向量和原始文件；问答与生成内容保留，引用退化为无资料外键的快照。SQLite、Chroma 和文件系统不共享事务，因此使用文件暂存、RAG 快照和失败补偿保证同步请求的一致性。
- 2026-07-15 资料工作区支持点击 PDF 资料名称打开悬浮预览窗；前端使用鉴权请求获取 Blob 并在关闭或替换时释放 object URL，后端仅向当前用户返回位于存储根目录内的 PDF 原文。
- 2026-07-15 课程详情资料工作区按已确认的 Product Design 视觉目标完成重构：保留现有三栏宽度和全部资料接口，头部提供选择统计与新建文件夹、上传资料、添加链接三个明确入口，主体使用搜索、一级文件夹和逐文件状态组成的圆角局部滚动列表。课程详情页不保留常驻底部拖拽区；只有点击上传按钮或文件夹菜单中的上传入口后，上传弹窗才承载文件选择与拖拽，并继续沿用单文件上传后自动解析的既有流程。
- 当前前端只提供可联调的基础操作，完整视觉和交互由 F04 负责人继续构建。
- 如果未来需要嵌套目录、批量拖拽或异步解析，必须先更新 PRD、API 契约和本领域文档。
- 当前 PDF 首轮关闭高级表格结构模型以避免不必要的内存峰值；需要恢复单元格级结构时，应单独建立带资源预算和复杂表格夹具的任务。

## 8. Frontend Interaction Notes

- 2026-07-13: `MaterialWorkspace` keeps the course-creation upload prompt as a dismissible UI affordance, but `CourseDetailPage` clears the route state after the first render so browser refreshes do not reopen the upload dialog.
- 2026-07-13: The upload dialog exposes a top-right close button, removes the old "skip upload" action, supports selecting files by click or drag-and-drop, and uses copy that explains uploaded files enter parsing automatically.
- 2026-07-13: After a file upload returns `parse_status = uploaded`, the frontend immediately shows the material as `parsing` and calls the retry-parse API. Parse API failure keeps the uploaded material visible and surfaces the backend error.
- 2026-07-13: Material row actions are opened from a three-dot left-click button. The material menu keeps rename and delete, and only exposes "retry parse" for `parse_failed`; it no longer asks users to manually start parsing for newly uploaded materials.
- 2026-07-13: Folder actions are also opened from a three-dot left-click button. The materials workspace no longer exposes custom business actions from right-clicking folders or the blank list area; top action buttons provide create folder, upload material, and add link entry points. Upload prompt copy shows the target folder on its own line and bolds the folder name.
- 2026-07-15: The redesigned resource rows expose file type, file size, parse status, folder counts, search, selection, menus, drag-to-move, and PDF preview without changing the existing APIs. The selected-count summary only counts explicit checked parsed files; an empty explicit selection still means the default all-parsed scope.
