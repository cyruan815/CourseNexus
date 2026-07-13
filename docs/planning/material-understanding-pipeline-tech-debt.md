# TD-017：资料理解流水线完整性与检索质量改造

## 1. 定位与状态

- 类型：跨 `materials`、`material-context`、RAG integration 和前端资料工作区的大型技术债。
- 优先级：高。
- 当前状态：待拆分规划；本文件只记录问题、边界和后续优化方向，不代表已经批准架构或开始实现。
- 处理原则：拆成多个可独立验证的子项目，不与普通业务功能混在一个提交或 PR 中。

本技术债的核心不是简单替换 Docling，而是修正两个错误假设：

1. 解析器返回 `success` 或存在非空 chunk，不等于资料内容完整。
2. 资料范围包含全部已解析资料，不等于一次问答已把全部资料发送给模型。

## 2. 已确认的问题证据

### 2.1 解析层静默漏内容

以 59 页 `Chap7 物理层.pdf` 真实材料为例：

- Docling 返回 `success`，资料被保存为 `parsed + complete`。
- 当前数据库只保存 49 个 chunk，chunk 原始字符总数约 4,406。
- 独立使用 PyMuPDF 和 Poppler 提取时，PDF 文本层约有 6,488-6,511 个非空白字符；数据库 chunk 只有约 3,566 个非空白字符。
- 约 45% 的可提取文本没有进入最终 chunk。
- 第 8、18、25、27、29、31、34、38、42、51、55、57 页存在原生文本，但完全没有生成 chunk。
- Docling 在这些页面上通常只保留标题，并把主体识别为 `PictureItem(text="")`；`HybridChunker` 因而没有输出页面正文。

当前 PDF 路径只要首轮产生任意有效 chunk 就直接返回，OCR fallback 只处理整份零 chunk 的场景。`parse_quality` 只依据 conversion status、明确失败页和 warning 判定，没有审计源页面与最终 chunk 的内容覆盖关系。

### 2.2 检索层无法保证任务覆盖

同一材料的课程问答还存在第二层信息损失：

- 课程问答固定使用相似度 `Top-K`，当前默认 `top_k = 8`。
- 模糊追问只使用本轮问题作为检索 query，没有先结合对话历史改写为独立问题。
- “每一节的详细讲解版”实际命中的前 6 个结果是来自不同页的重复“主要内容”目录，第 7 个仍接近目录，第 8 个只有页码文本。
- 当前缺少目录角色识别、精确/近似去重、相关性阈值、MMR/来源多样性、父上下文展开和章节覆盖检查。
- “总结整份材料”“逐节讲解”等全文任务仍走局部 Top-K，检索目标与用户任务目标不一致。

模型被提示只能依据本次提供的 context 回答，因此“只看到目录”是对实际输入的正确描述，不是生成模型本身无法理解整份文件。

## 3. 技术债范围

本技术债包含四个彼此关联但必须分阶段落地的方向：

1. 多格式分层解析与局部回退。
2. CourseNexus 自有的格式级完整性审计。
3. 结构化父子切块、内容角色和去重元数据。
4. 查询改写、任务路由、混合检索和全文覆盖策略。

本技术债不要求当前立即迁移到 RAGFlow、Dify、LangChain 或 pgvector。现有 FastAPI、SQLite、LlamaIndex、Chroma 和业务模块边界继续保留；是否引入新的核心依赖必须另写 ADR 并由项目负责人确认。

## 4. 兼容性硬约束

材料解析层的内部改造必须尽量对已开发业务透明：

- `course-qa`、生成器、学习计划和任务内容不得直接依赖 PyMuPDF、Docling、OCR 或格式原生解析器。
- `materials` 继续拥有资料状态和 `MaterialChunk`；业务消费者继续只通过 `material-context` 读取资料。
- `retrieve_relevant_context()`、`resolve_generation_context()` 和 `iter_material_context_batches()` 的现有核心语义必须保留；扩展字段采用可选或兼容默认值。
- 新的统一 IR 只存在于 parser integration 内部，通过兼容适配器继续产出现有 `ParsedDocument` / `ParsedChunk` 所需字段。
- `parse_status` 与 `parse_quality` 现有枚举不因本技术债直接破坏；回退来源、覆盖模式和逐单元状态优先放入扩展 diagnostics。
- API 变更只允许向后兼容的加字段；旧前端忽略新字段时仍能工作。
- 解析升级和检索升级使用独立 feature flag，可以分别启用、验证和回滚。

