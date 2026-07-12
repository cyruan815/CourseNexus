# F04 课程资料工作区

## 0. 业务功能说明

- **业务场景**：学生需要把课件、笔记、教材或网页链接集中放入当前课程，作为后续问答和生成的依据。
- **用户能力**：创建、重命名、排序和删除一级文件夹；上传文件、添加链接、重命名资料、移动归类、查看解析状态、启动或重试解析、删除资料，并逐个选择当前问答或生成要使用的已解析资料。
- **业务结果**：只有解析成功的资料可以进入 Agent 上下文；失败资料有明确状态和重试入口，不会污染问答、生成或计划结果。
- **业务边界**：文件夹只用于资料归类和列表过滤，不能作为 Agent 资料范围；本任务暂不提供资料正文预览和页码定位。

## 1. 任务信息
- 编号：`F04`；负责人：前端开发者。
- 目标：左栏完成文件夹 CRUD、资料 list/upload/link/rename/归类/开始解析/重试/删除和逐文件 scope 选择。
- 前置：F01-F03；materials 与 material-folders 现有接口。
- 当前基线：已有可联调的基础资料工作区、文件夹 API 封装和逐文件选择测试，负责人继续完善交互与状态。
- 范围外：正文预览/下载/页码定位、嵌套目录、文件夹批量选择、后台轮询、OCR 质量承诺。

## 2. 实现范围
1. 先测试完整 API、列表状态、mutation、scope 和占位。
2. 列表覆盖 loading/success/empty/error/retry，失败不影响其他栏。
3. 添加对话框分文件/链接；多文件串行，单项失败继续。
4. 扩展名与 50 MiB 前端预检只作反馈，后端错误码为权威。
5. 上传/link 成功插入真实 `MaterialRead`，不得本地改成 parsed。
6. uploaded 显示开始解析、parse_failed 显示重试，均调用 parse-retries。
7. 当前解析接口同步返回；等待时仅目标行 parsing；HTTP 200 + parse_failed 仍按失败展示。
8. 只有 parsed 资料行可进入显式 scope；文件夹按钮只过滤列表，不能勾选、不能批量转换成 `material_ids`。
9. 文件夹支持创建、重命名、排序和删除；资料支持重命名、移动到目录或未分类；重命名只更新展示名，不修改 `file_url` 或解析状态。
10. 删除目录会级联软删除其中全部资料；删除目录或资料均需二次确认，成功后移除并清理对应 scope，失败时保留当前列表；`file_url` 不作 URL。

### 精确文件边界
- 创建或完善：`features/materials/{MaterialWorkspace,MaterialList,MaterialFolderList,MaterialScopeSelector,AddMaterialDialog,DeleteMaterialDialog,MaterialStatus}.tsx`、`materialErrors.ts`。
- 修改：`features/materials/{api,types}.ts`、`course-workspace/CourseWorkspaceSlots.tsx`、相关 CSS。
- 测试：`tests/features/materials/{material-workspace,add-material-dialog,material-scope-selector,material-status}.test.tsx` 及 `api.test.ts`。
- 修改：`tests/pages/course-detail.test.tsx`；创建 `tests/manual/F04-material-workspace.md`。
- 禁止：后端、scope 字段、问答/生成/计划 feature。

## 3. 字段与接口
### 当前已实现 API
- `GET /api/v1/courses/{course_id}/materials` -> `MaterialRead[]`。
- `POST /api/v1/courses/{course_id}/materials` multipart `file` -> `MaterialRead`。
- `POST /api/v1/courses/{course_id}/material-links` `name,source_url` -> `MaterialRead`。
- `GET/POST /api/v1/courses/{course_id}/material-folders` -> list/create `MaterialFolderRead`。
- `PATCH/DELETE /api/v1/material-folders/{folder_id}` -> rename/sort/delete `MaterialFolderRead`。
- `PATCH /api/v1/materials/{material_id}/folder` `{folder_id:string|null}` -> `MaterialRead`。
- `PATCH /api/v1/materials/{material_id}` `{name:string}` -> 重命名后的 `MaterialRead`。
- `GET/DELETE /api/v1/materials/{material_id}` -> active/delete-state `MaterialRead`。
- `POST /api/v1/materials/{material_id}/parse-retries` -> final `MaterialRead`，当前同步。
- `MaterialRead`：`id,course_id,user_id,folder_id,name,material_type,source_type,file_url,source_url,file_size,mime_type,parse_status,parse_error,page_count,created_at,updated_at,deleted_at`。
- 状态：`uploaded,parsing,parsed,parse_failed,deleted`；未知值显示兜底且不可选。
### 本任务新增前端接口
- `listMaterials,fetchMaterial,renameMaterial,retryMaterialParsing,deleteMaterial`；保留 F02 upload/link 签名。
- `listMaterialFolders,createMaterialFolder,updateMaterialFolder,deleteMaterialFolder,moveMaterialToFolder`。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；无预览/下载/定位接口，不轮询或猜路径。

## 4. 测试计划
- `api.test.ts`：六路径、方法、body、拆包、FormData header。
- `material-workspace.test.tsx`：四态/retry、重命名、解析返回 parsed/failed、删除成败、401/404/未知码。
- `add-material-dialog.test.tsx`：串行队列、中间失败继续、扩展名/大小、link、防重。
- `material-scope-selector.test.tsx`：仅 parsed、all 清空、显式空、删除联动、未知状态、文件夹不可选择。
- `material-status.test.tsx`：五状态、未知、缺 parse_error、稳定错误码。
- 命令：`pnpm --dir frontend test -- --run tests/features/materials tests/features/material-scope tests/pages/course-detail.test.tsx`。
- 预期：退出码 0、无 live network；全量测试/build 成功。

## 5. 验收标准
### 自动化
- [ ] 资料与文件夹 API 以及所有 loading/success/error/disabled 状态有行为测试。
- [ ] 200+parse_failed 不误判；仅 parsed 可选；占位零请求。
### 人工
- [ ] 上传 md -> uploaded -> 开始解析 -> parsed；失败可重试。
- [ ] 合法/非法/过大混合队列继续；link 只显示真实状态。
- [ ] 重命名只更新展示名；删除已选资料同步范围；文件夹只归类不改变 scope；禁用预览不 fetch file_url。
- [ ] 1440/390 下长中文名、URL、状态/按钮不重叠。

## 6. 交付物
- 资料与文件夹 API、左栏、上传/link、重命名、归类、解析/重试、删除、逐文件 scope、状态组件和测试。
- 人工记录 F04；建议按列表、mutation、scope、测试小提交。

## 7. 文档同步
- 新建或更新 `docs/domains/materials/frontend.md`，记录上传、链接、重命名、状态轮询/刷新、重试和删除的组件边界、状态矩阵、API 数据流、错误降级、预览占位边界和测试入口。
- 更新 frontend-integration：资料与文件夹接口、同步解析、状态映射和预览缺口。
- 更新 current-state；不改 PRD 长期预览要求或 ADR。

## 8. 冲突与注意事项
- 依赖 materials 同步语义；改异步前先改契约；F05-F07 只消费 parsed scope。
- 严格遵循：parsed+未删除、稳定 code、file_url 内部路径、显式空禁用。
- 一定不能做：把文件夹作为资料范围；假预览；uploaded 改 parsed；failed 仍可选；猜 API。

## 9. 完成检查表
- [ ] 范围、测试、回归/build、双视口验收、docs/diff/所有权完成。
- [ ] 未调用未实现 API/制造假成功；小功能独立提交。
