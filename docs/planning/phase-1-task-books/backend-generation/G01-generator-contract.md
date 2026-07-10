# G01 生成能力公共契约与测试夹具

## 0. 业务功能说明

- **业务场景**：学生在课程详情里选择任意一种学习工具时，五类工具都应使用同一套资料范围、生成状态、历史记录和引用规则。
- **用户能力**：本任务本身不增加一个独立按钮，但它保证后续 Quiz、Flashcard、Mindmap、提纲和知识点清单都能稳定接收请求、覆盖所选资料并返回可追溯结果。
- **业务结果**：学生看到的五类生成内容具有一致的成功、失败、历史和引用体验；单个生成器替换提示词或模型时不会破坏其他工具。
- **业务边界**：G01 不负责生成任何具体学习内容，也不负责学习计划、今日讲义或任务测试题；它是 G02-G06 和 S06 共用的业务接入底座。

## 1. 任务信息
- **负责人**：独立生成功能后端开发者。
- **目标**：建立五类生成器共用但不含业务规则的注册、全材料批处理、结构化输出、真实引用、持久化和测试夹具。
- **前置依赖**：现有 `iter_material_context_batches()`、`run_material_coverage()`、`ModelProvider.generate_structured()`、`ai_generated_contents`、`source_citations` 和 generation router。
- **后续依赖**：G02-G06；Handout / Task Test 只能消费公开注册协议。
- **范围外**：五类业务 schema/prompt/map/reduce；计划、讲义、任务测试题、PDF、队列、durable 幂等。
- **当前已实现 API**：`POST /api/v1/courses/{course_id}/generations`、课程生成历史、生成详情。
- **本任务调整 API**：路径不变，三个响应新增 `source_citations`。
- **后端未实现仅占位**：`Idempotency-Key` 持久化、排队、取消和进度查询。

## 2. 实现范围
### 2.1 精确文件边界
- 修改 `backend/app/modules/generation/orchestrator/contracts.py`。
- 修改 `backend/app/modules/generation/orchestrator/registry.py`。
- 修改 `backend/app/modules/generation/orchestrator/service.py`、`router.py`。
- 修改 `backend/app/modules/generation/generators/placeholder_generators.py`，仅保留增量开发 fallback。
- 修改 `backend/app/modules/generated_content/{schemas,repository,service,router}.py`。
- 创建 `backend/tests/modules/generation/conftest.py`。
- 修改 `backend/tests/modules/generation/test_{orchestrator_contract,orchestrator_service,generation_api}.py`。
- 修改 `backend/tests/modules/generated_content/test_generated_content_service.py`。
- 禁止修改 `material_context/**`、`model_provider/**`、`course_qa/**`、`api/router.py`、DB models、migration 和五类业务目录。

### 2.2 公共协议
`contracts.py` 是下列名称和签名的单一所有者：
```python
class GenerateContentRequest(BaseModel):
    content_type: str
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    parameters: dict[str, Any] = Field(default_factory=dict)

class GeneratorOutput(BaseModel):
    title: str
    content: str | None = None
    content_json: dict[str, Any]
    item_citation_chunk_ids: dict[str, list[str]] = Field(default_factory=dict)

class Generator(Protocol):
    content_type: str
    def generate(self, *, batches: tuple[MaterialContextBatch, ...],
                 expected_material_ids: frozenset[str],
                 parameters: dict[str, Any]) -> GeneratorOutput: ...
```
- `GeneratorFactory = Callable[[ModelProvider], Generator]`。
- 每个可引用业务条目必须有唯一 `id`；binding key 等于该条目 ID，value 为最终保留的 chunk IDs。
- orchestrator 将 chunk IDs 转为数据库 citation IDs 并写入条目 `source_citation_ids`。

### 2.3 注册、批处理与状态
- `registry.py` 是 `GeneratorRegistry` 和内建模块路径的单一所有者。
- 固定方法：`register(content_type, factory, replace=False)`、`create(content_type, model_provider)`、`supported_content_types()`。
- 默认自动发现五个目录的 `generator.py:build_generator`；G02-G06 不得编辑 registry。
- 未知类型返回 `VALIDATION_ERROR`；重复注册返回 `CONFLICT`；计划模块可公开注册 Handout / Task Test。
- service 必须使用 `iter_material_context_batches(..., max_tokens=settings.material_batch_max_tokens)`，生产路径禁止 `resolve_context()` 和 Top-K。
- batches 为空返回 `NO_PARSED_MATERIAL` 且不落库；expected IDs 为 batch material IDs 并集。
- 各 generator 必须调用 `run_material_coverage()`；公共层不包含题型、卡片、节点、章节或知识点规则。
- 参数校验错误返回 422 且不落库；模型、schema、coverage 失败保存 failed 记录并以 HTTP 200 返回。
- 成功内容与 citations 同事务提交；失败 `content_json=null`、无 citations、保留 scope 和稳定 error code。