### 4.1 重解析安全切换

当前重解析会先替换旧 chunk，再删除和重建向量；新解析或索引失败可能破坏原本可用的资料。后续必须调整为候选结果安全切换：

```text
现有活动版本继续服务
  -> 生成候选 IR / chunk / 质量报告
  -> 完整性审计
  -> 候选索引验证
  -> 全部成功后切换活动结果
  -> 清理旧派生数据
```

失败时必须删除候选结果并保留旧 chunk、旧向量和原有 `parsed` 可用状态，只记录重解析尝试错误。

当前 chunk ID 由 `material_id + chunk_index` 决定，新切块可能出现“ID 相同但内容语义变化”。后续需评估版本化或内容哈希 ID，并为历史 `SourceCitation.chunk_id` 提供重解析脱钩策略；历史 `material_name`、页码和 `hit_text` 快照必须继续可展示。

## 5. 目标解析分层

### 5.1 公共内部流水线

```text
ParserRouter
  -> 格式原生解析器
  -> 按需增强解析器
  -> 轻量 Document IR
  -> QualityAuditor
  -> StructuralChunker
  -> CompatibilityChunkAdapter
  -> MaterialChunk / RagChunk
```

建议的轻量 IR 至少表达：

- `ParsedDocument`：文件类型、unit 集合、parser version、质量报告。
- `ParsedUnit`：page / slide / section / image、序号、元素集合、状态和指标。
- `ParsedElement`：类型、正文、标题路径、来源定位、解析器来源、内容角色和内容哈希。
- `SourceLocator`：按格式保存页码、幻灯片号、段落索引、行号或 bbox。

不建议把不同解析器不可比较的 confidence 强行统一为一个伪精确分值。完整性以可核验的源单元清单、逐单元状态和覆盖指标为准。

### 5.2 PDF

采用 Fast-first、按页分流：

1. PyMuPDF 快速读取每页文本块、坐标、字符数、图片和绘图占比，作为文本覆盖基线。
2. 原生文本充分且顺序可接受时直接生成页面元素。
3. 多栏、复杂表格或标题结构不清晰时，只对目标页调用无 OCR 的 Docling 做结构增强。
4. 无有效原生文本且存在栅格主体时，只对异常页执行 OCR。
5. 流程图、频谱图和拓扑图的视觉关系理解作为可选 VLM 层，不阻塞“文本覆盖完整”的第一阶段验收。
6. 每个有效文本页必须最终拥有正文；漏一页且补偿失败即为 `partial`。

PyMuPDF 基线不能被 Docling 增强结果删除。存在回退但全部有效文本页均成功覆盖时，资料仍可为 `complete`，同时在 diagnostics 中记录 `fallback_used` 和具体页码。

### 5.3 DOCX

- 使用 `python-docx` 和 OOXML body 顺序遍历段落、标题、列表、表格、超链接、drawing 和分页符。
- DOCX 不按页审计；以正文 XML 元素、表格和嵌入对象为完整性单位。
- 复杂表格可以用 Docling 做差异检查；SmartArt、图片型正文和嵌入对象进入渲染/OCR/VLM 回退。
- 每个源元素必须是 `extracted`、`described`、`ignored_with_reason`、`unsupported` 或 `failed`，不能静默消失。

### 5.4 PPTX

- 使用 `python-pptx` 读取幻灯片标题、文本框、列表层级、表格、图表、shape、speaker notes 和位置。
- 一张幻灯片作为一个父 unit；空幻灯片也必须有记录。
- 只提取到标题、图片占比高、包含 SmartArt/流程图/大量连接线或图表缺少可读数据时，渲染单页并按需 OCR/VLM。
- 每个 shape 必须被提取、描述、忽略并记录理由，或明确标记不支持/失败。

### 5.5 Markdown 与纯文本

