# Profile 个人中心前端接入

## 范围

个人中心当前接入的后端稳定能力：

- 当前用户信息：`GET /api/v1/auth/me`。
- 退出登录：`POST /api/v1/auth/logout`，成功或失败后都清理本地 token。
- 修改密码：`POST /api/v1/auth/change-password`，成功后该用户全部登录态失效，前端清理 token 并跳转 `/login`（带 `state.reason = "password_changed"` 提示）。
- 模型配置：`GET /api/v1/model-runtime/config` 与 `PUT /api/v1/model-runtime/config`，只提供 Embedding / 其他模型两组表单并同步单机共享 `.env`。
- 今日打卡：`GET /api/v1/checkins/{date}`。
- 当前年度打卡颜色和连续天数：`GET /api/v1/checkins?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`。

非目标：

- 不提供手动打卡 POST；打卡只由二级任务完成事务同步生成。
- 不做排行榜、奖励体系或长期统计图。
- 不做找回密码、资料编辑和邮箱验证。
- 模型配置不按用户隔离；当前单机实例内所有登录用户共享一套配置，管理员权限与多租户隔离记入 `TD-027`。

## 代码入口

- 页面：`frontend/src/pages/ProfilePage.tsx`
- 样式：`frontend/src/pages/profile.css`
- Checkins API 适配：`frontend/src/features/profile/api.ts`
- 模型配置弹窗：`frontend/src/features/profile/ModelConfigModal.tsx`
- 用户 API：`frontend/src/features/auth/api.ts`
- 路由：`frontend/src/router/AppRouter.tsx` 的 `/profile`
- 首页入口：`frontend/src/features/courses/HomeWorkbench.tsx`
- 课程详情入口：`frontend/src/pages/CourseDetailPage.tsx`
- 测试：`frontend/tests/pages/profile-page.test.tsx`、`frontend/tests/features/profile/model-config-modal.test.tsx`

## 前端状态

- loading：页面显示骨架。
- ready：展示头像、昵称/用户名、账号状态、今日完成比例、当前年度打卡颜色和 streak summary。
- error：任一核心请求失败时展示错误，不展示 mock 数据。
- logout：点击“退出登录”调用后端 logout，然后跳转 `/welcome`。
- changePassword：顶部“修改密码”按钮打开弹窗，输入当前密码、新密码（至少 8 位）和确认新密码；前端校验通过后调用 `POST /api/v1/auth/change-password`。成功后弹窗展示“密码已修改、登录已全部失效”，关闭或点击“重新登录”时清理本地 token 并跳转 `/login`；`403 CURRENT_PASSWORD_MISMATCH` 等失败保留输入并展示后端错误，不清理 token。
- modelConfig：顶部“模型配置”按钮打开弹窗；每次打开重新 GET，回填两组模型名和 Base URL，但 API Key 输入始终为空。已有 Key 时展示 `api_key_hint` 且留空保存表示保留；首次配置缺 Key 时阻止提交。保存成功清空 Key 输入，并用 PUT 响应刷新脱敏提示。

## 数据口径

`color_level` 直接来自后端 0-5 枚举。前端仅做颜色映射，不合并或改写 API 状态；缺失日期按 0 级展示为空白打卡格，但不写回后端。范围查询只展示后端已有持久化记录和 summary，不补齐不存在的数据库记录。

`current_streak_days` / `longest_streak_days` 使用后端 summary。前端不自行根据颜色格重新计算 streak。

模型配置的 `general` 对应所有非 Embedding 用途。`general_config_consistent=false` 时弹窗提示历史 `.env` 不一致；用户保存后由后端统一覆盖。完整 Key 只存在于本次输入状态和 PUT 请求中，不写入 localStorage、日志或响应。

## 已知限制

- 页面视觉为第一版可用态，后续可统一做视觉与交互 polish。
- 当前使用自然日 `YYYY-MM-DD` 调用后端，业务时区以服务端契约为准。
- 模型配置是服务实例全局状态，当前任一登录用户都可修改；共享或公网部署前必须完成管理员权限、审计和配置隔离。
