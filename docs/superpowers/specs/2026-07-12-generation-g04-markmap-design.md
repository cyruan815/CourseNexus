# G04 Mindmap Markmap 后端设计

## 状态

已于 2026-07-12 通过对话确认。本设计只实现 CourseNexus 的后端思维导图生成，不修改前端代码。前端使用 Markmap 完成交互式渲染。

## 目标

- 根据用户选定的全部已解析材料生成一棵有唯一根节点的知识树。
- 保留渲染器无关的 `nodes`、`edges` 和节点级真实引用。
- 额外生成 Markmap 可直接解析的 Markdown，降低前端接入成本。
- 将结构化图和 Markdown 一起保存到现有 `AIGeneratedContent.content_json`。
- 提供稳定的前后端数据契约，不生成本地文件、HTML、SVG 或坐标。

## 非目标

- 不实现 Markmap 前端组件。
- 不保存节点展开状态、坐标、缩放状态或用户编辑结果。
- 不新增 Mindmap、Node 或 Edge 数据表，不新增迁移。
- 不提供 `.md` 静态文件路径或文件下载接口。
- 不使用 Markmap、D3 或其他前端图形依赖作为后端依赖。

## 架构选择

采用“结构化 JSON 为权威数据，Markdown 为派生渲染数据”的双格式设计。

`nodes` 和 `edges` 用于图结构校验、节点引用绑定、未来编辑和渲染器替换；`markmap_markdown` 只由最终合法的 child 树确定性生成，供前端交给 Markmap。两者在同一次生成事务中保存，不允许出现 Markdown 与节点树版本不一致的状态。

## 数据流

1. 通用生成编排器解析 `content_type=mindmap` 的请求并交付全部材料批次。
2. Mindmap generator 对每个批次调用 `ModelProvider.generate_structured`，抽取局部概念、父子关系、相关关系和来源 chunk ID。
3. 本地 reduce 合并同义概念，选择唯一根节点，构造 child 树并按参数决定是否保留 related 边。
4. 本地校验保证唯一根、全部节点可达、非根节点单父、无环、无自环、层级连续、深度和节点数量合法。
5. 节点按稳定 BFS 顺序编号为 `node_001...node_N`，非根节点绑定至少一个真实范围内引用。
6. Markdown serializer 只遍历 `relation=child` 的边，将最终树转换为嵌套无序列表。
7. G01 编排器将节点引用替换为真实 `SourceCitation.id`，并将内容和引用原子保存。

## 请求参数

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

参数约束：

- `center_topic`: 可选，长度 1 到 120。
- `max_depth`: 默认 4，范围 2 到 6。
- `max_nodes`: 默认 80，范围 3 到 200。
- `include_cross_links`: 默认 `true`。

## 持久化契约

Markdown 不生成物理文件。固定存放位置为：

```text
数据库表：ai_generated_contents
内容类型：content_type = mindmap
数据库字段：content_json
JSON 路径：content_json.markmap_markdown
```

`content` 保持 `null`。成功记录的 `content_json` 格式为：

```json
{
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
      "source_citation_ids": ["cit_001"]
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
}
```

## Markdown 契约

- 使用嵌套无序列表，不使用 Markdown 标题层级。
- 每个节点占一行，格式为 `<缩进>- <label>`。
- 每深入一级增加两个 ASCII 空格。
- 只序列化 `child` 边；`related` 边保留在 `edges` 中，不进入 Markmap 树。
- 节点顺序与最终 child 邻接表的稳定顺序一致。
- 标签中的换行和连续空白归一为空格。
- 对可能改变列表结构的 Markdown 控制字符进行转义。
- 引用 ID 和节点 ID 不写入可见 Markdown；前端从 `nodes` 和顶层 `source_citations` 解析引用。
- Markdown 始终由已通过最终 schema 校验的树生成，模型不得直接提供最终 Markdown。

## API 契约

沿用现有接口，不新增路由：

```text
POST /api/v1/courses/{course_id}/generations
GET  /api/v1/courses/{course_id}/generated-contents
GET  /api/v1/generated-contents/{generated_content_id}
```

POST、历史和详情均通过现有 `GeneratedContentRead` 返回 `content_json` 和 `source_citations`。前端从 `data.content_json.markmap_markdown` 读取渲染输入。

参数非法返回 HTTP 422 且不创建记录；无可用材料返回 HTTP 400；模型、schema 或覆盖失败保存失败记录。失败记录的 `content_json=null`、`source_citations=[]`，前端不得尝试渲染。

## 前后端职责

后端负责生成、合并、图校验、稳定 ID、引用绑定、Markdown 序列化和持久化。前端负责安装 `markmap-lib` 与 `markmap-view`，解析 Markdown、创建 SVG、展开收起、缩放和平移，并根据节点引用展示来源。

前端不得依赖后端文件系统路径，也不得将 `markmap_markdown` 视为权威业务数据。需要节点信息或引用时，应读取 `nodes`、`edges` 和 `source_citations`。

## 测试策略

- schema 测试覆盖唯一根、可达性、单父、层级、悬空边、自环、环、多父、重复边、深度和数量限制。
- generator 测试覆盖全部批次、同义合并、稳定 BFS ID、裁剪、引用过滤和三类失败。
- Markdown serializer 测试覆盖任意深度、稳定顺序、空白归一、特殊字符转义，以及 related 边不进入 Markdown。
- API 测试覆盖 POST、历史、详情、失败记录和 `content_json.markmap_markdown` 的持久化一致性。
- 回归测试覆盖 G01、generated-content 和 material-context，不执行真实网络请求。

## 兼容性决定

原 G04 的渲染器无关结构继续保留，并仍是权威数据。本设计仅增加派生字段 `schema_version`、`renderer` 和 `markmap_markdown`，不把 Markmap 对象、HTML、SVG、坐标或交互状态写入后端。
