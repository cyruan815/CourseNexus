# 本地存储运行与迁移

## 1. 适用范围

本文定义单机 V1 的 SQLite、上传文件、Chroma 和日志路径，以及数据库连接、向量索引生命周期和旧数据迁移规则。API、Alembic 与维护命令必须复用同一套 Settings 和路径解析，不得根据进程启动目录自行推导数据位置。

## 2. 规范路径

相对路径统一以仓库配置根目录解析为绝对路径；从仓库根目录、`backend/` 或其他当前目录启动，均访问同一份数据。显式绝对路径保持原样。

默认位置如下：

| 配置 | 默认规范位置 |
| --- | --- |
| `DATABASE_URL=sqlite:///./course_nexus.db` | `<repo>/course_nexus.db` |
| `FILE_STORAGE_PATH=./uploads` | `<repo>/uploads` |
| `CHROMA_PERSIST_PATH=./data/chroma` | `<repo>/data/chroma` |
| `LOG_DIR=./logs` | `<repo>/logs` |

以上数据目录和文件不得提交到 Git。临时验收数据库、截图和日志统一放入 `<repo>/tmp/`。

## 3. 旧启动目录冲突保护

早期版本会把相对路径绑定到进程当前目录，因而可能在 `backend/` 等位置留下另一套数据。应用启动、Alembic 和 `rebuild_rag_index` 会在以下条件同时成立时拒绝继续：

1. 旧启动目录存在非空 SQLite、上传目录或 Chroma 数据；
2. 对应规范位置为空；
3. 当前配置仍指向仓库内的规范相对位置。

错误消息会列出旧位置和规范目标。程序不会自动移动或删除旧数据，也不会把日志文件视为业务数据冲突。显式配置到仓库外的绝对路径时，不扫描或干预该外部位置。

## 4. 旧数据迁移步骤

1. 停止所有 CourseNexus API、Alembic 和索引维护进程。
2. 在 `tmp/v1-closeout-backup-<timestamp>/` 建立备份目录。
3. 对 SQLite 使用一致性备份 API 或 SQLite `.backup`，不要在写入进程运行时直接复制数据库文件。
4. 完整快照上传目录与 Chroma 目录，并保留原目录不动。
5. 把数据复制到规范位置；若目标已存在数据，停止并人工确认，禁止覆盖合并。
6. 使用相同环境配置执行 `pnpm backend:migrate`。
7. 启动 API，验证资料列表、原文件访问和问答检索；必要时从 SQLite 执行 `python -m app.commands.rebuild_rag_index --all` 重建派生向量。
8. 负责人确认验证完成后，才可单独清理旧位置与备份。

若只发现旧日志，可按日志保留策略自行归档，不需要迁移到业务数据备份中。

## 5. SQLite 连接基线

所有在线和维护入口通过统一 Engine 工厂创建连接：

- `pool_pre_ping=true`，复用连接前执行健康检查；
- `foreign_keys=ON`，每条 SQLite 连接启用外键约束；
- `busy_timeout=30000`，锁竞争最多等待 30 秒；
- 文件数据库使用 `journal_mode=WAL`；
- 内存数据库不强制 WAL，避免测试和临时连接得到不可用的文件持久化语义。

这些设置在连接建立事件中执行，不能只依赖一次性迁移或手工 PRAGMA。

## 6. Chroma 生命周期

FastAPI 进程通过 `RagIndexManager` 管理一个延迟创建、线程安全的 `RagIndex` 实例。应用 lifespan 在配置可用时预热索引，在退出时只释放进程内引用，不调用 collection reset、目录删除或其他破坏性清理。

请求依赖和重建命令都从管理器取得索引，不直接重复创建 `PersistentClient`。SQLite 的材料和 chunk 仍是权威数据；Chroma 是可通过维护命令重建的派生索引。

## 7. 失败处理与资源预算

- 旧路径冲突在数据库或 Chroma 连接前失败，防止静默生成第二套数据。
- SQLite PRAGMA 设置失败会使连接建立失败，不降级为未知持久化语义。
- 未配置 embedding 时，API 保持可启动；真正需要 RAG 的消费者返回稳定的模型配置错误。
- 单个后端进程只持有一个 Chroma 客户端。多进程部署时每个进程各有一个实例；单机 V1 不承诺跨进程写入协调。
- 应用关闭不会删除 SQLite、上传文件或 Chroma 数据。

## 8. 验证入口

跨存储只读对账命令：

```powershell
cd backend
python -m app.commands.reconcile_storage
python -m app.commands.reconcile_storage --json
python -m app.commands.reconcile_storage --building-stale-minutes 60
```

命令只读取现有 SQLite、上传目录和 Chroma collection，不创建缺失数据库、不计算 embedding，也不删除或修复任何记录。人类可读输出适合本地排查，`--json` 输出稳定的 schema version、统计和带 `notice` / `warning` severity 的 `issues` 数组。退出码为：

- `0`：没有不一致；按策略保留的 `failed` / `retired` 版本或未超时 `building` 版本可以作为 notice 出现。
- `1`：发现文件缺失、孤儿目录、chunk/vector 集合差异、异常向量、非法 active 指针或超时 building 等不一致。
- `2`：命令无法完成，例如规范 SQLite 数据库不存在或存储无法读取。

JSON 报告中的稳定 `issue.code` 包括：`DATABASE_NOT_FOUND`、`MATERIAL_FILE_MISSING`、`ORPHAN_MATERIAL_DIRECTORY`、`ACTIVE_VECTOR_SET_MISMATCH`、`ORPHAN_VECTOR`、`VECTOR_FOR_DELETED_MATERIAL`、`VECTOR_METADATA_INVALID`、`VECTOR_METADATA_MISMATCH`、`ACTIVE_PARSE_VERSION_POINTER_INVALID`、`MULTIPLE_ACTIVE_PARSE_VERSIONS`、`PARSE_VERSION_RETAINED` 和 `STORAGE_RECONCILIATION_FAILED`。新增检测项可以扩展代码集合，但不得改变既有代码语义或把 notice 静默升级为 destructive 修复。

发现不一致后先停止相关写入进程并按第 4 节备份，再根据报告人工决定恢复文件、重建派生索引或修复业务数据；本命令不提供自动删除或自动修复。

```powershell
pnpm backend:test
pnpm backend:migrate
python -m app.commands.rebuild_rag_index --all
python -m app.commands.reconcile_storage --json
```

路径、冲突保护、SQLite PRAGMA、Chroma 单例与只读对账分别由 `backend/tests/core/test_paths.py`、`backend/tests/db/test_session.py`、`backend/tests/api/test_lifespan.py`、`backend/tests/integrations/test_rag_index_manager.py` 与 `backend/tests/commands/test_reconcile_storage.py` 覆盖。
