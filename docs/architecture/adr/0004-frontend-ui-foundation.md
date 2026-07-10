# ADR 0004: Frontend UI Foundation

## Status

Accepted.

## Context

CourseNexus v0.1 已经具备 React + TypeScript + Vite 前端骨架和 `react-router-dom` 路由基础。第一阶段后续需要持续实现登录、首页课程工作台、课程详情、资料工作台、课程问答、生成内容、学习计划和执行页等前端页面。

这些页面需要稳定的 UI 组件、图标、日期处理、请求缓存和全局交互能力。如果每个页面临时手写控件、请求状态和弹窗通知，会增加小团队开发成本，也会让 AI 协作生成的界面风格不一致。

## Options

1. 采用 Mantine 作为主 UI 组件库，配套 Tabler Icons、TanStack Query 和 dayjs。
2. 采用 shadcn/ui + Tailwind CSS，获得更强可定制性。
3. 采用 Ant Design，优先获得后台管理类组件效率。
4. 暂不引入组件库，继续手写基础组件。

## Decision

v0.1 前端 UI 基础设施选择：

- UI 组件库：`@mantine/core`。
- 通用 hooks / 表单 / 日期 / 通知 / 弹窗 / Spotlight：`@mantine/hooks`、`@mantine/form`、`@mantine/dates`、`@mantine/notifications`、`@mantine/modals`、`@mantine/spotlight`。
- 图标库：`@tabler/icons-react`。
- 服务端状态和请求缓存：`@tanstack/react-query`。
- 日期工具：`dayjs`。
- 路由库继续使用已引入的 `react-router-dom`。

Mantine 是当前主组件库。shadcn/ui 可作为后续视觉升级候选，但不在 v0.1 第一阶段作为默认依赖引入。

## Reasons

- CourseNexus 是学习工作台，不是营销官网。Mantine 的表单、布局、弹窗、通知、日期、状态组件更贴近工作台页面的高频需求。
- Mantine 相比 shadcn/ui 更接近装好即可使用的组件库，适合当前小团队和 AI 协作开发节奏。
- Tabler Icons 与 Mantine 视觉风格较匹配，能覆盖课程、资料、日历、设置、执行状态等常见图标场景。
- TanStack Query 能统一处理后端数据的 loading、error、cache、invalidate 和 retry，避免页面级组件重复编写请求状态。
- dayjs 体积小、API 简洁，适合学习计划、日历和任务截止日期处理。
- Ant Design 虽然成型快，但默认企业后台感较强，不是 CourseNexus 当前希望形成的学习工作台气质。

## Consequences

- `frontend/package.json` 必须声明 Mantine、Tabler Icons、TanStack Query 和 dayjs 相关依赖。
- 前端应用装配层应在 `frontend/src/app/` 集中配置 MantineProvider、QueryClientProvider、Notifications 和 Modals 等全局 provider。
- 页面和 feature 应优先复用 Mantine 组件；跨页面复用的二次封装进入 `frontend/src/components/`。
- API 请求和缓存策略优先通过 TanStack Query 组织；底层 HTTP client 和响应适配仍归属 `frontend/src/api/`。
- 课程、资料、计划、执行等页面必须继续覆盖 loading、empty、error 和 ready 状态。
- 后续如切换到 shadcn/ui、Tailwind CSS、Ant Design 或其他主 UI 体系，必须新增或更新 ADR。
