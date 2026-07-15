# Knowledge List Learning Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为知识点清单增加可永久保存的逐项已学习状态、绿色完成样式和整体学习进度。

**Architecture:** 保持现有数据库结构，在 `ai_generated_contents.content_json.items[*]` 中保存 `learned`。后端提供仅更新单个知识点学习状态的窄接口；前端进行即时状态切换、失败回滚，并从完整清单计算进度。

**Tech Stack:** FastAPI、Pydantic、SQLAlchemy、React、TypeScript、Mantine、Vitest、Testing Library、pytest。

---

### Task 1: 生成结果默认学习状态

**Files:**
- Modify: `backend/app/modules/generation/generators/knowledge_list/schemas.py`
- Test: `backend/tests/modules/generation/generators/knowledge_list/test_knowledge_list_generator.py`

- [ ] **Step 1: 写失败测试**

在生成器测试中断言最终 item 包含 `learned is False`，同时确认模型输入 schema 仍是没有学习状态的 `KnowledgeDraft`。

- [ ] **Step 2: 运行测试并确认因缺少字段失败**

Run: `pytest backend/tests/modules/generation/generators/knowledge_list/test_knowledge_list_generator.py -q`

- [ ] **Step 3: 最小实现**

给最终 `KnowledgeItem` 增加：

```python
learned: bool = False
```

保持 `KnowledgeDraft` 不变，使 AI 不参与用户状态生成。

- [ ] **Step 4: 重新运行测试并确认通过**

Run: `pytest backend/tests/modules/generation/generators/knowledge_list/test_knowledge_list_generator.py -q`

### Task 2: 单项学习状态更新接口

**Files:**
- Modify: `backend/app/modules/generated_content/schemas.py`
- Modify: `backend/app/modules/generated_content/service.py`
- Modify: `backend/app/modules/generated_content/router.py`
- Test: `backend/tests/modules/generated_content/test_generated_content_service.py`
- Test: `backend/tests/modules/generated_content/test_generated_content_api.py`

- [ ] **Step 1: 写服务层失败测试**

覆盖：所有者可以设置和取消 `learned`；历史 item 缺失字段仍可更新；其他 item 内容不变；错误用户、错误类型、失败记录、非法 JSON 和不存在的 item 被拒绝。

- [ ] **Step 2: 写 API 失败测试**

发送：

```json
{"learned": true}
```

断言返回内容中的目标 item 为 `learned: true`，并验证额外字段被 Pydantic 拒绝。

- [ ] **Step 3: 运行聚焦测试确认失败原因是接口尚不存在**

Run: `pytest backend/tests/modules/generated_content/test_generated_content_service.py backend/tests/modules/generated_content/test_generated_content_api.py -q`

- [ ] **Step 4: 最小实现 schema 和 service**

新增：

```python
class KnowledgeItemLearningStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learned: bool
```

服务函数只复制 `content_json`、定位 `knowledge_item_id`、修改 `learned`、更新时间并保存，不接受其他知识点字段。

- [ ] **Step 5: 接入 PATCH 路由**

增加 `/generated-contents/{generated_content_id}/knowledge-items/{knowledge_item_id}/learning-state`，使用当前登录用户 ID 调用 service。

- [ ] **Step 6: 运行聚焦测试并确认通过**

Run: `pytest backend/tests/modules/generated_content/test_generated_content_service.py backend/tests/modules/generated_content/test_generated_content_api.py -q`

### Task 3: 前端数据契约和 API

**Files:**
- Modify: `frontend/src/features/generated-content/types.ts`
- Modify: `frontend/src/features/generated-content/guards.ts`
- Modify: `frontend/src/features/course-workspace/api.ts`
- Test: `frontend/tests/features/courses/api.test.ts`

- [ ] **Step 1: 写 API 失败测试**

断言调用路径、PATCH 方法和请求体：

```ts
expect(fetch).toHaveBeenCalledWith(
  "/api/v1/generated-contents/gen_1/knowledge-items/kp_001/learning-state",
  expect.objectContaining({ method: "PATCH", body: JSON.stringify({ learned: true }) }),
);
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm exec vitest run frontend/tests/features/courses/api.test.ts`

- [ ] **Step 3: 最小实现**

给 `KnowledgeItem` 增加 `learned?: boolean`，guard 将缺失值规范化为 `false`，新增 `updateKnowledgeItemLearningState()` API 方法。

- [ ] **Step 4: 运行测试确认通过**

Run: `pnpm exec vitest run frontend/tests/features/courses/api.test.ts`

### Task 4: 知识点进度与绿色交互

**Files:**
- Modify: `frontend/src/features/generated-content/GeneratedContentRenderer.tsx`
- Modify: `frontend/src/features/generated-content/renderers/KnowledgeListResult.tsx`
- Modify: `frontend/src/features/generated-content/generated-content.css`
- Test: `frontend/tests/features/generated-content/renderers.test.tsx`

- [ ] **Step 1: 写前端失败测试**

覆盖初始 `1 / 2` 和 `50%`、历史缺失字段按未学习、点击后调用 API 并变绿、再次点击取消、搜索后进度仍按全部两项计算、失败时回滚并显示提示。

- [ ] **Step 2: 运行测试并确认失败**

Run: `pnpm exec vitest run frontend/tests/features/generated-content/renderers.test.tsx`

- [ ] **Step 3: 最小实现组件逻辑**

`GeneratedContentRenderer` 将 `content.id` 传入 `KnowledgeListResult`。组件维护完整 items、单个 pending ID 和错误信息，从完整 items 计算：

```ts
const learnedCount = items.filter((item) => item.learned === true).length;
const percentage = Math.round((learnedCount / items.length) * 100);
```

点击时即时切换，调用接口；失败时恢复旧数组并显示 Alert。

- [ ] **Step 4: 添加视觉样式**

顶部增加绿色进度区；条目增加可访问的学习状态按钮；`.is-learned` 使用浅绿色背景和绿色边框；移动端保持完整宽度和正常高度。

- [ ] **Step 5: 运行渲染测试并确认通过**

Run: `pnpm exec vitest run frontend/tests/features/generated-content/renderers.test.tsx`

### Task 5: 文档与完整验证

**Files:**
- Modify: `docs/domains/generated-content/knowledge-list.md`
- Modify: `docs/domains/generated-content/index.md`

- [ ] **Step 1: 更新领域文档**

记录 `learned` 数据语义、PATCH 接口、历史兼容、进度计算、保存失败回滚和同一清单串行保存约束。

- [ ] **Step 2: 运行后端完整生成内容与知识点测试**

Run: `pytest backend/tests/modules/generated_content backend/tests/modules/generation/generators/knowledge_list -q`

- [ ] **Step 3: 运行前端完整测试**

Run: `pnpm --filter frontend test -- --run`

- [ ] **Step 4: 运行前端构建**

Run: `pnpm --filter frontend build`

- [ ] **Step 5: 检查并提交**

仅暂存本功能相关代码、测试和文档，运行 `git diff --cached --check` 后使用 Conventional Commit 提交。
