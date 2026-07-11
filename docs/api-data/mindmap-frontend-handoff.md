# Mindmap 前后端交接文档

## 交接范围

后端生成并保存思维导图结构及 Markmap Markdown；前端负责使用 Markmap 渲染。当前没有 `.md` 文件和静态资源 URL。

## 数据位置

```text
数据库表：ai_generated_contents
记录类型：content_type = mindmap
结构字段：content_json
Markdown 字段：content_json.markmap_markdown
引用关系：nodes[].source_citation_ids -> source_citations[].id
```

前端不能访问数据库，应通过 API 获取以上字段。

## 接口

所有接口要求 Bearer token，响应使用项目统一 `{ "data": ..., "meta": ... }` 包装。

### 生成导图

```http
POST /api/v1/courses/{course_id}/generations
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "content_type": "mindmap",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "parameters": {
    "center_topic": "操作系统",
    "max_depth": 5,
    "max_nodes": 80,
    "include_cross_links": true
  }
}
```

### 获取课程生成历史

```http
GET /api/v1/courses/{course_id}/generated-contents
Authorization: Bearer <token>
```

前端可按 `content_type === "mindmap"` 筛选导图记录。

### 获取生成详情

```http
GET /api/v1/generated-contents/{generated_content_id}
Authorization: Bearer <token>
```

建议历史列表只负责选择记录，进入导图页面后调用详情接口获取完整内容。

## 成功数据示例

```json
{
  "data": {
    "id": "generated-content-id",
    "content_type": "mindmap",
    "title": "知识导图：操作系统",
    "content": null,
    "generation_status": "completed",
    "content_json": {
      "schema_version": "1.0",
      "renderer": "markmap",
      "root_node_id": "node_001",
      "nodes": [
        {
          "id": "node_001",
          "label": "操作系统",
          "summary": "操作系统核心知识结构",
          "level": 1,
          "source_citation_ids": []
        },
        {
          "id": "node_002",
          "label": "进程管理",
          "summary": "进程与调度相关知识",
          "level": 2,
          "source_citation_ids": ["citation-id"]
        }
      ],
      "edges": [
        {
          "from": "node_001",
          "to": "node_002",
          "relation": "child"
        }
      ],
      "markmap_markdown": "- 操作系统\n  - 进程管理"
    },
    "error_code": null,
    "source_citations": [
      {
        "id": "citation-id",
        "material_id": "material-id",
        "chunk_id": "chunk-id",
        "material_name": "操作系统.pdf",
        "page": "12",
        "page_index": 12,
        "hit_text": "进程是程序的一次执行过程。",
        "sort_order": 1
      }
    ]
  },
  "meta": {
    "request_id": "request-id"
  }
}
```

## 前端渲染步骤

1. 确认 `generation_status === "completed"`。
2. 确认 `content_json.schema_version === "1.0"`。
3. 读取 `content_json.markmap_markdown`。
4. 使用 `markmap-lib` 的 `Transformer` 转换 Markdown。
5. 使用 `markmap-view` 的 `Markmap.create` 渲染 SVG。
6. 在组件卸载或重新渲染前清理旧实例和 SVG 内容。

示例代码仅表示数据交接方式，前端应按项目组件规范封装：

```ts
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";

const transformer = new Transformer();

export function renderMindmap(svg: SVGSVGElement, markdown: string) {
  const { root } = transformer.transform(markdown);
  return Markmap.create(svg, { autoFit: true, duration: 300 }, root);
}
```

Markmap 负责 SVG 布局、展开收起、缩放和平移。前端不需要自行解析 `nodes/edges` 来重建主树。

## 引用展示

Markdown 中不包含引用标记。需要展示引用时：

1. 从当前业务节点读取 `source_citation_ids`。
2. 在顶层 `source_citations` 中按 `id` 查找引用详情。
3. 展示 `material_name`、`hit_text` 和页码。
4. 当 `page === null` 且 `page_index === 0` 时显示“页码未知”，不能显示“第 0 页”。

Markmap 默认只保留 Markdown 文本，不会自动把 SVG 节点映射回后端 `node_id`。第一阶段若只要求导图渲染，可不实现点击节点查看引用；若要求节点点击引用，需要前端在 Markmap 转换结果上附加节点标识，双方再单独确认可点击映射契约。

## 边类型

- `child`: 主树父子关系，已体现在 `markmap_markdown` 中。
- `related`: 跨分支关联，只存在于 `content_json.edges`。

Markmap 的标准树形渲染不会展示 `related` 边。第一阶段前端可以忽略该类型；不得把 related 边转换为额外父节点，否则会破坏树结构。

## 状态和错误处理

- `completed`: 可以渲染。
- `failed`: 不渲染，展示生成失败状态。
- `content_json === null`: 不渲染。
- `GENERATION_FAILED`: 模型或生成过程失败。
- `GENERATION_SCHEMA_INVALID`: 生成结果无法形成合法树或 Markdown。
- `MATERIAL_COVERAGE_INCOMPLETE`: 选定材料未被完整覆盖。
- HTTP 400 `NO_PARSED_MATERIAL`: 没有可生成的已解析材料。
- HTTP 422 `VALIDATION_ERROR`: 参数或内容类型非法。
- HTTP 404 `NOT_FOUND`: 课程、材料或记录不属于当前用户。

重复提交生成请求会创建不同的生成记录。前端应在请求进行时禁用重复提交按钮。

## 联调验收

- 前端能从生成响应或详情响应读取 Markdown 并渲染非空导图。
- 节点可以通过 Markmap 展开、收起，画布可以缩放和平移。
- 页面刷新后能通过详情接口恢复同一导图。
- failed 或空内容不会初始化 Markmap。
- Markdown 多层缩进可以正确显示层级。
- `related` 边不会被错误渲染成 child。
- 引用页码未知时不显示“第 0 页”。

## 后端代码落点

计划中的 Mindmap 实现位于：

```text
backend/app/modules/generation/generators/mindmap/schemas.py
backend/app/modules/generation/generators/mindmap/prompts.py
backend/app/modules/generation/generators/mindmap/generator.py
```

当前接口实现入口：

```text
backend/app/modules/generation/orchestrator/router.py
backend/app/modules/generation/orchestrator/service.py
backend/app/modules/generated_content/router.py
backend/app/modules/generated_content/schemas.py
```