### 2.4 引用与持久化
- 允许引用集合是本次所有 batch 的 chunk IDs；范围外或伪造 ID 必须丢弃。
- 空引用不得回退首 chunk；只为最终保留条目引用的 chunk 建 `SourceCitation`。
- 同一 chunk 每个 generated content 只建一条 citation，`sort_order` 从 1 连续递增。
- 保存真实 `material_id`、`chunk_id`、`material_name`、`page`、`page_index`、最多 500 字的 `hit_text`。
- `page` 与 `page_index` 必须原样保存；对 Markdown、Text 等无分页来源，两者允许同时为 `null`，前端显示“页码未知”。严禁用 `page_index=0` 伪造定位。当前数据库没有“二者至少一个非空”的硬约束，不需要改表；同时更新字段文档以消除歧义。
- 重复请求生成独立记录，符合 PRD；当前无持久化幂等字段，不得伪装支持 durable 幂等。

## 3. 字段与接口
请求复用：
```json
{"content_type":"quiz","material_scope":{"include_all_parsed_materials":true,"folder_ids":[],"material_ids":[]},"parameters":{}}
```
响应新增字段：
```json
{"source_citations":[{"id":"cit_1","material_id":"mat_1","chunk_id":"chk_1","material_name":"chapter.pdf","page":"3","page_index":2,"hit_text":"片段","sort_order":1}]}
```
- 列表、详情、POST 的 `source_citations` 空值固定 `[]`。
- 未登录 401；他人课程 / 资料 404；未知类型 422；无 parsed 资料 400。
- 模型、schema、coverage 失败分别保存 `GENERATION_FAILED`、`GENERATION_SCHEMA_INVALID`、`MATERIAL_COVERAGE_INCOMPLETE`。

## 4. 测试计划
- `conftest.py` 提供内存 SQLite、alice/bob、两份 parsed 多 chunk 资料、无效状态资料、recording/failing ModelProvider 和 TestClient。
- `test_orchestrator_contract.py`：默认 scope、未知类型、重复 / replace 注册、provider 注入、自动发现、外部扩展注册。
- `test_orchestrator_service.py`：多 batch 全覆盖、引用交集 / 去重 / 回填、无 fallback、成功原子写、三类失败无部分数据。
- `test_orchestrator_service.py` 还必须断言无分页 chunk 保存后 `page=null`、`page_index=null`，不会写入虚构的第 0 页。
- `test_generation_api.py`：401、404、400、422、成功 POST / 列表 / 详情、failed 记录、重复请求不同 ID。
- `test_generated_content_service.py`：用户隔离、软删除、citation 归属、空数组。
```powershell
cd backend
conda run -n course-nexus pytest tests/modules/generation tests/modules/generated_content -q
conda run -n course-nexus pytest tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
```
- 预期全部 PASS，且无 live OpenAI / Chroma 网络访问。

## 5. 验收标准
### 自动化验收
- [ ] 两份资料全部进入 map；缺失资料时 reduce 不执行。
- [ ] G02-G06 无需改 registry 即可被默认 registry 创建。
- [ ] 所有 citation chunk 属于 scope，空引用不回退。
- [ ] `source_citation_ids` 均能解析到响应 citation。
- [ ] 成功 / 失败均无半提交，跨用户读取返回 404。
### 人工验收
- [ ] 两资料生成后详情引用可来自两份资料。
- [ ] 强制 provider 失败后历史存在 failed 记录且无 JSON / citations。
- [ ] OpenAPI 无新生成路径，三个响应均含 citation 数组。

## 6. 交付物
- 公共 contracts、registry、orchestrator、generated-content citation response。
- 公共 fixtures、service / API / contract 测试和中文验收记录。
- 建议提交：`feat(generation): 建立公共批处理与引用契约`、`test(generation): 覆盖公共边界`。

## 7. 文档同步
- 更新 `docs/architecture/module-boundaries.md`、`runtime-flows.md`。
- 更新 `docs/api-data/contracts.md`；向前端负责人提交 `frontend-integration.md` 最小 patch。
- 更新 `docs/planning/current-state.md`，只标公共链路完成。
- 更新 `docs/api-data/table-schema.md` 和 `data-model.md` 的无分页引用语义；不改数据库 model 或 migration，因为表字段没有变化。

## 8. 冲突与注意事项
- **冲突点**：`contracts.py`、`registry.py` 仅 G01 修改；generated-content 是共享热点；frontend-integration 由前端负责人合并。
- **严格遵循**：全材料 batch + coverage；ModelProvider；真实引用；固定 scope / envelope / enum。
- **一定不能做**：新增业务表 / migration / job 表；修改计划、handout、task_test；直接调用 OpenAI、Docling、LlamaIndex、Chroma；把 placeholder 当业务完成。

## 9. 完成检查表
- [ ] 实现、测试、人工验收和 docs 同步全部完成。
- [ ] G01 单一所有权签名未被其他任务修改。
- [ ] 受影响模块回归和 `git diff --check` 通过。
- [ ] 自动化测试无 live network，修改未越权。
- [ ] 未新增表、migration、核心依赖；小功能已独立提交。
