# Mindmap 生成模块

## 能力边界

G04 根据用户选定的全部已解析材料生成一棵带真实引用的知识树，同时生成可交给 Markmap 的 Markdown。后端不依赖 Markmap，不输出 HTML、SVG、坐标或展开状态。

权威数据是 `content_json.nodes` 和 `content_json.edges`。`content_json.markmap_markdown` 是由最终合法 child 树确定性生成的渲染投影。

## 代码入口

```text
backend/app/modules/generation/generators/mindmap/schemas.py
backend/app/modules/generation/generators/mindmap/prompts.py
backend/app/modules/generation/generators/mindmap/markdown.py
backend/app/modules/generation/generators/mindmap/generator.py
```

`generator.py:build_generator` 由 G01 registry 自动发现。模块只依赖 G01 contract、`ModelProvider`、material-context batch 和 coverage helper。

## 数据流

1. 参数在第一次模型调用前校验。
2. 每个材料批次调用一次 `ModelProvider.generate_structured`。
3. coverage helper 检查全部预期材料均被处理。
4. reduce 合并规范化 label，批次内 `local_key` 不跨批次共享。
5. 显式中心主题优先作为根，否则选择跨材料支持最多且最早出现的概念。
6. 本地代码构造单父 child 树，BFS 应用深度和节点数量限制并生成稳定 ID。
7. schema 校验唯一根、可达性、单父、连续 level、无自环/环和兄弟 label 唯一。
8. Markdown serializer 只遍历 child 边；G01 绑定真实引用并原子保存。

## 持久化

Markdown 固定保存到 `ai_generated_contents.content_json.markmap_markdown`，不创建 `.md` 文件。成功状态为 `generation_status="success"`。`nodes/edges` 是权威数据，Markdown 是派生渲染数据。

## 算法与预算

图校验和 Markdown 序列化时间复杂度均为 `O(V + E)`，空间复杂度为 `O(V + E)`。`V <= 200`、深度不超过 6；模型调用次数等于材料批次数。

标签会合并连续空白，并转义可能改变 Markdown 结构的反斜杠、星号、下划线、方括号、尖括号和井号。related 边保留在 `edges`，不进入 Markmap Markdown。

## 失败策略

- 参数非法：`VALIDATION_ERROR`，HTTP 422，不创建记录。
- 模型失败：`GENERATION_FAILED`。
- 空概念、非法图或非根缺少真实引用：`GENERATION_SCHEMA_INVALID`。
- 材料覆盖不完整：`MATERIAL_COVERAGE_INCOMPLETE`。

后三类保存失败记录，且 `content_json=null`、`source_citations=[]`，不保存部分导图。

## 测试

```powershell
python -m pytest tests/modules/generation/generators/mindmap -q
python -m pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
```

覆盖参数、图结构、Markdown、多批次 key 隔离、全部批次调用、稳定 BFS ID、引用以及 POST、历史和详情持久化。
