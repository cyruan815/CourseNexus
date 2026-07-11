# 计网第七章 PDF 解析漏页问题分析

## 背景

- 日期：2026-07-12
- 触发用例：`我要两天学完计网这门课的第七章节，今天是2026年7月12日`
- 测试资料：`D:\大二下课程\计算机网络\课件\Chap7 物理层.pdf`
- 关联报告：`docs/planning/phase-1-validation/net-chap7-physical-real-model-preview-after-quality-2026-07-12.md`

本问题来自一次真实模型回归测试。测试中，`study_plan_parser` 与 `study_plan_generator` 都已成功调用真实模型；学习计划最终失败的直接原因是 study-mode 的每日时长校验不通过。但进一步看材料输入，会发现更大的隐患是：PDF 资料没有被完整解析，模型只拿到了第七章的一小部分内容。

## 总体结论

这是一个资料解析链路问题，根因不在 study-mode。

严格归属上，它属于：

- `backend/app/integrations/parsers/docling_parser.py`
- `backend/app/modules/materials/service.py`
- 后续可能涉及 `material_context` 的上下文质量诊断

study-mode 的职责不是修复 OCR 或 PDF 分页解析，但它应该在消费资料上下文时做防护：

- 发现资料上下文明显不完整时返回 warning；
- 不应在输入资料缺章时声称“学完整章”；
- 对“学完第七章”这类完成型目标，应把资料覆盖不足暴露给前端或用户。

所以建议拆成两个任务：

- 根因修复：materials/parser 负责。
- 消费侧防护：study-mode 负责。

## 现象

本次测试中，PDF 解析服务最终把资料标记为 `parsed`，但实际只产生了 15 个 chunk。

报告中的关键信息：

```json
{
  "parse_status": "parsed",
  "parse_error": null,
  "chunk_count": 15,
  "formula_placeholder_count": 1,
  "pages_with_chunks": [
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "32"
  ]
}
```

PDF 目录里明确出现：

- `7.1 物理层概述`
- `7.2 数据通信的基础知识`
- `7.3 传输介质`
- `7.4 调制技术和编码技术`
- `7.5 复用技术`
- `7.6 物理层互连设备`
- `7.7 物理层的安全隐患`

但实际进入模型上下文的 chunk 基本只覆盖：

- 物理层概述；
- 数据通信基本概念；
- Nyquist / Shannon 公式；
- 一页数字数据编码技术。

缺失或严重不足的部分包括：

- `7.3 传输介质`
- `7.4 调制技术和编码技术` 的大部分内容
- `7.5 复用技术`
- `7.6 HUB / 物理层互连设备`
- `7.7 物理层安全隐患`

测试时终端还出现了 Docling/RapidOCR 的内存相关错误，例如：

```text
Stage preprocess failed for run 1, pages [17]: std::bad_alloc
Stage preprocess failed for run 1, pages [18]: std::bad_alloc
...
onnxruntime.capi.onnxruntime_pybind11_state.RuntimeException:
Status Message: bad allocation
```

这些错误说明 PDF 后半部分在预处理或 OCR 阶段出现了内存分配失败。当前代码没有把这些失败页记录到数据库，也没有把“部分解析成功”与“完整解析成功”区分开。

## 当前数据流

这次链路可以拆成下面几步：

```text
PDF 文件
  -> DoclingParser.parse()
  -> ParsedDocument(chunks)
  -> materials.service.parse_material()
  -> material_chunks 入库
  -> material.parse_status = parsed
  -> material_context 读取 chunks
  -> study_plans planner map/reduce
  -> 模型基于不完整 chunks 生成学习计划
```

关键问题在中间两层：

1. `DoclingParser.parse()` 当前只返回 `ParsedDocument(chunks=...)`。
2. `materials.service.parse_material()` 只要 chunks 非空，就把资料标记为 `parsed`。

也就是说，现在系统的状态表达只有：

- `parse_failed`：完全失败。
- `parsed`：有 chunk。

它缺少第三种很重要的状态或诊断：

- `parsed_with_warnings`：有 chunk，但解析不完整、存在失败页、存在 OCR 失败或页码断层。

## 为什么这不属于 study-mode 根因

study-mode 的输入不是原始 PDF，而是 material context。

study-mode 看到的是这样的数据：

- chunk id
- chunk index
- page
- heading
- content_text
- material_id

它并不知道：

- PDF 总页数是多少；
- 哪些页 OCR 失败；
- 哪些页预处理失败；
- 解析器是否吞掉了后半部分页面；
- `parse_status=parsed` 是否代表完整解析。

