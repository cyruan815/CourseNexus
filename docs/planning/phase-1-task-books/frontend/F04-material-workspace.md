# F04 课程资料工作区

## 1. 任务信息
- 编号：`F04`；负责人：前端开发者。
- 目标：左栏完成资料 list/upload/link/开始解析/重试/删除和 scope 选择。
- 前置：F01-F03；materials 六个现有接口与 `MaterialRead`。
- 当前基线：仅 F02 upload/link 封装；无资料 UI。
- 范围外：正文预览/下载/页码定位、目录 CRUD/移动、后台轮询、OCR 质量承诺。

## 2. 实现范围
1. 先测试完整 API、列表状态、mutation、scope 和占位。
2. 列表覆盖 loading/success/empty/error/retry，失败不影响其他栏。
3. 添加对话框分文件/链接；多文件串行，单项失败继续。
4. 扩展名与 50 MiB 前端预检只作反馈，后端错误码为权威。
5. 上传/link 成功插入真实 `MaterialRead`，不得本地改成 parsed。
6. uploaded 显示开始解析、parse_failed 显示重试，均调用 parse-retries。
7. 当前解析接口同步返回；等待时仅目标行 parsing；HTTP 200 + parse_failed 仍按失败展示。
8. 只有 parsed 可进入显式 scope；未知/未解析状态禁用。
9. 删除二次确认；成功移除并 `removeMaterial(id)`，失败保留。
10. 预览和目录为后端未实现仅占位：disabled、零请求；`file_url` 不作 URL。

### 精确文件边界
- 创建：`features/materials/{MaterialWorkspace,MaterialList,MaterialScopeSelector,AddMaterialDialog,DeleteMaterialDialog,MaterialStatus}.tsx`、`materialErrors.ts`。
- 修改：`features/materials/{api,types}.ts`、`course-workspace/CourseWorkspaceSlots.tsx`、相关 CSS。
- 测试：`tests/features/materials/{material-workspace,add-material-dialog,material-scope-selector,material-status}.test.tsx` 及 `api.test.ts`。
- 修改：`tests/pages/course-detail.test.tsx`；创建 `tests/manual/F04-material-workspace.md`。
- 禁止：后端、scope 字段、问答/生成/计划 feature。

## 3. 字段与接口
### 当前已实现 API
- `GET /api/v1/courses/{course_id}/materials` -> `MaterialRead[]`。
- `POST /api/v1/courses/{course_id}/materials` multipart `file` -> `MaterialRead`。
- `POST /api/v1/courses/{course_id}/material-links` `name,source_url` -> `MaterialRead`。
- `GET/DELETE /api/v1/materials/{material_id}` -> active/delete-state `MaterialRead`。
- `POST /api/v1/materials/{material_id}/parse-retries` -> final `MaterialRead`，当前同步。
- `MaterialRead`：`id,course_id,user_id,folder_id,name,material_type,source_type,file_url,source_url,file_size,mime_type,parse_status,parse_error,page_count,created_at,updated_at,deleted_at`。
- 状态：`uploaded,parsing,parsed,parse_failed,deleted`；未知值显示兜底且不可选。
### 本任务新增前端接口
- `listMaterials,fetchMaterial,retryMaterialParsing,deleteMaterial`；保留 F02 upload/link 签名。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；无预览/下载/定位和 MaterialFolder API；不轮询或猜路径。

## 4. 测试计划
- `api.test.ts`：六路径、方法、body、拆包、FormData header。
- `material-workspace.test.tsx`：四态/retry、解析返回 parsed/failed、删除成败、401/404/未知码。
- `add-material-dialog.test.tsx`：串行队列、中间失败继续、扩展名/大小、link、防重。
- `material-scope-selector.test.tsx`：仅 parsed、all 清空、显式空、删除联动、未知状态。
- `material-status.test.tsx`：五状态、未知、缺 parse_error、稳定错误码。
- 命令：`pnpm --dir frontend test -- --run tests/features/materials tests/features/material-scope tests/pages/course-detail.test.tsx`。
- 预期：退出码 0、无 live network；全量测试/build 成功。

## 5. 验收标准
### 自动化
- [ ] 六 API 和所有 loading/success/error/disabled 状态有行为测试。
- [ ] 200+parse_failed 不误判；仅 parsed 可选；占位零请求。
### 人工
- [ ] 上传 md -> uploaded -> 开始解析 -> parsed；失败可重试。
- [ ] 合法/非法/过大混合队列继续；link 只显示真实状态。
- [ ] 删除已选资料同步范围；禁用预览不 fetch file_url。
- [ ] 1440/390 下长中文名、URL、状态/按钮不重叠。

## 6. 交付物
- 资料 API、左栏、上传/link、解析/重试、删除、scope、状态组件和测试。
- 人工记录 F04；建议按列表、mutation、scope、测试小提交。

## 7. 文档同步
- 更新 frontend-integration：六接口、同步解析、状态映射、预览/目录缺口。
- 更新 current-state；不改 PRD 长期预览要求或 ADR。

## 8. 冲突与注意事项
- 依赖 materials 同步语义；改异步前先改契约；F05-F07 只消费 parsed scope。
- 严格遵循：parsed+未删除、稳定 code、file_url 内部路径、显式空禁用。
- 一定不能做：假预览/目录；uploaded 改 parsed；failed 仍可选；猜 API。

## 9. 完成检查表
- [ ] 范围、测试、回归/build、双视口验收、docs/diff/所有权完成。
- [ ] 未调用未实现 API/制造假成功；小功能独立提交。
