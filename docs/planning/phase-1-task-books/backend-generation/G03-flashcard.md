# G03 Flashcard 生成器

## 1. 任务信息
- **负责人**：独立生成功能后端开发者。
- **目标**：将全部选定资料转为简洁、可翻转、逐卡可追溯的结构化卡片，保存为 `content_type=flashcard`。
- **前置依赖**：G01 公共 contracts、registry、coverage、引用和 fixtures。
- **范围外**：间隔重复、掌握度统计、卡片编辑、学习会话、Anki 导出和独立表。
- **当前已实现 API**：通用 generation POST、历史、详情。
- **本任务新增 API**：无新路径；实现 `content_type=flashcard` 的真实生成。
- **后端未实现仅占位**：掌握 / 待复习写接口；生成时 `mastery_status` 只固定为 `unknown`。

## 2. 实现范围
### 2.1 文件边界
- 创建 / 修改 `backend/app/modules/generation/generators/flashcard/{__init__,schemas,prompts,generator}.py`。
- 创建 `backend/tests/modules/generation/generators/flashcard/test_{flashcard_schemas,flashcard_generator,flashcard_api}.py`。
- 只读 G01、material-context、ModelProvider、generated-content、table-schema。
- 禁止修改 registry、contracts、其他 generator、计划 / handout / task_test、DB model、migration、前端。

### 2.2 参数与 schema
```python
class FlashcardParameters(BaseModel):
    card_count: int = Field(default=20, ge=1, le=100)
    card_style: Literal["term_definition","question_answer","mixed"] = "mixed"
    include_formulas: bool = True
    focus: str | None = Field(default=None, min_length=1, max_length=200)
```
- map schema：`FlashcardCandidate(front, back, tags, source_chunk_ids)` 和 `FlashcardMapResult(candidates, citation_chunk_ids)`。
- front 1-300 字，作为概念 / 问题 / 提示且不泄露完整 back；back 1-1200 字，必须自足、准确、简洁。
- tags 最多 5 个，每个 1-40 字，trim、去空、casefold 去重。
- 每卡至少一个真实 chunk；同次 front trim + casefold 后唯一；重复候选合并引用。

最终 `content_json`：
```json
{"cards":[{"id":"card_001","front":"什么是特征值？","back":"定义与说明","tags":["线性代数"],"mastery_status":"unknown","source_citation_ids":["cit_1"],"sort_order":1}]}
```
- ID 为 `card_001..card_N`，sort order 连续；mastery 固定 unknown；`content=null`；标题 `记忆卡片（N 张）`。

### 2.3 Prompt / map / reduce / 持久化
- map prompt 标注 chunk ID、资料名、定位、heading、正文，提取原子概念、定义、公式含义、步骤和易混点。
- 每个 batch 均调用一次 `ModelProvider.generate_structured(..., FlashcardMapResult)`，达到 card_count 后也不得停止。
- 每批候选 `min(30, max(3, ceil(card_count / batch_count)+2))`。
- reduce 只使用 map 候选，按 style、focus、信息增益、材料覆盖去重排序，不引入资料外事实。
- 本地代码复核长度、唯一性、标签、稳定 ID 和 citation binding；1..requested 张可成功，0 张为 schema invalid。
- include_formulas=false 只降低公式卡优先级，不能跳过含公式资料的 map。
- `run_material_coverage()` 在 reduce 前核对全部 batches；只保存最终 cards 引用。
- `build_generator(model_provider)` 返回 FlashcardGenerator，由 G01 自动发现；不调用其他 generator。

## 3. 字段与接口
请求：
```json
{"content_type":"flashcard","material_scope":{"include_all_parsed_materials":false,"folder_ids":["folder_1"],"material_ids":["mat_2"]},"parameters":{"card_count":30,"card_style":"mixed","include_formulas":true,"focus":"期末核心概念"}}
```
- 成功 HTTP 200：cards 非空、结构固定、逐卡 citation 可在顶层 citations 解析。
- 参数非法：422 `VALIDATION_ERROR` 且不落库；无资料：400；他人资源：404。
- 模型 / schema / coverage 错误保存 failed 记录，无部分 cards / citations。
- 不返回 mastery 更新 URL、复习时间或用户掌握度字段。

## 4. 测试计划
- `test_flashcard_schemas.py`：card count 1/100、0/101；front/back 空 / 超长；tags 去重；空引用；mastery 非 unknown 失败。
- `test_flashcard_generator.py`：两资料多 batch、三种 style、重复 front 合并引用、稳定 ID、数量裁剪、伪造引用过滤、三类失败、import 独立。
- `test_flashcard_api.py`：401、404、400、422、成功 POST / 历史 / 详情、非法参数不落库、failed 可重读、重复请求不同 ID。
```powershell
cd backend
conda run -n course-nexus pytest tests/modules/generation/generators/flashcard -q
conda run -n course-nexus pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context -q
```
- 预期全部 PASS；registry 创建 FlashcardGenerator；无 live network。

## 5. 验收标准
### 自动化验收
- [ ] 所有选择资料 batches 均 map，cards 不超过请求数。
- [ ] front 唯一、ID / sort order 连续、mastery 全为 unknown。
- [ ] 每卡真实引用；未保留候选和伪造 chunk 不落库。
- [ ] 权限、参数、空材料和三类生成失败均覆盖。
### 人工验收
- [ ] 两份含概念 / 公式 / 易混点资料生成 20 张 mixed 卡片。
- [ ] 正面不泄露背面，标签无重复，至少 5 张引用能回到资料快照。
- [ ] card_count=0 返回 422 且历史不变。
- [ ] OpenAPI 没有掌握状态写接口。

## 6. 交付物
- Flashcard 参数、map / reduce / final schema、prompt、generator、factory。
- schema / generator / API 测试和中文验收记录。
- 建议提交：`feat(flashcard): 实现全材料卡片生成`、`test(flashcard): 覆盖结构引用和失败路径`。

## 7. 文档同步
- 更新 `docs/api-data/contracts.md` 的参数、cards 和 mastery 初始语义。
- 核对 table-schema；字段未变不修改。
- 更新 `runtime-flows.md`、`current-state.md`，只标 Flashcard 完成。
- 间隔重复 / 掌握度持久化必须另走产品和数据契约。

## 8. 冲突与注意事项
- **冲突点**：G01 文件只读；mastery 尚无写模型；table-schema 变更交唯一负责人。
- **严格遵循**：全材料 batch + coverage、ModelProvider、最终卡片真实引用、统一内容表。
- **一定不能做**：新增 flashcard / mastery 表或 migration；实现假间隔重复；调用其他 generator / 计划；直接访问 Chroma / OpenAI；空 cards 或无引用标 success。

## 9. 完成检查表
- [ ] 实现、测试、人工验收、docs 全部完成。
- [ ] G01、generated-content、material-context 回归通过。
- [ ] `git diff --check` 通过，测试无网络，修改未越权。
- [ ] 未新增表、migration、依赖；小功能已独立提交。
