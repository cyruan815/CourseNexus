# Materials 资料领域实现

## 1. 业务定位

`materials` 负责把用户资料绑定到课程，完成上传、重命名、一级文件夹归类、解析、切片、索引和删除，并向 Agent 消费者提供可追溯的逐文件资料范围。

一级文件夹只帮助用户整理和浏览资料，不代表 Agent 上下文。用户可以使用课程全部已解析资料，或选择一个、多个具体资料；不能选择整个文件夹。

当前非目标包括嵌套目录、资料正文预览、下载、后台解析队列和链接内容抓取。

## 2. 所有权与代码地图

- 后端入口：`backend/app/modules/materials/{router,schemas,service,repository,models}.py`。
- 解析和索引：`backend/app/integrations/parsers/`、`backend/app/integrations/rag/`。
- 资料范围：`backend/app/modules/material_context/`。
- 基础前端：`frontend/src/features/materials/`，由第一阶段前端负责人继续完善。`MaterialWorkspace` 支持课程详情页传入创建后上传提示开关，用于课程创建成功后引导用户上传资料。
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

文件夹和资料 API 同步执行。上传先写文件和 `CourseMaterial`；解析接口同步写 chunk 与向量。移动已解析资料或删除文件夹时，只更新 Chroma 的 `folder_id` metadata，不重新计算 embedding。

## 4. 数据、状态与接口

- `MaterialFolder`：课程内一级文件夹，`sort_order` 从 1 开始；软删除后不可再访问。
- `CourseMaterial.folder_id`：可空，`null` 表示未分类。
- `CourseMaterial.name`：用户可见展示名，可以重命名；`file_url` 是不可由重命名改变的内部存储路径。
- 删除文件夹不会删除资料，所有关联资料回到未分类。
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
- 文件夹操作不得隐式改变当前选中的 `material_ids`。
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

1. 查询目录内资料。
2. 对已解析且未删除资料更新向量 metadata 为未分类。
3. 将所有关联资料 `folder_id` 置空。
4. 软删除文件夹并在同一数据库提交中保存资料变化。

重命名资料：

1. 按当前用户读取未删除资料，跨用户或不存在统一返回 `NOT_FOUND`。
2. schema 去除名称首尾空格并校验长度为 1-255。
3. 只更新 `CourseMaterial.name` 和 `updated_at`，不调用文件存储、Parser 或 RagIndex。
4. 历史 `SourceCitation.material_name` 作为生成时快照保留原值，新问答使用重命名后的资料名。

### 5.3 复杂度与资源预算

- 创建目录、重命名资料或目录、移动单份资料为常数次查询；目录列表排序由数据库索引辅助。
- 删除文件夹为 `O(n)`，`n` 是目录内资料数；每份已解析资料执行一次 metadata 更新。
- metadata 更新不重新调用 Embedding 服务，不产生模型 token 成本。
- 上传文件大小上限由 `MAX_UPLOAD_FILE_SIZE_BYTES` 控制，默认 50 MiB。
- PDF parser 同时只让每个模型阶段处理 1 个 batch，空间预算以单页 layout/OCR 推理为主，不随磁盘压缩体积线性变化。

## 6. 测试与验收

- 文件夹 CRUD、资料重命名、资料移动、删除回未分类和权限：`backend/tests/modules/materials/`。
- metadata 原位更新：`backend/tests/integrations/test_llama_index_chroma.py`。
- 文件夹范围字段拒绝和逐文件范围：`backend/tests/modules/material_context/`。
- 基础前端归类与逐文件复选、创建后上传提示、删除文件夹后资料回到未分类、链接资料创建、资料重命名和拖拽移动的前端状态回归：`frontend/tests/features/materials/`。
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
- 2026-07-12 前端补齐资料区能用版资源管理器交互：空白区域右键可新建文件夹、上传资料或添加链接；资料右键可重命名、解析或删除；文件夹右键可重命名或删除；资料可拖拽到文件夹或未分类完成移动。当前创建和重命名仍使用浏览器 prompt，后续视觉优化时替换为 Mantine 弹窗。
- 当前前端只提供可联调的基础操作，完整视觉和交互由 F04 负责人继续构建。
- 如果未来需要嵌套目录、批量拖拽或异步解析，必须先更新 PRD、API 契约和本领域文档。
- 当前 PDF 首轮关闭高级表格结构模型以避免不必要的内存峰值；需要恢复单元格级结构时，应单独建立带资源预算和复杂表格夹具的任务。
