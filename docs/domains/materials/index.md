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

文件夹和资料 API 同步执行。上传先写文件和 `CourseMaterial`；解析接口同步写 chunk 与向量。移动已解析资料时，只更新 Chroma 的 `folder_id` metadata，不重新计算 embedding。当前前端删除文件夹按“删除文件夹及其全部内容”的产品语义处理：接口成功后从当前列表移除该文件夹及其下资料；接口失败时不做假删除，保留列表并展示后端错误。

## 4. 数据、状态与接口

- `MaterialFolder`：课程内一级文件夹，`sort_order` 从 1 开始；软删除后不可再访问。
- `CourseMaterial.folder_id`：可空，`null` 表示未分类。
- `CourseMaterial.name`：用户可见展示名，可以重命名；`file_url` 是不可由重命名改变的内部存储路径。
- 删除文件夹的产品语义为删除文件夹及其全部内容；前端成功后移除该文件夹及其下资料。
- 资料状态：`uploaded -> parsing -> parsed`，失败进入 `parse_failed`，删除进入 `deleted`。
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

创建文件夹：

1. 校验课程所有权。
2. 未提供 `sort_order` 时查询当前最大值并加 1。
3. 写入 `MaterialFolder` 并返回完整对象。

移动资料：

1. 校验资料所有权及目标文件夹同课程归属。
2. 如果资料已解析，调用 `RagIndex.update_material_folder()` 原位更新 metadata。
3. 更新 SQLite `CourseMaterial.folder_id` 和 `updated_at`。

删除文件夹：

1. 前端先展示二次确认弹窗，明确告知文件夹下资料和子文件夹会一并删除且无法恢复。
2. 用户确认后调用 `DELETE /api/v1/material-folders/{folder_id}`，请求期间显示 loading 并禁用重复提交。
3. 接口成功后关闭弹窗，从当前列表移除该文件夹及其下资料，并清理这些资料在当前 `MaterialScope` 中的勾选状态。
4. 接口失败时保留列表和弹窗，展示后端返回的错误信息。

重命名资料：

1. 按当前用户读取未删除资料，跨用户或不存在统一返回 `NOT_FOUND`。
2. schema 去除名称首尾空格并校验长度为 1-255。
3. 只更新 `CourseMaterial.name` 和 `updated_at`，不调用文件存储、Parser 或 RagIndex。
4. 历史 `SourceCitation.material_name` 作为生成时快照保留原值，新问答使用重命名后的资料名。

### 5.3 复杂度与资源预算

- 创建目录、重命名资料或目录、移动单份资料为常数次查询；目录列表排序由数据库索引辅助。
- 前端删除文件夹后的本地列表更新为 `O(n)`，`n` 是当前课程资料数。
- metadata 更新不重新调用 Embedding 服务，不产生模型 token 成本。
- 上传文件大小上限由 `MAX_UPLOAD_FILE_SIZE_BYTES` 控制，默认 50 MiB。

## 6. 测试与验收

- 文件夹 CRUD、资料重命名、资料移动、删除回未分类和权限：`backend/tests/modules/materials/`。
- metadata 原位更新：`backend/tests/integrations/test_llama_index_chroma.py`。
- 文件夹范围字段拒绝和逐文件范围：`backend/tests/modules/material_context/`。
- 基础前端归类与逐文件复选、创建后上传提示、文件夹折叠、右键菜单关闭、删除文件夹及其资料后立即移除、删除资料后立即移除、删除失败保留列表并展示错误、链接资料创建、资料重命名和拖拽移动的前端状态回归：`frontend/tests/features/materials/`。

验证命令：

```powershell
pnpm backend:test
pnpm frontend:test
pnpm frontend:build
```

## 7. 决策、限制与演进

- 2026-07-10 确认文件夹只用于归类，不作为 Agent 范围；该规则覆盖早期文档中的目录选择设计。
- 2026-07-12 前端确认课程创建成功后由课程详情页资料区弹出可关闭的上传提示；创建课程弹窗本身不承载资料上传。
- 2026-07-12 前端补齐资料区资源管理器式交互：页面不再同时展示旧侧栏和资料下拉视图，改为单一文件夹树列表；空白区域右键可新建文件夹、上传资料或添加链接；资料右键可重命名、解析或删除；文件夹右键可重命名、上传到此文件夹或删除；资料可拖拽到文件夹或未分类完成移动；左键点击其他位置会关闭右键菜单。当前创建/重命名仍使用浏览器 prompt，后续视觉优化时可替换为 Mantine 弹窗。
- 当前前端只提供可联调的基础操作，完整视觉和交互由 F04 负责人继续构建。
- 如果未来需要嵌套目录、批量拖拽或异步解析，必须先更新 PRD、API 契约和本领域文档。
