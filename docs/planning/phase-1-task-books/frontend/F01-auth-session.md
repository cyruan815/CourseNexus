# F01 账号、会话与路由保护

## 0. 业务功能说明

- **业务场景**：学生第一次使用 CourseNexus 时需要注册账号；之后通过登录进入自己的课程空间，并在登录过期时安全返回登录页。
- **用户能力**：注册、登录、退出；刷新页面后恢复有效登录态；登录失效后重新登录并返回原先准备访问的页面。
- **业务结果**：每位学生只能进入自己的课程、资料、对话和计划空间，未登录用户不能绕过登录页访问业务页面。
- **业务边界**：本任务不包含修改密码、头像、昵称、设备管理或多角色权限，这些属于后续个人中心能力。

## 1. 任务信息
- 编号：`F01`；负责人：前端开发者。
- 目标：完成注册、登录、退出、刷新恢复会话和全局 401 失效闭环。
- 前置：现有 auth router、F01 所列响应 envelope、`course_nexus_token` key。
- 当前基线：API/token 函数已存在；登录页未提交，路由只判断 token 是否存在。
- 范围外：修改/找回密码、refresh token、OAuth、多设备和服务端撤销。

## 2. 实现范围
1. 先写认证 API、Provider、页面、路由和 401 失败测试。
2. 建立 `restoring | authenticated | anonymous` 会话状态；有 token 时只调用一次 `/auth/me`。
3. 完成 `/login`、`/register`；注册含确认密码，确认密码不发送后端。
4. 登录/注册成功保存 token 和用户，回原受保护地址；提交中禁止重复请求。
5. `apiRequest()` 遇 HTTP 401 时清 token 并发布失效事件；403/404 不退出。
6. logout 无论 API 成败都清本地会话并跳 `/login`。
7. 恢复中不挂载业务页；匿名访问受保护页保存 pathname/search/hash。
8. 已认证访问登录/注册页跳首页；未知路由按认证态回首页或登录。

### 精确文件边界
- 创建：`frontend/src/features/auth/types.ts`、`AuthSessionProvider.tsx`、`useAuthSession.ts`、`frontend/src/pages/RegisterPage.tsx`。
- 修改：`frontend/src/app/App.tsx`、`router/AppRouter.tsx`、`api/client.ts`、`features/auth/{api,session}.ts`、`pages/LoginPage.tsx`。
- 创建测试：`frontend/tests/features/auth/auth-session-provider.test.tsx`、`tests/pages/{login-page,register-page}.test.tsx`。
- 修改测试：`tests/api/client.test.ts`、`tests/features/auth/{api,session}.test.ts`、`tests/pages/app-router.test.tsx`。
- 禁止：`backend/**`、migration、根 README；不引入 Axios/Redux/表单库。

## 3. 字段与接口
### 当前已实现 API
- `POST /api/v1/auth/register`：`username,password,nickname?` -> `AuthResponse`。
- `POST /api/v1/auth/login`：`username,password` -> `AuthResponse`。
- `GET /api/v1/auth/me`：Bearer -> `AuthUser`。
- `POST /api/v1/auth/logout`：Bearer -> `{logged_out:true}`。
- `AuthUser`：`id,username,nickname,avatar_url,status,created_at`。
- `AuthResponse`：`access_token,token_type,expires_at,user`；字段保持 snake_case。
### 本任务新增前端接口
- `AuthSessionValue`：`status,user,acceptAuth(auth),logout()`；未知用户使用 `null`。
- 401 事件不携带 token、密码或请求正文。
### 本任务新增 API / 后端未实现仅占位
- 不新增后端 API；refresh token、修改密码、找回密码均不展示可操作假入口。

## 4. 测试计划
- `auth-session-provider.test.tsx`：无 token 不请求 me；有效 token 恢复；me 401 清理；业务 401 失效；logout 成败都清理。
- `login-page.test.tsx`：精确 JSON、原路由返回、401、loading 防重。
- `register-page.test.tsx`：8 字符、确认密码、CONFLICT、请求不含 `confirm_password`。
- `app-router.test.tsx`：恢复态不挂业务页；公开/保护/未知路由；完整 returnTo。
- `client.test.ts`：401 非标准 payload 仍清理；403 保留；FormData 不设 JSON 头。
- 命令：`pnpm --dir frontend test -- --run tests/features/auth tests/pages/login-page.test.tsx tests/pages/register-page.test.tsx tests/pages/app-router.test.tsx tests/api/client.test.ts`。
- 预期：退出码 0、无 live network；再从仓库根目录运行 `pnpm frontend:test` 与 `pnpm frontend:build`，两者均成功。

## 5. 验收标准
### 自动化
- [ ] 注册、登录、退出、恢复、401 均有行为测试。
- [ ] 401 清会话，403/404 不清；未知错误码有兜底。
- [ ] 重复提交只发一个请求，注册不发送确认密码。
### 人工
- [ ] 无 token 访问课程页跳登录，登录后返回原 URL。
- [ ] 注册后自动登录；刷新恢复；伪造 token 后回登录并删除 token。
- [ ] logout 后浏览器后退不显示受保护数据。
- [ ] 1280px/390px 下表单、错误和按钮不重叠。

## 6. 交付物
- Provider/hook/types、登录注册页、认证路由、401/退出实现及测试。
- `frontend/tests/manual/F01-auth-session.md`，不得记录密码/token。
- 建议小提交：`feat(auth): 完成注册登录与会话恢复`、`fix(auth): 统一处理登录失效`、`test(auth): 覆盖认证边界`。

## 7. 文档同步
- 更新 `docs/api-data/frontend-integration.md`：认证路由、恢复、token key、401/403。
- 完成后更新 `docs/planning/current-state.md`；产品/架构未变化，不改 PRD/ADR。

## 8. 冲突与注意事项
- 热点：`api/client.ts`、`router/AppRouter.tsx`；F01 先合并，后续任务只消费。
- 严格遵循：Bearer、`course_nexus_token`、稳定 `error.code`、密码/token 不入日志。
- 一定不能做：只凭 token 视为恢复；把 403 当退出；API 模块直接操作 Router；猜测 refresh API。

## 9. 完成检查表
- [ ] 范围、目标测试、全量回归、构建和双视口验收完成。
- [ ] 文档同步、`git diff --check`、所有权检查通过。
- [ ] 未新增核心依赖/假 API；每个小功能独立提交。
