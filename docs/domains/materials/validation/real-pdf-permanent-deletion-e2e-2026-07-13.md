# 真实 PDF 永久删除端到端验证（2026-07-13）

## 结论

通过。两条完整链路均使用真实 PDF、真实 Docling 解析、真实 SQLite、真实 Chroma `PersistentClient` 和实际 HTTP API；资料或文件夹删除后，资料记录、SQLite chunk、Chroma 向量、上传文件与暂存目录均不存在。

测试不会触碰开发数据库、开发上传目录或开发 Chroma collection：全部在临时 SQLite、临时上传目录和临时 Chroma 目录中执行，结束后已清理。

## 输入与环境

- 输入文件：`testfile/Chap7 物理层.pdf`
- 文件大小：3,634,087 bytes
- SHA-256：`BADB0E5A2B00FADE6164E556E8F81849C0DD6F29D04A864C16F9EFD317E6AB49`
- HTTP：FastAPI `TestClient`，覆盖注册、建课、上传、解析、移入文件夹与删除 API。
- 解析：项目真实 `DoclingParser`，PDF 文本优先、CPU 单线程、batch 为 1。
- 向量库：项目真实 `LlamaIndexChromaRagIndex` + 临时 Chroma `PersistentClient`。
- 嵌入：本地确定性 16 维 embedding，仅替代外部 Embedding API；用于验证真实 Chroma 写入、metadata 更新和删除，不评估语义检索质量。

`page_count = 59` 是 PDF 文档总页数；解析日志中的 `pages = 47` 是实际产生 chunk 的页数。

## 场景与结果

| 场景 | 解析结果 | 删除后验证 | 结果 |
| --- | --- | --- | --- |
| 上传真实 PDF → 解析 → 删除单份资料 | 59 页、49 chunk、49 Chroma 向量 | `CourseMaterial = 0`、`MaterialChunk = 0`、Chroma 向量 = 0、上传文件不存在、GET 资料返回 404 | 通过 |
| 上传真实 PDF → 解析 → 创建文件夹 → 移入资料 → 删除文件夹 | 59 页、49 chunk、49 Chroma 向量；移动后 49 条向量的 `folder_id` 全部更新 | `MaterialFolder = 0`、`CourseMaterial = 0`、`MaterialChunk = 0`、Chroma 向量 = 0、上传文件不存在、资料/文件夹列表为空、`.trash` 不存在 | 通过 |

## 性能记录

| 指标 | 单资料删除场景 | 文件夹删除场景 |
| --- | ---:| ---:|
| Docling 解析 | 117,392 ms | 106,554 ms |
| Chroma 索引 49 chunk | 85.58 ms | 48.88 ms |
| Chroma 删除向量 | 35.43 ms | 31.25 ms |
| HTTP 删除请求 | 62.99 ms | 48.03 ms |

总端到端时间为 224,592 ms。真实 PDF 的 Docling 解析是主要耗时；文件、数据库和 Chroma 删除均在毫秒级完成。

## 关键运行日志

```text
2026-07-13 01:34:34 | INFO  | materials.upload | 上传成功 | material=mat_3bf... file=Chap7 物理层.pdf size=3634087 cost_ms=17.85
2026-07-13 01:36:31 | INFO  | rag.index        | 索引成功 | collection=real_pdf_delete_e2e chunks=49 cost_ms=85.58
2026-07-13 01:36:31 | INFO  | materials.parse  | 解析成功 | material=mat_3bf... pages=47 chunks=49 cost_ms=117382.23
2026-07-13 01:36:31 | INFO  | rag.index        | 索引批量删除成功 | collection=real_pdf_delete_e2e materials=1 cost_ms=35.43
2026-07-13 01:36:31 | INFO  | http.request     | DELETE /api/v1/materials/mat_3bf... -> 200 | cost_ms=62.99
2026-07-13 01:36:31 | INFO  | http.request     | GET /api/v1/materials/mat_3bf... -> 404 | cost_ms=10.28

2026-07-13 01:36:31 | INFO  | materials.upload | 上传成功 | material=mat_e2a... file=Chap7 物理层.pdf size=3634087 cost_ms=29.21
2026-07-13 01:38:18 | INFO  | rag.index        | 索引成功 | collection=real_pdf_delete_e2e chunks=49 cost_ms=48.88
2026-07-13 01:38:18 | INFO  | materials.parse  | 解析成功 | material=mat_e2a... pages=47 chunks=49 cost_ms=106542.06
2026-07-13 01:38:18 | INFO  | rag.index        | 索引目录更新成功 | material=mat_e2a... vectors=49 cost_ms=34.23
2026-07-13 01:38:18 | INFO  | rag.index        | 索引批量删除成功 | collection=real_pdf_delete_e2e materials=1 cost_ms=31.25
2026-07-13 01:38:18 | INFO  | http.request     | DELETE /api/v1/material-folders/fld_51c... -> 200 | cost_ms=48.03
2026-07-13 01:38:18 | INFO  | http.request     | GET /api/v1/materials/mat_e2a... -> 404 | cost_ms=6.60
```

## 验收边界

- 已验证：真实 PDF 文件、真实 Docling、真实 chunk 持久化、真实 Chroma 写入与 metadata 移动、资料物理删除、文件夹级联物理删除、SQLite 清理、文件系统清理和暂存目录清理。
- 未验证：外部 Embedding 服务的网络可用性和真实语义召回质量；本次使用本地确定性 embedding，避免测试依赖 API key 和外部网络。
