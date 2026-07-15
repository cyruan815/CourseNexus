# Generated Content Loading Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every generation click immediately create a disabled animated list item, support concurrent requests, replace it with the returned record, and show canonical titles plus Chinese relative creation times.

**Architecture:** Add a focused course-workspace helper for pending-item metadata, canonical labels, loading copy, and relative-time formatting. Keep network calls unchanged; `CourseDetailPage` owns a pending-task array and renders it ahead of persisted contents, which preserves click order when requests finish out of order. CSS supplies the approved slow gradient sweep, spinner, disabled state, and reduced-motion fallback.

**Tech Stack:** React 19, TypeScript, Mantine, React Router, Vitest, Testing Library, CSS animations.

---

### Task 1: Generated-content list domain helpers

**Files:**
- Create: `frontend/src/features/course-workspace/generated-content-list.ts`
- Create: `frontend/tests/features/course-workspace/generated-content-list.test.ts`

- [ ] **Step 1: Write failing helper tests**

Test canonical names for all five content types, type-specific loading copy, unique pending IDs, and exact relative-time boundaries: less than one minute, minutes, hours, and days.

- [ ] **Step 2: Run the helper test and verify failure**

Run: `npm run test -- tests/features/course-workspace/generated-content-list.test.ts --run`

Expected: FAIL because `generated-content-list.ts` does not exist.

- [ ] **Step 3: Implement the helper module**

Define:

```ts
export interface PendingGeneration {
  id: string;
  content_type: string;
  created_at: string;
}

export function generatedContentTitle(contentType: string): string;
export function generationLoadingMessage(contentType: string): string;
export function createPendingGeneration(contentType: string, now?: Date): PendingGeneration;
export function formatGeneratedContentAge(createdAt: string, now?: Date): string;
```

Use canonical labels `Quiz`, `知识闪卡`, `思维导图`, `复习提纲`, and `知识点清单`. Use a module counter plus timestamp for unique local IDs. Floor elapsed values and return `刚刚`, `N 分钟前`, `N 小时前`, or `N 天前`.

- [ ] **Step 4: Run the helper test and verify pass**

Run: `npm run test -- tests/features/course-workspace/generated-content-list.test.ts --run`

Expected: all helper tests PASS.

### Task 2: Concurrent optimistic loading rows

**Files:**
- Modify: `frontend/src/pages/CourseDetailPage.tsx`
- Modify: `frontend/tests/pages/course-detail.test.tsx`

- [ ] **Step 1: Write failing page tests**

Add deferred generation responses and assert:

```tsx
fireEvent.click(screen.getByRole("button", { name: "生成 Quiz" }));
fireEvent.click(screen.getByRole("button", { name: "生成 Mind Map" }));
expect(screen.getByLabelText("正在生成 Quiz")).toHaveAttribute("aria-disabled", "true");
expect(screen.getByLabelText("正在生成 思维导图")).toHaveAttribute("aria-disabled", "true");
expect(screen.queryByRole("link", { name: "正在生成 Quiz" })).not.toBeInTheDocument();
```

Resolve requests out of order and verify that each pending row independently becomes a link. Return a backend title containing parentheses and a count, then assert the list shows only its canonical title. Assert successful rows do not contain `已完成` or `success`.

- [ ] **Step 2: Run page tests and verify failure**

Run: `npm run test -- tests/pages/course-detail.test.tsx --run`

Expected: FAIL because the current page waits for the request and tracks only one `generatingType`.

- [ ] **Step 3: Implement pending state and rendering**

Replace `generatingType` with:

```ts
const [pendingGenerations, setPendingGenerations] = useState<PendingGeneration[]>([]);
```

On every click, prepend a new pending item before calling `generateCourseContent`. On success remove only that pending ID and prepend the returned record. On thrown error remove only that pending ID and keep the existing workspace error alert. Do not disable tool cards during another request, so the same or different functions can run concurrently.

Update `GeneratedContentPanel` to accept persisted and pending items. Pending items render as non-link `Paper` elements with `aria-disabled="true"`, a spinner, type-specific loading copy, and `生成中`. Persisted items render canonical titles and relative time only; they remain links and have no success badge.

- [ ] **Step 4: Add automatic relative-time refresh**

Inside the panel, store `now` and update it every 60 seconds with an effect. Pass that value to `formatGeneratedContentAge`, and clear the interval during unmount.

- [ ] **Step 5: Run page tests and verify pass**

Run: `npm run test -- tests/pages/course-detail.test.tsx --run`

Expected: all course-detail tests PASS.

### Task 3: Approved loading visuals and accessibility

**Files:**
- Modify: `frontend/src/pages/course-detail.css`
- Modify: `frontend/tests/pages/course-detail.test.tsx`

- [ ] **Step 1: Add source-level visual contract assertions**

Import `course-detail.css?raw` and assert it contains the pending class, 2.1-second sweep, spinner keyframes, disabled cursor, and `prefers-reduced-motion` override.

- [ ] **Step 2: Run the page test and verify failure**

Run: `npm run test -- tests/pages/course-detail.test.tsx --run`

Expected: FAIL because the approved animation classes do not exist.

- [ ] **Step 3: Implement CSS**

Add `.course-detail-generated-item.is-pending`, its gradient border and `::before` sweep layer, `.course-detail-generation-spinner`, and `.course-detail-generation-state`. Use a 2.1-second sweep cycle with a pause at the end and a 0.9-second spinner. Ensure text stays above the sweep layer. Add a `@media (prefers-reduced-motion: reduce)` block that disables both animations.

- [ ] **Step 4: Run the focused tests and verify pass**

Run: `npm run test -- tests/features/course-workspace/generated-content-list.test.ts tests/pages/course-detail.test.tsx --run`

Expected: both suites PASS.

### Task 4: Regression verification

**Files:**
- Verify only; no planned source changes.

- [ ] **Step 1: Run the complete frontend test suite**

Run: `npm run test -- --run`

Expected: all frontend tests PASS.

- [ ] **Step 2: Run production build**

Run: `npm run build`

Expected: TypeScript compilation and Vite production build complete successfully.

- [ ] **Step 3: Review the final diff**

Run: `git diff --check` and `git status --short`.

Expected: no whitespace errors; only planned source, test, plan, and existing unrelated untracked files are present.

- [ ] **Step 4: Commit implementation**

Stage only the helper, page, stylesheet, tests, and this plan. Commit with:

```text
feat(frontend): add generation loading feedback
```
