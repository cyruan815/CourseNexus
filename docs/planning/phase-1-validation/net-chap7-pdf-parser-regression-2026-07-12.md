# 计网第七章 PDF 解析完整性回归

## 1. 验证目标

验证 materials/parser 基础设施修复后，不再因默认 RapidOCR / ONNX 并行处理出现 `bad_alloc` 并静默漏掉 PDF 后半部分；同时验证解析完整性诊断能够写入 `CourseMaterial`。

本次不验证 material-context、study-mode 或学习计划生成行为。

## 2. 测试文件

- 本地路径：`testfile/Chap7 物理层.pdf`
- 文件大小：3,634,087 bytes
- 页数：59
- SHA-256：`BADB0E5A2B00FADE6164E556E8F81849C0DD6F29D04A864C16F9EFD317E6AB49`
- Git 规则：`testfile/` 通过 `.git/info/exclude` 仅在本地保留，PDF 未追踪、未暂存、未提交。

## 3. 修复前基线

学习计划开发者真实模型回归记录显示：

- `parse_status = parsed`
- `chunk_count = 15`
- `pages_with_chunks = [2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 32]`
- Docling/RapidOCR 从第 17 页起出现 `std::bad_alloc` / ONNX Runtime `bad allocation`
- Parser 没有检查 `ConversionResult.status/errors`，materials 无条件把非空 chunk 标记为 `parsed`

该结果缺少 7.3 至 7.7 的大部分内容。

## 4. 实施内容

### 4.1 Parser 资源策略

PDF 首轮使用 `pdf_text_first`：

- `do_ocr = false`
- `force_backend_text = true`
- `do_table_structure = false`
- `ocr_batch_size = 1`
- `layout_batch_size = 1`
- `table_batch_size = 1`
- `queue_max_size = 4`
- `num_threads = 1`
- CPU device

只有首轮零 chunk 时才使用相同资源限制的 `pdf_ocr_fallback`。

### 4.2 诊断契约

Parser 返回：

- conversion status 和 profile
- PDF 总页数、处理页、内容页、chunk provenance 页
- 失败页
- 稳定 warning code、组件、页码和 severity

Materials 保存：

- `parse_quality = unknown | complete | partial`
- `parse_diagnostics_json`
- 权威 `page_count`

`parse_status = parsed` 继续表达“存在可消费且成功索引的 chunk”，不再承担完整性语义。

## 5. 真实文件结果

在 `codex/pdf-parse-completeness` worktree 中，以真实 Docling 2.111.x、内存 SQLite、真实 LocalFileStorage 和 FakeRagIndex 执行：

```text
upload
-> DoclingParser
-> MaterialChunk 写入
-> FakeRagIndex 索引
-> CourseMaterial 诊断持久化
```

结果：

```json
{
  "seconds": 104.2,
  "parse_status": "parsed",
  "parse_quality": "complete",
  "page_count": 59,
  "chunks": 49,
  "profile": "pdf_text_first",
  "conversion_status": "success",
  "processed_count": 59,
  "processed_max": 59,
  "content_count": 59,
  "content_max": 59,
  "chunk_page_max": 59,
  "failed_pages": [],
  "warnings": []
}
```

与修复前相比：

- chunk 从 15 增加到 49；
- 从后半部分基本缺失变为 59/59 页均处理且均检测到内容；
- 没有触发 OCR fallback；
- 没有 `OCR_MEMORY_ERROR`、失败页或其他 Docling warning；
- 数据库明确保存 `parsed + complete`，而不是只保存 `parsed`。

## 6. 自动化测试

实施前基线：

```text
264 passed in 68.20s
```

最终全后端回归：

```powershell
pnpm backend:test
```

```text
275 passed in 28.26s
```

Focused materials/schema 回归：

```text
26 passed in 14.90s
```

Parser/materials 回归：

```text
35 passed in 12.12s
```

Migration 在一次性 SQLite 数据库完成：

```text
upgrade -> 20260709_0001 -> 20260712_0002
downgrade -> 20260709_0001
upgrade -> 20260712_0002
```

三次命令退出码均为 0，临时数据库随后删除。

另在 0001 数据库插入一条历史 `parse_status = parsed` 记录后升级到 0002，查询结果为：

```text
('parsed', 'unknown', None)
```

确认 migration 不会把没有诊断证据的历史资料误标为 `complete`。

## 7. 结论与限制

本次真实回归证明：该 PDF 的问题不是 3.6 MB 文件过大，而是文本型 PDF 被默认送入 OCR、表格与并行模型流水线造成的资源错误。文本优先和低资源 profile 已消除本用例的漏页与内存错误。

仍需注意：

- chunk 数和 `pages_with_chunks` 不能单独作为页面完整性分母，HybridChunker 可能合并跨页内容；应优先使用 `processed_pages`、`pages_with_content`、失败页和 conversion status。
- 当前文本优先 profile 关闭高级表格结构模型，能保留文字但不保证单元格级结构恢复。
- OCR fallback 当前整份重试；失败页局部 OCR 和跨页 chunk 合并需另立任务。
- 本次只生产、保存并暴露全局质量信号；material-context 和各业务消费者如何展示或拦截不在本次范围内。