- Markdown 直接进行 UTF-8/YAML front matter/AST 解析，保留标题树、段落、列表、引用、代码块、表格、图片和链接。
- 代码块和表格不得为了固定 token 长度被强行拆开。
- 纯文本完成编码检测、换行规范化和按标题/段落切分，并保留行号定位。
- Markdown 和纯文本不需要经过 Docling。

### 5.6 图片与链接

- 图片使用 OCR 作为文本基线，VLM 作为可选语义描述层，二者来源必须区分。
- 链接抓取涉及 SSRF、重定向、动态页面和内容快照，应单独建立安全设计；不能与本轮文件解析无条件合并。

## 6. 质量审计语义

`parse_status` 继续描述运行状态，`parse_quality` 描述当前证据支持的内容质量：

- `complete`：要求核账的源 unit 全部有明确状态，不存在 failed unit；有效文本 unit 均形成可定位正文。
- `partial`：存在未覆盖、unsupported 或 failed 的必要 unit，但仍有可消费内容。
- `unknown`：历史资料或旧 parser 没有足够审计证据。

完整性必须标明 `coverage_mode`。例如 `coverage_mode = text` 只表示文本覆盖完整，不代表图表关系或图片语义已被理解。完整 diagnostics 应记录总 unit、已核账 unit、native/fallback/OCR/visual-only/failed 数量和列表；SQLite 保留摘要，完整 IR/质量报告可作为可重建本地派生 artifact 保存。

## 7. 结构化切块与去重

不同格式不得统一无条件调用一次 `HybridChunker`：

| 格式 | 父节点 | 典型子 chunk |
| --- | --- | --- |
| PDF | 页面或小节 | 段落组合、表格、视觉说明 |
| DOCX | 标题 section | 段落组、完整表格、图片说明 |
| PPTX | 整张幻灯片 | 正文、notes、表格、图片说明 |
| Markdown | 标题 section | 段落、列表、代码块、表格 |
| 图片 | 整张图片 | OCR 区域、视觉描述 |

子 chunk 可优先控制在 300-700 tokens，父节点可控制在 1,000-2,500 tokens；表格、代码块和短幻灯片优先保持语义完整。

每个 chunk 后续至少应能表达：

- `parent_unit_id`、页/幻灯片/section 定位和 `heading_path`。
- `content_role`，包括 body、table_of_contents、table、code、speaker_notes、visual_description 等。
- `parser_sources`、`fallback_used` 和 `content_hash`。

入库前执行页眉页脚和模板清理、精确内容哈希去重、重复目录/导航页近似去重。目录块普通问答默认降权或排除，只在课程结构问题中启用。

## 8. 目标检索策略

### 8.1 查询理解与任务路由

1. 识别“详细一点”“每一节讲解版”“继续”等模糊追问，仅对此类请求调用模型结合最近对话改写为独立查询。
2. 将请求分类为局部事实、跨章节、全文覆盖、课程结构、比较或生成任务。
3. 查询改写失败时，降级为原问题与最近用户消息的确定性组合。

### 8.2 局部事实问答

建议在保留 Chroma 的前提下逐步演进：

```text
Chroma Dense candidates
+ SQLite FTS5/BM25 candidates
  -> RRF 融合
  -> 精确/近似去重
  -> 页码、章节、资料多样性
  -> 可选 reranker
  -> Top 6-10
  -> 展开父 unit 上下文
```

第一阶段可先实现 dense 召回池扩大、目录降权、去重、多样性和父上下文；FTS5、独立 reranker endpoint 和学习型重排可以在后续子项目接入。任何新增核心依赖或模型用途都必须更新 ADR/配置契约。

### 8.3 跨章节与全文任务

- 跨章节问题拆成子查询，按章节分别召回、聚合并执行章节覆盖检查。
- 全文总结、逐节讲解、全部知识点、整章出题和完整学习计划不得走普通 Top-K。
- 总 token 在限额内时按文档顺序读取全部父节点；超限时按 section/page 分批 map，再 reduce。
- 课程结构问题优先使用 outline/heading 元数据，允许目录块参与。
- 全文或批次任一必要阶段失败时，不得声称已覆盖完整材料。

