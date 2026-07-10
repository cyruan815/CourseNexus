# F03 课程详情布局与共享资料范围

## 1. 任务信息
- 编号：`F03`；负责人：前端开发者。
- 目标：固定课程详情三栏，并为 F04-F07 提供唯一共享 `MaterialScope`。
- 前置：F01-F02；课程详情 API；shared-contract 的范围结构。
- 当前基线：详情页是四个顺序空 section，无共享范围/响应式布局。
- 范围外：资料、问答、生成、计划的业务请求。

## 2. 实现范围
1. 先测试 scope 纯函数/Provider、三栏、窄屏和栏级隔离。
2. 默认 scope 为 all=true 且两个数组为空；切 all 时立即清空 IDs。
3. 显式范围 ID 去重保序；两个数组空时标记不可提交。
4. 桌面固定左资料、中问答、右工具；右栏内含工具/生成历史/计划入口。
5. `>=1024px` Grid：`minmax(240px,.8fr) minmax(360px,1.5fr) minmax(280px,1fr)`。
6. 窄屏用“资料/问答/工具”分段切换；三个 slot 保持挂载，避免丢输入。
7. 每栏独立 ErrorBoundary；单栏失败不卸载整页或重置 scope。
8. 课程请求 loading/403/404/500 为页面级；401 交 F01；业务状态归各 feature。
9. courseId 变化重置 scope；同课程切 panel 不重置。

### 精确文件边界
- 创建：`features/material-scope/{types,materialScope}.ts`、`MaterialScopeProvider.tsx`、`useMaterialScope.ts`。
- 创建：`features/course-workspace/{CourseWorkspace,WorkspacePanel,WorkspacePanelBoundary,CourseWorkspaceSlots}.tsx`、`course-workspace.css`。
- 修改：`pages/CourseDetailPage.tsx`、`features/courses/CourseHeader.tsx`、`tests/pages/course-detail.test.tsx`。
- 测试：`tests/features/material-scope/{material-scope,material-scope-provider}.test.ts(x)`、`tests/features/course-workspace/course-workspace.test.tsx`。
- 禁止：Provider 内请求 API；引入 UI/状态库；修改后端。

## 3. 字段与接口
### 当前已实现 API
- F03 只调用 `GET /api/v1/courses/{course_id}` -> `CourseRead`。
### 固定前端接口
- `MaterialScope`：`include_all_parsed_materials:boolean, folder_ids:string[], material_ids:string[]`。
- all=true 时两个数组必须空；all=false 时二者按并集，显式空范围禁止提交。
- Context：`scope,has_explicit_selection,useAllParsedMaterials,useExplicitMaterials,toggleMaterial,toggleFolder,removeMaterial,resetScope`。
- `toggleFolder` 仅保留契约；无真实 folder API 时 UI 不制造 folder ID。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；MaterialFolder 与资料预览无 router，slot 仅占位、不发请求。

## 4. 测试计划
- `material-scope.test.ts`：默认值、all 清空、去重、移除幂等、显式空。
- `material-scope-provider.test.tsx`：多消费者同步；局部状态隔离；course key 重置。
- `course-workspace.test.tsx`：恰好三顶级 region；右栏子区；窄屏保持挂载；栏级失败/重试。
- `course-detail.test.tsx`：页面四态、401、缺 courseId、F02 失败摘要。
- 命令：`pnpm --dir frontend test -- --run tests/features/material-scope tests/features/course-workspace tests/pages/course-detail.test.tsx`。
- 预期：退出码 0；再运行全量测试和 `pnpm frontend:build` 均成功。

## 5. 验收标准
### 自动化
- [ ] scope 不变量和每个 action 有测试；两栏共享且状态隔离。
- [ ] 桌面仅三栏；窄屏切换不卸载；未知字段/异常兜底。
### 人工
- [ ] 1440/1024 三栏滚动正常；768/390 分段切换且输入保留。
- [ ] 单栏报错其他栏可用；长标题/失败名不撑破容器。

## 6. 交付物
- MaterialScope 类型/Provider/hook、三栏壳、ErrorBoundary、CSS 与测试。
- `frontend/tests/manual/F03-course-detail-shell.md`。
- 建议小提交：三栏、scope、隔离测试分别提交。

## 7. 文档同步
- 更新 `docs/api-data/frontend-integration.md`：唯一 scope、默认值、显式空禁用、消费者。
- 更新 current-state；既有 PRD 三栏和架构未变化。

## 8. 冲突与注意事项
- F04-F07 必须导入本类型，不复制；`CourseWorkspaceSlots` 是共享热点。
- 严格遵循：范围硬过滤、固定三字段、局部 500 隔离、全局 401。
- 一定不能做：新增同义 scope 字段；四顶级栏；Provider 请求业务 API；单栏失败清 scope。

## 9. 完成检查表
- [ ] 范围、目标测试、全量回归、构建、四视口验收完成。
- [ ] docs、diff、所有权检查通过；未复制 scope/造假接口；小功能独立提交。