因此，study-mode 在这次测试中“没生成 7.3 到 7.7 的细计划”，不是因为它主动忽略了这些章节，而是因为这些章节没有进入上下文。模型无法从不存在的上下文中可靠生成知识点。

更准确地说：

- materials/parser 是资料真实性和完整性的生产者；
- material_context 是资料上下文的搬运和组织者；
- study-mode 是资料上下文的消费者。

生产者没有提供完整上下文，也没有提供“不完整”的诊断信号，消费者就无法可靠判断自己拿到的是全量资料还是残缺资料。

## 为什么 study-mode 仍然要做防护

虽然根因不在 study-mode，但 study-mode 是用户最终看到学习计划的地方。如果它完全信任不完整资料，就会出现产品层面的误导。

例如本次目标是“学完计网第七章”，用户期待覆盖第七章全部内容。但模型实际只拿到少量 chunk，仍可能生成一个看起来完整的计划标题，甚至在描述中出现“章节综合测试，涵盖所有物理层知识点”。

这会造成三层风险：

1. 用户以为计划覆盖了完整第七章。
2. 模型计划实际只覆盖被解析出来的页面。
3. 后续任务、测验、讲义都会沿用这份不完整上下文，错误会被继续放大。

所以 study-mode 应做的是消费侧防护，而不是解析修复：

- 检查资料上下文是否明显稀疏；
- 检查页码是否出现大段断层；
- 检查目标中的章节范围与 chunk heading/页码是否匹配；
- 在 preview 返回 warnings；
- 对完成型目标标注“资料覆盖不足，计划可能不完整”。

## 这次对计划生成的具体影响

Generator map 阶段实际抽取了 6 个知识单元：

- 物理层概述与功能；
- IEEE802.3 10BaseT 与 RJ45；
- 信息、数据、信号与码元；
- 信道容量：奈奎斯特与香农公式；
- 数字数据编码技术；
- 教学内容与章节结构。

这些知识单元都来自已经解析出的 chunks。它们本身不算乱编，但明显不足以代表完整第七章。

因此本次输出暴露了两个问题：

1. 计划校验问题：候选计划第 1 天时长不足，被 `validate_preview()` 拒绝。
2. 资料覆盖问题：输入上下文缺失第七章后半内容，导致即使通过校验，计划也不应被认为是完整章节学习计划。

第 1 个是 study-mode 生成质量问题。

第 2 个是 materials/parser 解析完整性问题，并需要 study-mode 做提示。

## 建议改动一：materials/parser 记录解析诊断

建议给资料解析结果增加诊断信息，至少能表达：

- PDF 总页数；
- 成功产生 chunk 的页码；
- 失败页码；
- OCR 或 preprocess 失败类型；
- 是否存在明显页码断层；
- 是否存在公式未解析占位符。

可以考虑新增类似字段：

```json
{
  "parse_status": "parsed_with_warnings",
  "parse_diagnostics": {
    "page_count": 60,
    "pages_with_chunks": [2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 32],
    "missing_page_ranges": ["17-31", "33-60"],
    "failed_pages": [17, 18, 19],
    "warnings": [
      {
        "code": "OCR_MEMORY_ERROR",
        "message": "RapidOCR bad allocation during preprocess"
      }
    ]
  }
}
```

如果短期不想改数据库，也可以先在 service 层返回 transient diagnostics，或把 warnings 暂时放在 material detail response 中。但长期看，解析诊断最好落库，因为后续 study-mode、RAG、任务生成、讲义生成都会依赖它。

## 建议改动二：DoclingParser 支持降级解析

当前 `DoclingParser` 是一次性把文件交给 `DocumentConverter()`，然后 chunk。

建议增加降级策略：

1. 优先尝试正常 Docling 解析。
2. 如果出现 OCR / preprocess 内存错误：
   - 降低 OCR 压力；
   - 分页或分段处理；
   - 对失败页单独重试；
   - 必要时跳过 OCR，只保留可提取文本；
   - 把失败页写入 diagnostics。
3. 如果最终有 chunk 但存在失败页，状态不能静默等同于完整 `parsed`。

这部分属于 parser 集成层，不应该塞进 study-mode。

## 建议改动三：materials.service 区分完整成功和部分成功

当前 `parse_material()` 逻辑大致是：

```text
parser.parse()
  -> 有 chunks
  -> 写 material_chunks
  -> material.parse_status = parsed
```

建议改成：

```text
parser.parse()
  -> 有 chunks 且无 warnings
  -> parse_status = parsed

parser.parse()
  -> 有 chunks 但有 warnings / failed_pages / missing ranges
  -> parse_status = parsed_with_warnings
  -> parse_diagnostics_json 写入诊断

parser.parse()
  -> 无 chunks 或关键错误
  -> parse_status = parse_failed
```

