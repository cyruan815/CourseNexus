# Contracts v0.1

## 前后端契约基线

- 基础设施阶段的前端是最小集成验证工作台；已落地接口、请求体和响应字段以 [frontend-integration.md](frontend-integration.md) 为前端接入入口。
- 前端提交字段、后端返回字段统一使用 `snake_case`。
- 成功响应统一包含 `data` 和 `meta`。
- 错误响应统一包含 `error.code`、`error.message`、`error.details` 和 `meta.request_id`。
- 前端根据 HTTP status 与 `error.code` 决定交互，不解析中文错误文案。
- 异步操作返回资源 ID 与状态，前端通过详情或状态接口刷新。
- 空列表返回 `[]`，不使用 `null` 表示空集合。
- `401` 触发重新登录；`403` 展示无权限；`404` 可用于不暴露他人数据是否存在。

## 模块间契约基线

- 资料模块只把 `parse_status = parsed` 的资料暴露给检索和 Agent。
- 问答、生成和学习计划不得直接读取资料表或 chunk 表，必须通过 `material_context.resolve_context()` 获取资料上下文。
- Agent 模块不得跨课程混用上下文。
- 无资料命中时，Agent 必须返回 `answer_type = no_source`，并禁止伪引用。
- AI 生成内容统一写入 `AIGeneratedContent`，通过 `content_type` 区分用途。
- 保存为笔记统一使用 `content_type = note`，不新增 Note 对象。
- 学习计划模块只生成计划和任务结构，不提前生成讲义或任务测试题。
- 今日讲义和任务测试题按需生成，并绑定 `study_subtask_id`。
- 任务完成状态更新后必须同步一级任务状态和 `CheckinRecord`。
- 首页今日待办和首页大日历是只读聚合入口，不提供创建、编辑或重新生成计划能力。

## 跨模块数据引用原则

- 跨模块引用 ID 时，必须同时保证当前用户有权访问被引用资源。
- `SourceCitation` 必须保存 `material_id`、`material_name`、页码或页序号、`hit_text`。
- `material_name` 是快照字段，避免资料改名后历史引用展示异常。
- 历史引用定位失败时，前端仍可展示快照文本和定位失败提示。
- `StudySubTask.related_material_ids_json` 只能引用当前课程下当前用户可访问的资料。

## 资料上下文契约

`MaterialScope` 是前端工作台、问答、生成和计划基础能力共用的资料范围结构：

```json
{
  "include_all_parsed_materials": true,
  "folder_ids": [],
  "material_ids": []
}
```

规则：

- 默认 `include_all_parsed_materials = true`，返回当前课程下全部 `parsed` 且未删除资料的 chunk。
- 当 `include_all_parsed_materials = false` 时，`material_ids` 和 `folder_ids` 表示显式选择范围。
- 显式传入 `material_ids` 时，后端必须校验这些资料属于当前用户、当前课程、已解析且未删除；否则返回 `NOT_FOUND`。
- 未解析、解析失败和已删除资料不得进入上下文结果。

`resolve_context()` 返回的 `ContextChunk` 最小字段：

```json
{
  "material_id": "mat_123",
  "chunk_id": "chk_123",
  "material_name": "notes.md",
  "page": null,
  "page_index": null,
  "heading": "Intro",
  "content_text": "Alpha"
}
```

当前范围没有可用 parsed chunk 时，返回 `no_parsed_material = true`，调用方应进入 no source 或无资料兜底流程。

## 请求 / 响应示例格式

Agent 提问请求示例：

```json
{
  "course_id": "crs_123",
  "conversation_id": null,
  "question": "这份课件的核心概念是什么？",
  "material_scope": {
    "include_all_parsed_materials": true,
    "folder_ids": [],
    "material_ids": []
  },
  "source_page": "course_detail"
}
```

Agent 回答响应示例：

```json
{
  "data": {
    "answer_text": "回答正文",
    "answer_type": "grounded",
    "created_message_id": "msg_123",
    "source_citations": [
      {
        "material_id": "mat_123",
        "material_name": "chapter-01.pdf",
        "page": 3,
        "page_index": null,
        "hit_text": "命中文本片段"
      }
    ]
  },
  "meta": {
    "request_id": "req_123",
    "server_time": "2026-07-09T12:00:00+08:00",
    "api_version": "v1"
  }
}
```

## 契约变更规则

- API 契约变更前先更新本分区，再实现。
- 新增字段必须说明默认值、是否可为空和前端展示兜底。
- 修改状态枚举必须同步状态流转、错误处理和验收口径。
- 权限规则变更必须明确影响哪些资源和接口。
- 引用来源字段不可随意弱化；资料名快照、页码或页序号、命中文本片段是 v0.1 最小展示契约。

## 向后兼容要求

- 新增可选字段时，前端不得因未知字段失败。
- 后端删除或重命名字段前，应提供迁移期兼容字段。
- 枚举新增时，前端必须展示兜底状态。
- 错误码新增时，前端默认按通用错误处理。
- 字段类型变化、枚举语义变化、权限语义变化视为破坏性变更，必须单独评审。
