# Study Mode validation artifacts

本目录用于记录 Study Mode 的真实文件回归、手工验收和模型效果验证摘要。

## 可提交内容

- 人工整理后的验收报告，例如 `report.md`、`final-report.md`。
- 脱敏后的复现条件、关键结论、哈希、问题清单和后续行动。

## 仅保留本地

`real-e2e-physical-layer-*` 目录下的本地中间产物默认不提交，包括：

- JSON 响应、任务测试题 Markdown、PDF 导出件。
- SQLite / DB 文件。
- 后端日志、app logs、`*.log`、`*.jsonl`。
- Chroma 索引目录、uploads 目录和其他运行时缓存。

如需提交新的真实 E2E 证据，优先把原始产物整理成脱敏摘要或最终报告，再确认 `.gitignore` 是否需要补充例外规则。
