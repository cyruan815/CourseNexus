# 知识点清单学习进度设计

## 目标

知识点清单中的每个知识点可以标记为“已学习”或取消标记。已学习知识点使用绿色完成样式，清单顶部根据全部知识点显示已学习数量、总数、进度条和百分比。状态永久保存，刷新页面后仍然存在。

## 数据设计

不新增数据库表或数据库列。每个知识点继续保存在 `ai_generated_contents.content_json.items` 中，并增加布尔字段 `learned`：

```json
{
  "id": "kp_001",
  "sort_order": 1,
  "name": "奈奎斯特定理",
  "definition": "用于描述理想低通信道最高码元传输速率的定理。",
  "importance": "high",
  "related_section": "第七章 物理层",
  "learned": false
}
```

AI 输出模型不包含 `learned`，生成器在构造最终 `KnowledgeItem` 时统一写入默认值 `false`。历史记录缺少该字段时，后端和前端均按 `false` 处理。

## 后端更新边界

新增单项状态接口：

```http
PATCH /api/v1/generated-contents/{generated_content_id}/knowledge-items/{knowledge_item_id}/learning-state
Content-Type: application/json

{"learned": true}
```

接口只接受 `learned`，不接受名称、定义、重要程度等内容字段。服务层验证记录属于当前用户、类型为 `knowledge_list`、状态为 `success`、JSON 结构有效且知识点 ID 存在，然后复制并更新目标 item，写回完整 `content_json` 并更新 `updated_at`。错误分别使用现有 `NOT_FOUND`、`INVALID_GENERATED_CONTENT_TYPE`、`STATE_CONFLICT` 和 `GENERATED_CONTENT_SCHEMA_INVALID` 语义。

## 前端交互

`KnowledgeListResult` 接收 `generatedContentId`，在本地维护规范化后的知识点状态。点击完成按钮时立即切换绿色样式并调用接口；保存失败则回滚并显示错误提示。同一份清单一次只允许一个学习状态请求，避免并发覆盖整份 JSON。

进度按完整清单计算，不受搜索和重要程度筛选影响：

```text
percentage = round(learnedCount / totalCount * 100)
```

顶部展示“已学习 X / Y”、绿色进度条和百分比。已学习条目使用浅绿色背景、绿色边框和绿色对勾；再次点击取消学习。

## 兼容与限制

- 历史知识点没有 `learned` 时视为未学习，无需数据迁移。
- 学习状态与 AI 生成结果共同存放于 `content_json`，适用于当前一份生成内容只属于一个用户的模型。
- 本次不实现多人共享进度、掌握程度等级、学习历史或审计日志。
- 本次不修改其他四类生成式功能。

## 验收标准

- 新生成知识点均包含 `learned: false`。
- 历史清单可以正常打开并显示 0% 或已有状态对应的进度。
- 标记和取消学习可以永久保存，刷新详情页后状态不丢失。
- 搜索和筛选不会改变总进度的分母。
- 非所有者、错误内容类型、失败内容和不存在的知识点均不能被修改。
- 保存失败时前端恢复原状态并向用户显示提示。
