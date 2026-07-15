# Knowledge List Unlearned Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在知识点清单的重要程度筛选右侧增加可变色、可与现有条件组合的“未学习”按钮。

**Architecture:** 使用 `KnowledgeListResult` 内部布尔状态控制本地筛选，不引入接口或持久化。现有搜索、重要程度和学习状态三个条件在同一个 `filter` 表达式中按“并且”组合，进度继续从完整 `items` 计算。

**Tech Stack:** React、TypeScript、CSS、Vitest、Testing Library。

---

### Task 1: 未学习组合筛选

**Files:**
- Modify: `frontend/src/features/generated-content/renderers/KnowledgeListResult.tsx`
- Modify: `frontend/src/features/generated-content/generated-content.css`
- Test: `frontend/tests/features/generated-content/renderers.test.tsx`
- Modify: `docs/domains/generated-content/knowledge-list.md`

- [ ] **Step 1: 写失败测试**

渲染已学习高、未学习高、未学习低三个知识点；选择高重要程度并点击“未学习”，断言仅保留未学习高重要程度项，同时按钮 `aria-pressed` 为 `true`、整体进度仍按三项计算。

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm exec vitest run tests/features/generated-content/renderers.test.tsx`
Expected: FAIL，因为页面没有“未学习”按钮。

- [ ] **Step 3: 实现最小状态和组合条件**

新增：

```ts
const [showUnlearnedOnly, setShowUnlearnedOnly] = useState(false);
```

在现有过滤条件中追加：

```ts
&& (!showUnlearnedOnly || item.learned !== true)
```

在重要程度右侧添加带 `aria-pressed` 的“未学习”按钮，并在激活时添加 `is-active` 类。

- [ ] **Step 4: 添加布局和激活颜色**

工具栏调整为“搜索框、重要程度、未学习按钮”三列；激活按钮使用强调色背景和边框，移动端保持单列换行。

- [ ] **Step 5: 验证并提交**

运行聚焦测试、前端全量测试和生产构建；更新领域文档，检查 `git diff --check` 后提交。
