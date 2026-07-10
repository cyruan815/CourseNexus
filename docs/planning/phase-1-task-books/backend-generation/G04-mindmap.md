# G04 Mindmap 生成器

## 0. 业务功能说明

- **业务场景**：学生面对章节多、概念关系复杂的课程资料时，需要先看清主题之间的层级和联系。
- **用户能力**：选择资料和中心主题，生成包含根节点、知识节点和关系边的结构图，并查看主要节点对应的资料来源。
- **业务结果**：零散知识被组织成可展开、可收起的知识结构，前端可以据此渲染真正的 Mindmap。
- **业务边界**：本任务只生成结构化节点和关系，不决定前端使用哪种图形库，也不输出 SVG、Mermaid 或固定坐标。

## 1. 任务信息
- **负责人**：独立生成功能后端开发者。
- **目标**：基于全部选定资料生成稳定节点、父子层级、关联边和节点级引用的知识结构图 JSON。
- **前置依赖**：G01 公共 contracts、registry、coverage、引用和 fixtures。
- **范围外**：前端图库、坐标布局、拖拽编辑、SVG / Mermaid / 图片输出、节点表和跨次合并。
- **当前已实现 API**：通用 generation POST、历史、详情。
- **本任务新增 API**：无新路径；实现 `content_type=mindmap` 的真实生成。
- **后端未实现仅占位**：节点展开状态、用户编辑、布局坐标和导出，不得制造这些字段。

## 2. 实现范围
### 2.1 文件边界
- 创建 / 修改 `backend/app/modules/generation/generators/mindmap/{__init__,schemas,prompts,generator}.py`。
- 创建 `backend/tests/modules/generation/generators/mindmap/test_{mindmap_schemas,mindmap_generator,mindmap_api}.py`。
- 只读 G01、material-context、ModelProvider、generated-content 和 table-schema。
- 禁止修改 registry、contracts、其他 generator、计划 / exports、DB model、migration、前端。

### 2.2 参数、schema 和图不变量
```python
class MindmapParameters(BaseModel):
    center_topic: str | None = Field(default=None, min_length=1, max_length=120)
    max_depth: int = Field(default=4, ge=2, le=6)
    max_nodes: int = Field(default=80, ge=3, le=200)
    include_cross_links: bool = True
```
- map schema：`ConceptCandidate(local_key,label,summary,parent_local_key,source_chunk_ids)`、`RelationCandidate(from_local_key,to_local_key,relation)`、`MindmapMapResult`。
- 最终恰有一个 level=1 根；根 ID 等于 root_node_id；其他节点恰有一个 child 父边且全部从根可达。
- child 边无环 / 自环 / 多父；子 level=父 level+1，不超过 max_depth。
- related 边仅在 include_cross_links=true；端点存在、无自环、无同向重复。
- 节点按 breadth-first 稳定编号 `node_001..node_N`；同父 label casefold 唯一；非根至少一条真实引用。

最终 `content_json`：
```json
{"root_node_id":"node_001","nodes":[{"id":"node_001","label":"线性代数","summary":"中心主题","level":1,"source_citation_ids":[]},{"id":"node_002","label":"特征值","summary":"节点说明","level":2,"source_citation_ids":["cit_1"]}],"edges":[{"from":"node_001","to":"node_002","relation":"child"}]}
```
- nodes 目标 3..max_nodes；资料只支持 1-2 个合法节点时允许成功并在标题加 `（资料较少）`；0 节点失败。
- edges 不直接带 citation；根引用可为空；`content=null`，标题 `知识导图：{root.label}`。

### 2.3 Prompt / map / reduce / 持久化
- map prompt 逐 chunk 标注 ID、资料名、定位、heading、正文，提取局部概念 / 父子 / 明确关联。
- 每个 batch 均调用一次 `ModelProvider.generate_structured(..., MindmapMapResult)`；无概念时也返回空结果并计入 coverage。
- reduce 只用 map 结果做同义合并、中心选择、层级组织和裁剪，不重新读取原文 / 外部事实。
- 本地代码负责 breadth-first 编号、level 计算、端点校验、树可达性 / 环 / 多父检测和 citation binding。
- 超 max_nodes 时按跨材料支持数、主题相关性、基础性裁剪；删除父节点时重挂到最近保留祖先或删除子树，不能悬空。
- `run_material_coverage()` 在 reduce 前检查；只保存最终 nodes 的引用。
- `build_generator(model_provider)` 返回 MindmapGenerator，由 G01 自动发现；不依赖前端图库或其他 generator。

