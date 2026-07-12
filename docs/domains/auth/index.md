# Auth 认证领域实现

## 业务目标

`auth` 负责用户注册、登录、退出和浏览器侧登录态接入。当前前端登录入口已经从静态原型落地为 React + Mantine 页面，并通过现有 API 适配器连接后端认证接口。

当前用户场景：

- 新用户从入口页进入注册页，提交昵称、用户名/邮箱和密码后进入系统首页。
- 已有用户从入口页进入登录页，提交用户名/邮箱和密码后进入系统首页。
- 认证失败时页面展示后端错误信息，不跳转。

非目标：

- 找回密码流程尚未实现，当前不展示可点击入口，避免用户进入无效自循环。
- 不在本领域实现课程、资料、问答或计划页面。

## 代码入口

- 前端页面入口：`frontend/src/pages/WelcomePage.tsx`、`frontend/src/pages/LoginPage.tsx`、`frontend/src/pages/RegisterPage.tsx`。
- 前端认证 UI：`frontend/src/features/auth/AuthPages.tsx`、`frontend/src/features/auth/auth-pages.css`。
- 前端 API 适配：`frontend/src/features/auth/api.ts`。
- 登录态存储：`frontend/src/features/auth/session.ts`。
- 路由保护：`frontend/src/router/AppRouter.tsx`。
- 测试入口：`frontend/tests/features/auth/auth-pages.test.tsx`、`frontend/tests/pages/app-router.test.tsx`。

## 接口和状态

前端通过以下真实接口完成认证：

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`

成功响应由 `login()` / `register()` 写入 `course_nexus_token`，随后页面导航到 `/`。受保护路由在没有 token 时跳转到 `/welcome`，由入口页再引导用户进入登录或注册。任意 API 请求收到 401 时，`apiRequest()` 清理 token，`session` 模块发出登录态变化事件，路由守卫重新计算状态并回到公开入口。

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

## 测试和验证

- `frontend/tests/pages/app-router.test.tsx` 覆盖匿名跳转 `/welcome`、公开 `/login` 和 `/register`、认证后首页和课程详情路由，以及 401 后回到公开入口。
- `frontend/tests/features/auth/auth-pages.test.tsx` 覆盖登录提交、注册提交、token 写入、成功跳转、错误提示和未实现找回密码入口不展示。
- `backend/tests/api/test_api_foundation.py` 覆盖本地前端对注册接口的 CORS 预检，确保登录、注册和 Bearer Token 请求不会被浏览器拦截。

匹配验证命令：

```powershell
pnpm frontend:test
pnpm frontend:build
```
