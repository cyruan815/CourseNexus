# S01 Schema Audit

## 日期

2026-07-10

## 结论

S01 计划学习模式契约与迁移审计完成。当前 SQLAlchemy metadata、baseline migration 和文档契约共同确认：计划学习模式第一阶段复用现有 13 张核心表，不新增业务表，不修改 baseline migration，不创建新的 Alembic revision。

## 审计范围

已审计表：

| 表 | 结论 |
| --- | --- |
| `users` | 复用，作为用户权限根。 |
| `courses` | 复用，作为单课程计划归属。 |
| `material_folders` | 复用，作为资料范围目录来源。 |
| `course_materials` | 复用，作为计划和任务内容的资料边界。 |
| `material_chunks` | 复用，作为全材料批次和引用来源。 |
| `conversations` | 复用，可承载执行页问答会话来源。 |
| `messages` | 复用，可承载执行页问答消息。 |
| `source_citations` | 复用，保存生成内容和问答引用快照。 |
| `ai_generated_contents` | 复用，承载 `handout` 和 `task_test`。 |
| `study_plans` | 复用，承载单课程计划主记录。 |
| `study_tasks` | 复用，承载日期级一级任务。 |
| `study_subtasks` | 复用，承载二级任务、完成事实和关联资料。 |
| `checkin_records` | 复用，承载用户自然日打卡快照。 |

明确禁止新增的独立业务表：

```text
todos
calendar_events
handouts
task_tests
export_records
```

## 验证命令

```powershell
cd D:\Projects\CourseNexus\backend
uv run python -m pytest tests/modules/study_mode/test_subsystem_schema_contract.py -q
uv run python -m pytest tests/test_schema_metadata.py -q --tb=short
uv run python -m alembic upgrade head
```

验证结果：

- `tests/modules/study_mode/test_subsystem_schema_contract.py`：`8 passed in 0.53s`。
- `tests/test_schema_metadata.py`：`2 passed in 0.40s`。
- Alembic `upgrade head` 成功，未产生新 revision。

## 无 Migration 结论

本阶段不创建 Alembic migration，原因如下：

1. 自然语言解析结果、用户确认配置、偏好和材料范围可写入 `study_plans.parsed_config_json`。
2. 计划、日期级任务和二级任务可由 `study_plans`、`study_tasks`、`study_subtasks` 表达。
3. 今日待办和日历是查询投影，不需要 `todos` 或 `calendar_events`。
4. 今日讲义和任务测试题复用 `ai_generated_contents.content_type = handout|task_test`，并通过 `study_subtask_id` 绑定二级任务。
5. 打卡每日唯一约束、计数、比例和 `0..5` 颜色等级已存在于 `checkin_records`。
6. PDF 导出可作为请求派生文件返回，不需要 `export_records`。

只有出现现有列无法表达且已通过共享契约评审的持久化需求时，才允许创建后续兼容 migration；不得修改 `backend/migrations/versions/20260709_0001_create_core_tables.py`。

## 后续状态

S01 已完成测试和文档侧契约沉淀。S02-S07 业务功能仍未实现，后续应按任务书逐项实现并继续保持小测试、小提交。
