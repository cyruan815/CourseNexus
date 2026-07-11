# Courses Domain

## 概述

课程领域负责系统首页的课程工作台和后续课程管理能力。当前实现是第一阶段静态 POC：首页按照低保真原型呈现今日待办、日历空状态、课程概览、课程卡片和添加课程入口，用于先确认页面结构和视觉基线。

## 业务目标

- 帮助学生进入系统后快速看到课程、今日学习任务和日历计划状态。
- 在无学习计划时给出生成计划入口，不展示不存在的任务内容。
- 为后续课程详情、课程创建、学习计划生成和大日历页面保留清晰入口。

## 当前范围

- 已实现：静态首页工作台，包含顶部品牌栏、主题切换占位、个人中心占位、今日待办空状态、日历空状态、课程卡片网格、添加课程入口和交互说明。
- 未实现：课程创建表单、真实课程列表接口接入、计划生成页跳转、大日历页、课程卡片编辑/删除菜单。

## 代码入口

- 页面入口：`frontend/src/pages/HomePage.tsx`
- 首页工作台组件：`frontend/src/features/courses/HomeWorkbench.tsx`
- 首页样式：`frontend/src/features/courses/home-workbench.css`
- 课程 API 适配仍保留在：`frontend/src/features/courses/api.ts`
- 课程列表旧组件仍保留在：`frontend/src/features/courses/CourseList.tsx`

## 模块边界

- `HomePage` 只负责挂载课程首页工作台。
- `features/courses/HomeWorkbench.tsx` 只承载课程首页静态 UI 和 mock 数据，不直接调用后端 API。
- 后续真实数据接入时，应通过 `features/courses/api.ts` 或专用 adapter 获取课程数据，再把页面状态映射到组件 props。
- 今日待办、日历和学习计划的真实状态属于 `study-mode` / `todos-calendar` 相关领域；课程首页只能展示聚合结果，不直接耦合其内部实现。

## 状态流转

当前静态 POC 固定展示 ready 状态：

- 课程概览：展示 4 门 mock 课程和一个添加课程入口。
- 今日待办：展示无计划 empty 状态和生成计划入口占位。
- 日历：展示无计划 empty 状态和跳转计划生成页说明。

后续接入真实接口时需要补齐：

- loading：课程列表、今日任务和日历聚合加载中。
- empty：没有课程、没有计划、当天没有任务。
- error：课程或计划聚合加载失败，提供重试入口。
- ready：展示真实课程和计划聚合。

## 关键决策

- 首页采用 Mantine 组件和局部 CSS，遵守亮色工作台规范，不做营销型 hero。
- 静态数据放在 `HomeWorkbench.tsx` 内部，避免在尚未确认 API 聚合契约前扩大数据层变更。
- 课程名是明确链接，卡片更多操作是独立按钮，避免交互元素嵌套。
- 当前添加课程、生成计划、主题切换和个人中心入口只做静态占位。

## 测试与验证

- 页面测试：`frontend/tests/pages/home-page.test.tsx`
- 路由测试：`frontend/tests/pages/app-router.test.tsx`
- 验证命令：

```powershell
pnpm frontend:test
pnpm frontend:build
```

## 已知限制

- 本页面仍是静态 HTML/前端 POC，不读取真实课程、计划或日历数据。
- 主题切换按钮和个人中心按钮尚未绑定行为。
- 课程详情链接使用 mock course id，后续接真实数据后应改为后端课程 id。