## 3. 字段与接口
请求：
```json
{"content_type":"mindmap","material_scope":{"include_all_parsed_materials":true,"folder_ids":[],"material_ids":[]},"parameters":{"center_topic":"内存管理","max_depth":5,"max_nodes":100,"include_cross_links":true}}
```
- 成功 HTTP 200：root / nodes / edges 符合不变量，node citation 可在顶层 citations 解析，不返回坐标 / HTML。
- 参数非法 422 且不落库；无资料 400；他人资源 404。
- 模型失败保存 `GENERATION_FAILED`；根缺失、悬空、环、多父、空图为 `GENERATION_SCHEMA_INVALID`；覆盖缺失为 coverage error。

## 4. 测试计划
- `test_mindmap_schemas.py`：唯一根、可达、单父、level；悬空、自环、环、多父、重复边、超深 / 超量失败；cross links 开关。
- `test_mindmap_generator.py`：两资料多 batch、同义合并、breadth-first ID、裁剪不悬空、最终引用、伪造引用过滤、三类失败、import 独立。
- `test_mindmap_api.py`：401、404、400、422、成功 POST / 历史 / 详情、所有 edge 端点存在、环输出形成 failed 记录、重复请求不同 ID。
```powershell
cd backend
conda run -n course-nexus pytest tests/modules/generation/generators/mindmap -q
conda run -n course-nexus pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context -q
```
- 预期全部 PASS；registry 创建 MindmapGenerator；无 live network。

## 5. 验收标准
### 自动化验收
- [ ] 每个 batch 被 map，未使用 Top-K。
- [ ] 根、节点、边、层级、可达性、环和多父检测通过。
- [ ] 节点数 / 深度符合参数，稳定 ID 可供前端使用。
- [ ] 非根节点均为真实范围内引用，失败无部分图。
### 人工验收
- [ ] 两份相关资料生成导图，主要分支能覆盖两份资料。
- [ ] 任意 child 路径 level 连续，任意 edge 两端存在。
- [ ] cross links=false 时只有 child；max_nodes=3 时仍连通。
- [ ] JSON 不含 SVG、Mermaid、坐标或前端库对象。

## 6. 交付物
- Mindmap 参数、map / reduce / final schema、prompt、generator、factory。
- 图校验 / generator / API 测试和中文验收记录。
- 建议提交：`feat(mindmap): 实现全材料知识导图生成`、`test(mindmap): 覆盖图结构引用和失败路径`。

## 7. 文档同步
- 新建或更新 `docs/domains/generated-content/mindmap.md`：记录生成器分层和代码入口、nodes/edges schema 与图结构不变量、prompt 职责、分批节点抽取、跨批次实体归一、稳定 ID、边合并、环路/孤立节点处理、覆盖和引用算法及伪代码，并说明图算法复杂度、资源预算、失败策略和测试证据。
- 更新 `docs/api-data/contracts.md` 的参数和 nodes / edges。
- 核对 table-schema；字段不变不修改，变更交唯一负责人。
- 更新 `runtime-flows.md`、`current-state.md`，只标 Mindmap 完成。
- 不修改前端渲染或 PRD。

## 8. 冲突与注意事项
- **冲突点**：G01 文件只读；JSON 是前端热点；table-schema 由 S01 负责人维护。
- **严格遵循**：全材料 batch + coverage、ModelProvider、后端只产结构化图、真实节点引用。
- **一定不能做**：新增 mindmap / node / edge 表；输出 SVG / Mermaid / 坐标；调用其他 generator / 计划 / Chroma / OpenAI；悬空、环、多父、空图标 success。

## 9. 完成检查表
- [ ] 实现、测试、人工验收、docs 全部完成。
- [ ] G01、generated-content、material-context 回归通过。
- [ ] `git diff --check` 通过，测试无网络，修改未越权。
- [ ] 未新增表、migration、依赖；小功能已独立提交。
