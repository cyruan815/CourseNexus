# F02 首页工作台与课程管理

## 1. 任务信息
- 编号：`F02`；负责人：前端开发者。
- 目标：首页课程工作台支持课程 CRUD，并在建课后串行处理可选初始资料。
- 前置：F01；courses CRUD、文件上传、链接创建接口已注册。
- 当前基线：首页仅 list，课程 API 仅 list/detail。
- 范围外：今日待办、日历、个人中心、目录、搜索/排序、计划创建。

## 2. 实现范围
1. 先写 course API、表单、创建编排、编辑删除和局部错误测试。
2. 首页课程区支持 loading/success/empty/error/retry；局部失败不影响退出。
3. 创建弹窗字段 `name,description,teacher,term`，可选文件/链接；防重复提交。
4. 严格先 `POST /courses`，再按用户顺序逐个上传文件、逐个创建链接。
5. 资料单项失败继续后续项，不删除/回滚课程；最终进入课程详情并传失败摘要。
6. 失败摘要只含展示名、source_type、稳定 error.code，不伪造 material_id。
7. 编辑弹窗回填；成功用响应替换列表项；失败保留表单。
8. 删除二次确认；成功移除，失败保留卡片；调用 F01 logout。
9. 今日待办/大日历为后端未实现仅占位：禁用、不请求、不造数据。

### 精确文件边界
- 创建：`features/courses/{types,CourseForm,CreateCourseDialog,EditCourseDialog,DeleteCourseDialog}.tsx`（types 为 `.ts`）。
- 创建：`features/materials/{api,types}.ts`，仅先放 upload/link；F04 追加。
- 创建：`features/todos-calendar/{HomeTodoPlaceholder,HomeCalendarPlaceholder}.tsx`。
- 修改：`features/courses/{api,CourseList}.ts(x)`、`pages/HomePage.tsx`、`types/course.ts`。
- 测试：`tests/features/courses/{course-form,course-mutations}.test.tsx`、`tests/features/materials/api.test.ts`、`tests/pages/home-page.test.tsx` 及现有 course tests。
- 禁止：后端、schema、migration；不创建 todos/calendar 假 API。

## 3. 字段与接口
### 当前已实现 API
- `GET/POST /api/v1/courses`：list / `CourseCreate` -> `CourseRead[]/CourseRead`。
- `GET/PATCH/DELETE /api/v1/courses/{course_id}`：detail/update/软删除 -> `CourseRead`。
- `POST /api/v1/courses/{course_id}/materials`：multipart `file` -> `MaterialRead`。
- `POST /api/v1/courses/{course_id}/material-links`：`name,source_url` -> `MaterialRead`。
- `CourseRead`：`id,user_id,name,description,teacher,term,status,created_at,updated_at,deleted_at`。
- 可选空白字段转 `null`；不发送 ID、user_id、status、审计字段。
### 本任务新增前端接口
- `createCourse/updateCourse/deleteCourse/uploadMaterial/createMaterialLink`，返回真实后端 DTO。
- `InitialMaterialFailure`：`display_name,source_type,error_code`。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；今日待办、日历、`material_count` 均不可猜测或伪造。

## 4. 测试计划
- `courses/api.test.ts`：CRUD 方法、路径、body、拆包。
- `materials/api.test.ts`：FormData 字段 `file` 且不手写 Content-Type；link 精确 body。
- `course-form.test.tsx`：name 必填、空白转 null、loading 防重、错误兜底。
- `course-mutations.test.tsx`：只建课；多资料严格串行；中间失败继续且不删课；建课失败零资料请求；编辑/删除成败。
- `home-page.test.tsx`：四态/retry、401、占位零请求、局部失败隔离、未知 status。
- 命令：`pnpm --dir frontend test -- --run tests/features/courses tests/features/materials/api.test.ts tests/pages/home-page.test.tsx`。
- 预期：退出码 0、无 live network；从仓库根目录运行 `pnpm frontend:test`、`pnpm frontend:build` 均成功。

## 5. 验收标准
### 自动化
- [ ] CRUD 与串行资料均断言真实请求；部分失败不回滚/造数据。
- [ ] 401 跳登录；未知枚举/缺失可选字段兜底；占位零请求。
### 人工
- [ ] 无课程可创建并进详情；初始合法/非法资料混合时课程保留。
- [ ] 编辑刷新一致；删除取消零请求、确认移除。
- [ ] 列表 500 可重试且退出仍可用；1280px/390px 无溢出。

## 6. 交付物
- 课程 CRUD、三个弹窗、首页、初始资料串行流程、占位组件和测试。
- `frontend/tests/manual/F02-home-course-workspace.md`。
- 建议小提交：课程创建/list、编辑删除、初始资料、测试分别提交。

## 7. 文档同步
- 更新 `docs/api-data/frontend-integration.md`：CRUD、null、串行/partial success。
- 更新 `docs/planning/current-state.md`；既有产品/架构口径不变。

## 8. 冲突与注意事项
- 热点：`features/materials/api.ts` 由 F02 建立、F04 追加；`HomePage` 后续替换占位。
- 严格遵循：课程先建、资料后传；软删除；逻辑只依赖 error.code。
- 一定不能做：资料失败补偿删课；并发丢失顺序；猜日历 API；伪造 material_count。

## 9. 完成检查表
- [ ] 范围、测试、回归、构建、桌面/窄屏验收完成。
- [ ] docs、`git diff --check`、所有权检查通过。
- [ ] 未造假数据/接口；小功能独立提交。
