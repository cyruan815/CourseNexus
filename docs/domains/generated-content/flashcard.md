# Flashcard Generation

Flashcard uses one structured model call over the complete selected material context. `card_style`, `include_formulas`, and `focus` are generation preferences communicated in the prompt rather than cross-batch filtering rules.

The backend limits the returned array to `card_count`, validates and trims front/back text and tags, rejects duplicate fronts, and adds `card_001...`, `mastery_status="unknown"`, and continuous `sort_order`. Cards contain no source or citation fields.
## 质量与渲染

- `FlashcardDraft.explanation` 是可选兼容字段，用于易混点或补充语境。
- Prompt 要求每张卡只测试一个原子知识点，避免提纲段落和重复正面。
- `FlashcardResult.tsx` 提供单卡翻转、导航、打乱、掌握/未掌握和错卡重练；正面或背面整张卡片均可点击翻面，正面使用云雾蓝 `#E5EDF5`，背面使用 `#EFF2F5`，切换正反面时通过独立渲染节点触发 3D 翻转动画。
- 到达当前练习牌组最后一张后，无论是否已判定全部卡片，都会显示“练习全部”和“只练未掌握”。未明确标记为已掌握的卡片（包括标记未掌握和尚未判定）都会进入“只练未掌握”牌组；“练习全部”始终恢复完整持久化牌组。
- 翻面、导航、判定和当前重练牌组等练习状态仅存在页面内存，不写入后端。

## 牌组编辑与持久化

- 前端入口：`frontend/src/features/generated-content/renderers/FlashcardResult.tsx` 和 `frontend/src/features/course-workspace/api.ts`。
- 后端入口：`backend/app/modules/generated_content/router.py`、`schemas.py` 和 `service.py`。
- `PATCH /api/v1/generated-contents/{generated_content_id}/flashcards` 使用 Bearer 登录态和 `user_id` 归属过滤，只允许编辑未删除的 Flashcard。
- 接口按完整牌组替换 `content_json.cards`。前端分别维护完整持久化牌组和当前练习牌组；打乱及错卡重练只改变练习牌组，添加和删除始终基于完整牌组提交，避免练习子集覆盖未显示卡片。
- 请求包含 1-100 张卡片，正面规范化后必须唯一。后端按提交顺序重新生成 `card_001...`、连续 `sort_order` 和 `mastery_status="unknown"`，并更新 `AIGeneratedContent.updated_at`。
- 成功写入记录 `generated_content_id`、`user_id` 和修改前后卡片数量，不记录卡片正反面、标签或解释正文。

处理步骤为：归属与类型校验 → 牌组数量和重复校验 → O(n) 重新编号与结构校验 → 单行 JSON 更新和提交 → 返回最新 `GeneratedContentRead`。牌组上限为 100，因此时间和额外空间复杂度均为 O(n)，且有明确资源上界。

失败策略：非法牌组返回 `VALIDATION_ERROR`，错误用户或已删除记录返回 `NOT_FOUND`，非 Flashcard 返回 `INVALID_GENERATED_CONTENT_TYPE`；所有校验发生在数据库提交前，不保存部分牌组。前端保存失败时保留原完整牌组并显示错误，不把失败请求当作成功。

测试入口：

- `frontend/tests/features/generated-content/renderers.test.tsx`：整卡翻面、末张重练、未判定卡片处理、完整牌组以及错卡子集添加和删除。
- `frontend/tests/features/generated-content/flashcard-styles.test.js`：正反面固定配色契约。
- `backend/tests/modules/generated_content/test_generated_content_service.py`：归属、类型、牌组约束、规范化、更新时间和脱敏日志。