## 9. 前端透明度与可观测性

资料区需要区分运行状态与内容质量，例如：

- 已解析 · 文本完整。
- 已解析 · 使用若干页文本补偿。
- 已解析 · 部分内容缺失。
- 已解析 · 含未理解的视觉内容。

问答区需要区分：

- 资料选择范围：当前课程全部已解析资料。
- 本次实际上下文：N 个相关片段；或全文覆盖 X/Y 个 unit。

日志和诊断必须记录 parser/profile/version、逐单元统计、fallback 原因、检索候选数、去重前后数量、最终页/章节分布和任务路由；不得记录完整资料正文、用户问题、prompt 或 API key。

## 10. 建议拆分与实施顺序

### P0：质量基线与 shadow 验证

- 固定 Chap7 PDF 回归样本，并补充 DOCX、PPTX、Markdown 小型夹具。
- 新解析器只生成质量报告，不写数据库、不更新 Chroma。
- 对比源单元数、文本覆盖、耗时、内存和旧/new chunk 差异。

### P1：统一解析基础与 PDF 参考实现

- 轻量 IR、QualityAuditor、StructuralChunker 和兼容适配器。
- PyMuPDF 快速路径、Docling 按页增强、OCR 按页恢复。
- 候选结果安全切换、parser version 和回滚能力。

### P2：原生格式解析器

- Markdown AST。
- DOCX OOXML 顺序解析。
- PPTX slide/shape/notes 解析。
- 各格式独立审计规则和回退触发条件。

### P3：结构化索引与迁移

- parent-child、content role/hash 和定位元数据。
- 可选 FTS5 派生索引。
- 历史引用兼容、按资料 dry-run/重解析和索引重建。

### P4：自适应检索

- 模糊追问改写、任务路由、目录治理、去重和多样性。
- Dense + lexical 融合、可选 reranker 和父上下文。
- 全文/跨章节覆盖执行器。

### P5：前端质量展示与历史迁移

- 资料质量和 fallback/partial 提示。
- 实际上下文范围提示。
- 新上传默认启用后，再显式迁移历史资料；不得未经确认自动全量重解析。

每个阶段都必须形成独立设计、实现计划、测试、文档和 Conventional Commit；数据库、公共 API/schema、核心依赖和架构变化按项目规则由负责人确认。

## 11. 验收标准

### 11.1 兼容性

- feature flag 关闭时，上传、解析、问答、生成和学习计划行为与当前版本一致。
- 新解析失败或索引失败时，旧 chunk/向量仍可服务。
- 上层消费者无需 import 新 parser/IR 类型。
- 旧前端可忽略新增字段并继续工作。
- 历史引用在重解析后仍能展示资料名、位置和命中快照。

### 11.2 解析质量

- 所有源 unit 均被核账，必要 unit 无静默缺失。
- Chap7 PDF 59 页全部有明确状态；有效文本页最终覆盖率为 100%。
- `complete` 不再由 Docling `success` 或 chunk 非空直接决定。
- fallback、OCR、visual-only 和 failed unit 可从 diagnostics 查询。

### 11.3 检索质量

- 最终上下文不被重复目录块占满。
- “每一节的详细讲解版”能恢复前文主题，并覆盖 7.1-7.7 或明确指出缺失章节。
- 局部问题不会因全文路由产生不必要的全材料成本。
- 全文任务具有可验证的材料/章节/unit 覆盖记录。
- 所有引用可以定位回页、幻灯片、section 或行号。

## 12. 风险与触发条件

- 多解析器会增加依赖、包体和维护成本，必须通过按需触发避免所有引擎整份重复执行。
- VLM、OCR、reranker 和后台长任务需要独立资源预算与用途级模型配置。
- 完整 IR、版本化 chunk 或 FTS5 会改变数据和索引契约，实施前必须补 ADR、migration 和回滚策略。
- 同步解析无法长期承载复杂材料；当单文件解析稳定超过可接受请求时延或需要批量迁移时，应先处理后台任务技术债 TD-009。
- 只有在 shadow 回归证明覆盖率、耗时和兼容性满足标准后，才能把新解析器设为默认。