这样下游就能知道资料是否可信。

## 建议改动四：material_context 暴露上下文质量

study-mode 不应该自己重新分析数据库里的所有 chunk 完整性。更好的边界是由 material_context 返回上下文质量摘要。

例如：

```json
{
  "chunks": [],
  "context_quality": {
    "has_warnings": true,
    "warning_codes": ["MATERIAL_PARSE_INCOMPLETE"],
    "materials": [
      {
        "material_id": "mat_xxx",
        "parse_status": "parsed_with_warnings",
        "pages_with_chunks": [2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 32],
        "missing_page_ranges": ["17-31", "33-60"]
      }
    ]
  }
}
```

这样 study-mode 只需要消费 warning，而不是直接耦合 materials 内部细节。

## 建议改动五：study-mode 在 preview 中返回 warning

study-mode 可以做一个轻量防护：

- 如果目标包含“学完/掌握/完成”等完成型意图；
- 如果材料上下文有 `MATERIAL_PARSE_INCOMPLETE`；
- 则 preview 返回 warning。

示例：

```json
{
  "warnings": [
    {
      "code": "MATERIAL_CONTEXT_INCOMPLETE",
      "message": "当前资料解析可能不完整，计划仅覆盖已解析内容。建议重新解析资料后再生成完整章节计划。",
      "material_ids": ["mat_xxx"]
    }
  ]
}
```

如果当前 API schema 不想马上改，也可以先在 coverage 或 metadata 中带出。但从产品角度看，warning 应该是 preview 的一等字段。

## 是否应该阻止生成

不建议一开始就全部阻止。

更合理的分级：

- 轻微断层：允许生成，但返回 warning。
- 明显大段漏页：允许生成“基于已解析内容的计划”，但不能声称完整覆盖。
- 完成型目标且缺失范围很大：建议前端提示用户重新解析，或者让用户确认“继续基于部分资料生成”。
- 完全无 chunk：直接阻止生成，返回无可用资料。

本次属于“明显大段漏页”，因为 chunk 页码从 16 跳到 32，后续很多页面没有进入上下文。

## 推荐拆分任务

### Task A：materials/parser 解析诊断

目标：

- 记录 PDF 总页数、成功页、失败页、页码断层、OCR 错误；
- 支持 `parsed_with_warnings` 或等价诊断；
- 解析失败不是只有全失败一种状态。

验收：

- 用本次 `Chap7 物理层.pdf` 解析后，系统能明确显示后半部分页面未完整解析；
- material detail 或 diagnostics API 能看到 `missing_page_ranges`；
- 不再把部分解析静默当成完整成功。

### Task B：study-mode 消费侧 warning

目标：

- preview 读取 material_context 的上下文质量；
- 当完成型目标遇到资料解析不完整时，在 preview 返回 warning；
- prompt 中明确告诉模型“只基于已解析资料生成，不得声称覆盖缺失章节”。

验收：

- 本次用例重新生成时，即使模型能产出计划，也必须返回 `MATERIAL_CONTEXT_INCOMPLETE` warning；
- 计划标题或描述不得声称“完整覆盖第七章”；
- 报告中能看到 warning 与涉及 material。

### Task C：Docling/RapidOCR 降级解析

目标：

- 降低大 PDF 或图片页 OCR 内存失败概率；
- 失败页可以单独重试或跳过 OCR 保留文本；
- 对失败页给出可追踪诊断。

验收：

- 本次 PDF 的 chunk 覆盖页数明显提升；
- 如果仍有失败页，失败页被记录，而不是静默消失。

## 推荐优先级

优先级建议：

1. 先做 Task B：study-mode warning。成本低，能立即避免误导用户。
2. 再做 Task A：materials/parser 诊断。它是长期正确边界。
3. 最后做 Task C：Docling/RapidOCR 降级解析。它技术不确定性最高，但能从根上提高资料质量。

这样安排的原因是：降级解析可能涉及第三方库、PDF 分页处理和 OCR 配置，风险较高；而 warning 可以先把风险显性化，让用户知道当前计划是“基于部分资料”的。

## 一句话总结

这次不是 study-mode 把第七章后半部分“漏学了”，而是资料解析层没有把后半部分稳定转成 chunk；study-mode 当前又缺少“输入资料不完整”的感知能力，所以最终表现成了计划内容覆盖不足。根因在 materials/parser，study-mode 需要补消费侧 warning 和防误导机制。
