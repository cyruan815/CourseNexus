# Auth 认证领域实现

## 业务目标

`auth` 负责用户注册、登录、退出、修改密码和浏览器侧登录态接入。当前前端登录入口已经从静态原型落地为 React + Mantine 页面，并通过现有 API 适配器连接后端认证接口。

当前用户场景：

- 新用户从入口页进入注册页，提交昵称、用户名/邮箱和密码后进入系统首页。
- 已有用户从入口页进入登录页，提交用户名/邮箱和密码后进入系统首页。
- 认证失败时页面展示后端错误信息，不跳转。
- 已登录用户在个人中心修改密码；成功后该用户全部登录态失效，必须用新密码重新登录。

非目标：

- 找回密码流程尚未实现，当前不展示可点击入口，避免用户进入无效自循环。
- 不在本领域实现课程、资料、问答或计划页面。
- 单会话撤销与服务端会话表（退出登录仅清本地 token，不能吊销单个 token）属于后续 S02 服务端会话方案，当前通过 `token_epoch` 只支持“按用户整体撤销”。

## 代码入口

- 后端路由：`backend/app/modules/users/router.py`（`/api/v1/auth/*`：register、login、me、logout、change-password）。
- 后端服务：`backend/app/modules/users/service.py`（注册、认证、改密、签发响应）。
- 密码哈希与 token：`backend/app/core/security.py`（PBKDF2-SHA256/210k；HMAC 签名 token，payload 含 `sub`、`epoch`、`exp`）。
- 登录态校验：`backend/app/api/dependencies.py`（`get_current_user` 比对签名、有效期、用户状态和 `token_epoch`）。
- 数据表：`users`（含 `token_epoch` 列，migration `20260930_0006`）。
- 前端页面入口：`frontend/src/pages/WelcomePage.tsx`、`frontend/src/pages/LoginPage.tsx`、`frontend/src/pages/RegisterPage.tsx`、`frontend/src/pages/ProfilePage.tsx`（修改密码入口）。
- 前端认证 UI：`frontend/src/features/auth/AuthPages.tsx`、`frontend/src/features/auth/auth-pages.css`。
- 前端 API 适配：`frontend/src/features/auth/api.ts`。
- 登录态存储：`frontend/src/features/auth/session.ts`。
- 路由保护：`frontend/src/router/AppRouter.tsx`。
- 后端测试：`backend/tests/modules/users/`。
- 前端测试：`frontend/tests/features/auth/auth-pages.test.tsx`、`frontend/tests/pages/app-router.test.tsx`、`frontend/tests/pages/profile-page.test.tsx`。

## 接口和状态

前端通过以下真实接口完成认证：

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/change-password`（2026-09-30 新增）

成功响应由 `login()` / `register()` 写入 `course_nexus_token`，随后页面导航到 `/`。受保护路由在没有 token 时跳转到 `/welcome`，由入口页再引导用户进入登录或注册。任意 API 请求收到 401 时，`apiRequest()` 清理 token，`session` 模块发出登录态变化事件，路由守卫重新计算状态并回到公开入口。

### 修改密码与登录态撤销

`POST /api/v1/auth/change-password` 需要 Bearer token，请求体为 `current_password` + `new_password`（8-255，确认密码仅前端校验）。服务端在同一事务内更新 `password_hash` 并递增 `token_epoch`：

- token 签发时把用户当前 `token_epoch` 写入 payload；`get_current_user` 校验签名与有效期后查库比对 epoch，不一致按 `UNAUTHORIZED` 处理。
- 历史 token payload 不含 `epoch`，解码兜底为 0，与列默认值一致：升级 migration `20260930_0006` 后存量登录态不受影响。
- 修改密码成功 → 该用户全部存量 token（含发起改密的会话）立即失效；前端清理本地 token，跳转 `/login` 并提示用新密码重新登录。
- 当前密码错误返回 `403 CURRENT_PASSWORD_MISMATCH`：不能使用 401，前端会把 401 统一处理为清理 token 跳登录，输错旧密码不应把用户登出。
- 新旧密码相同返回 `400 VALIDATION_ERROR`；长度违规走统一 `422 VALIDATION_ERROR`。
- 请求体不落日志；错误日志只记录错误码、方法和路径。

失败与状态：

- `ready`：表单可编辑。
- `pending`：提交中按钮 loading，弹窗禁止关闭。
- `error`：展示后端稳定错误信息，保留输入，不清 token。
- `changed`：展示成功提示；关闭弹窗或点击“重新登录”时清理 token 并跳转登录页。

本地前端以 `http://localhost:5173` 直连 `http://localhost:8000` 时，后端通过 `CORS_ALLOWED_ORIGINS` 处理跨域预检；默认仅允许该本地前端来源，并允许 Bearer Token 所需的 `Authorization` 请求头。CORS 只允许浏览器发起和读取请求，实际身份仍由后端 Bearer Token 校验。

页面状态：

- `ready`：展示入口页、登录表单或注册表单。
- `pending`：提交中按钮进入 Mantine `loading` 状态。
- `error`：后端返回错误时展示 `Alert`，保留在当前表单页。

## 设计决策

- 认证入口页保持轻量品牌展示，不承担系统首页的业务工作台职责。
- 登录和注册页采用左侧蓝绿渐变视觉区 + 右侧白底表单区，延续静态原型方向。
- 输入框采用接近 Google 登录表单的小圆角方框，而不是胶囊形输入框。
- 静态原型不展示 loading / empty / error；真实接入后只在实际提交和失败时出现 pending / error。
- 2026-09-30 修改密码采用 `token_epoch` 整体撤销而非服务端会话表：改动小、不依赖待审定的 S02；代价是退出登录仍不能吊销单个 token，S02 落地后该列可退役。错误旧密码使用 403 避免触发前端全局 401 登出。

## 测试和验证

- `frontend/tests/pages/app-router.test.tsx` 覆盖匿名跳转 `/welcome`、公开 `/login` 和 `/register`、认证后首页和课程详情路由，以及 401 后回到公开入口。
- `frontend/tests/features/auth/auth-pages.test.tsx` 覆盖登录提交、注册提交、token 写入、成功跳转、错误提示和未实现找回密码入口不展示。
- `backend/tests/api/test_api_foundation.py` 覆盖本地前端对注册接口的 CORS 预检，确保登录、注册和 Bearer Token 请求不会被浏览器拦截。
- `backend/tests/modules/users/test_auth_service.py` 覆盖密码哈希、token epoch 编解码、历史 token 兜底和 `get_current_user` 拒绝过期 epoch。
- `backend/tests/modules/users/test_auth_api.py` 覆盖改密成功后旧 token 失效/旧密码不可登录/新密码可登录、错误旧密码保留会话、相同与过短新密码拒绝、不影响其他用户、密码不落入日志。
- `frontend/tests/pages/profile-page.test.tsx` 覆盖改密表单校验、成功清理会话跳转登录页和失败保留会话。

匹配验证命令：

```powershell
pnpm frontend:test
pnpm frontend:build
```
