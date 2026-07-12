# Materials 资料领域实现

## 1. 业务定位

`materials` 负责把用户资料绑定到课程，完成上传、重命名、一级文件夹归类、解析、切片、索引和删除，并向 Agent 消费者提供可追溯的逐文件资料范围。

一级文件夹只帮助用户整理和浏览资料，不代表 Agent 上下文。用户可以使用课程全部已解析资料，或选择一个、多个具体资料；不能选择整个文件夹。

当前非目标包括嵌套目录、资料正文预览、下载、后台解析队列和链接内容抓取。

## 2. 所有权与代码地图

- 后端入口：`backend/app/modules/materials/{router,schemas,service,repository,models}.py`。
- 解析和索引：`backend/app/integrations/parsers/`、`backend/app/integrations/rag/`。
- 资料范围：`backend/app/modules/material_context/`。
- 基础前端：`frontend/src/features/materials/`，由第一阶段前端负责人继续完善。`MaterialWorkspace` 支持课程详情页传入创建后上传提示开关，用于课程创建成功后引导用户上传资料；当前提供资源管理器式资料区，包括顶部工具栏、搜索、文件夹折叠、空白区域右键菜单、文件夹右键菜单、资料右键菜单和拖拽资料移动到文件夹。
- 后端测试：`backend/tests/modules/materials/`、`backend/tests/modules/material_context/`、`backend/tests/integrations/test_llama_index_chroma.py`。
- 前端测试：`frontend/tests/features/materials/`。

`materials` 拥有 `MaterialFolder`、`CourseMaterial` 和 `MaterialChunk`。问答、生成和计划模块只能通过 `material-context` 使用资料，不得直接写这些对象。

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

文件夹和资料 API 同步执行。上传先写文件和 `CourseMaterial`；解析接口同步写 chunk 与向量。移动已解析资料时，只更新 Chroma 的 `folder_id` metadata，不重新计算 embedding。删除文件夹时，后端从 SQLite chunk 构造补偿快照，批量清理其中资料的 Chroma 向量，再在一次 SQLite 提交中软删除文件夹和全部活动资料；任一步失败都会回滚数据库并尝试从快照恢复向量。

## 4. 数据、状态与接口

- `MaterialFolder`：课程内一级文件夹，`sort_order` 从 1 开始；软删除后不可再访问。
- `CourseMaterial.folder_id`：可空，`null` 表示未分类。
- `CourseMaterial.name`：用户可见展示名，可以重命名；`file_url` 是不可由重命名改变的内部存储路径。
- 删除文件夹会级联软删除其中全部活动资料；资料保留原 `folder_id` 用于历史审计，但不再出现在资料列表或新的 Agent 范围中。
- 级联软删除不物理删除原始上传文件和 `MaterialChunk`；RAG 向量会被清理，历史引用仍可使用保存的资料名快照和 SQLite chunk。
- 资料状态：`uploaded -> parsing -> parsed`，失败进入 `parse_failed`，删除进入 `deleted`。
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
2. 读取活动且已解析资料的 SQLite chunk，构造可重新索引的 `RagChunk` 补偿快照。
3. 为文件夹和全部活动资料写入同一个删除时间；资料状态改为 `deleted`，但此时不提交数据库。
4. 调用 `RagIndex.delete_materials()` 批量清理文件夹内全部资料的派生向量。
5. RAG 清理成功后一次性提交 SQLite；成功才向前端返回文件夹删除结果。
6. RAG 清理或数据库提交失败时执行 `rollback()`，并用步骤 2 的快照重新索引已解析资料；原异常继续返回。补偿失败时返回 `502 INDEXING_FAILED` 和 `rebuild_required = true`，需运行 RAG 重建命令。
7. 前端调用期间显示 loading 并禁用重复提交；成功后移除文件夹及其资料并清理 scope，失败时保留列表和弹窗并展示后端错误。

重命名资料：

1. 按当前用户读取未删除资料，跨用户或不存在统一返回 `NOT_FOUND`。
2. schema 去除名称首尾空格并校验长度为 1-255。
3. 只更新 `CourseMaterial.name` 和 `updated_at`，不调用文件存储、Parser 或 RagIndex。
4. 历史 `SourceCitation.material_name` 作为生成时快照保留原值，新问答使用重命名后的资料名。

### 5.3 复杂度与资源预算

- 创建目录、重命名资料或目录、移动单份资料为常数次查询；目录列表排序由数据库索引辅助。
- 删除文件夹读取 `n` 份资料和 `c` 个已保存 chunk，应用层时间与补偿快照空间均为 `O(n + c)`；RAG 使用一次批量 material-id 删除。前端成功后的本地列表同步为 `O(m)`，`m` 是当前课程资料数。
- metadata 更新不重新调用 Embedding 服务，不产生模型 token 成本。
- 正常级联删除不调用 Embedding；只有 RAG 或数据库失败后的补偿恢复才会重新计算被恢复 chunk 的 embedding。补偿仍失败时必须使用 `rebuild_rag_index` 运维命令恢复派生索引。
- 上传文件大小上限由 `MAX_UPLOAD_FILE_SIZE_BYTES` 控制，默认 50 MiB。
- PDF parser 同时只让每个模型阶段处理 1 个 batch，空间预算以单页 layout/OCR 推理为主，不随磁盘压缩体积线性变化。

## 6. 测试与验收

- 文件夹 CRUD、资料重命名、资料移动、文件夹级联软删除、RAG 清理、数据库回滚、索引补偿和权限：`backend/tests/modules/materials/`。
- metadata 原位更新：`backend/tests/integrations/test_llama_index_chroma.py`。
- 文件夹范围字段拒绝和逐文件范围：`backend/tests/modules/material_context/`。
- 基础前端归类与逐文件复选、创建后上传提示、文件夹折叠、右键菜单关闭、删除文件夹及其资料后立即移除、删除资料后立即移除、删除失败保留列表并展示错误、链接资料创建、资料重命名和拖拽移动的前端状态回归：`frontend/tests/features/materials/`。
- 计网第七章 59 页 PDF 真实回归：[validation/net-chap7-pdf-parser-regression-2026-07-12.md](validation/net-chap7-pdf-parser-regression-2026-07-12.md)。

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
- 2026-07-13 文件夹删除统一为级联软删除语义：文件夹和其中活动资料同事务软删除，RAG 同步清理；SQLite chunk 与原始文件保留。由于 SQLite 与 Chroma 不共享事务，后端用删除前快照和失败重建补偿保证同步接口的一致性。
- 当前前端只提供可联调的基础操作，完整视觉和交互由 F04 负责人继续构建。
- 如果未来需要嵌套目录、批量拖拽或异步解析，必须先更新 PRD、API 契约和本领域文档。
- 当前 PDF 首轮关闭高级表格结构模型以避免不必要的内存峰值；需要恢复单元格级结构时，应单独建立带资源预算和复杂表格夹具的任务。
