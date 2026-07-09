# Development Conventions v0.1

## 命名约定

- API 路径使用英文复数资源名，例如 `/courses`、`/materials`、`/study-plans`。
- JSON 字段使用 `snake_case`，与后端模型和 PRD 字段口径保持一致。
- 前端组件使用 `PascalCase`，普通函数和变量使用 `camelCase`。
- 后端 Python 文件、函数和变量使用 `snake_case`。
- 状态枚举值保持小写下划线，例如 `parse_failed`、`not_started`。

## 目录约定

- 前端页面级入口放在 `frontend/src/pages/`。
- 前端跨页面组件放在 `frontend/src/components/`。
- 前端请求封装放在 `frontend/src/api/`。
- 后端路由放在 `backend/app/api/`。
- 后端配置、鉴权、错误码放在 `backend/app/core/`。
- 后端模型、schema、service、repository 分层放在对应目录。
- 长期文档必须放入 `docs/` 对应分区。

## 代码风格

- 优先使用明确的数据结构和类型，不用隐式字典在多层之间传递关键业务数据。
- 后端业务逻辑优先放在 service 层，路由层保持薄。
- 前端页面应区分数据请求、状态展示和交互组件，避免页面文件无限膨胀。
- 复杂状态变化必须有清晰函数名和测试或验收说明。

## 错误处理约定

- 后端统一返回 `error.code`、`error.message`、`error.details` 和 `request_id`。
- 前端只根据 `error.code` 做逻辑判断。
- 未登录使用 `UNAUTHORIZED`。
- 已登录但无权访问使用 `FORBIDDEN`。
- 状态不允许操作使用 `STATE_CONFLICT`。
- 生成或解析失败必须保存失败状态，允许用户重试。

## 日志约定

- 后端日志至少包含请求 ID、错误码、接口路径和必要上下文 ID。
- 不记录密码、完整资料内容、完整用户问题正文或密钥。
- 资料解析、Agent 生成、保存计划、导出失败等关键错误必须记录。

## 配置和环境变量约定

- 数据库地址、密钥、初始账号配置、文件存储路径通过配置或环境变量管理。
- 本地默认配置可以有示例值，但真实密钥不得提交。
- SQLite 是当前 POC 默认数据库，模型设计保持可迁移。
- 本仓库长期按 monorepo 管理，环境变量示例统一放在根目录 `.env.example`，真实 `.env` 也只放在根目录且不得提交。
- 后端读取根目录 `.env`；前端 Vite 读取根目录 `.env` 中的 `VITE_` 公共变量。
- API Key、`SECRET_KEY`、模型服务地址等敏感配置只能作为后端变量使用，禁止放入 `VITE_` 变量。

## 包管理约定

- 根目录 `package.json` 提供跨前后端常用脚本，例如 `frontend:dev`、`frontend:build`、`frontend:test`、`backend:dev`、`backend:test`、`backend:migrate` 和 `test`。
- 前端包管理使用 pnpm，workspace 配置位于根目录 `pnpm-workspace.yaml`，锁文件为根目录 `pnpm-lock.yaml`。
- 前端依赖声明只放在 `frontend/package.json`。
- 后端依赖声明以 `backend/pyproject.toml` 为准；conda 环境示例位于 `backend/environment.yml`。
- 后端项目 conda 环境固定使用 Python 3.12；`backend/environment.yml` 是后端 Python 环境文件，创建或更新 conda 环境时从 `backend/` 目录执行，确保 `-e ".[dev]"` 指向后端包。
- `.gitignore` 统一放在根目录，子项目不再维护独立 `.gitignore`。
- 根目录 `.env.example` 可以提交，真实 `.env` 不得提交。

## 测试或验收约定

- 后端使用 pytest 覆盖权限、数据归属、状态流转、幂等和核心服务。
- 前端使用 Vitest 覆盖关键组件、状态转换和请求边界。
- 暂无自动化覆盖的关键流程必须记录手动验收步骤。
- 生成类能力至少验证成功、失败、重试和无资料场景。

## Git 提交约定

- 每完成一个可验证的小功能、小修复或小文档规范变更，都应单独提交一次 git。
- 不要把多个小功能、跨模块改动或多轮需求攒到一个完整大功能结束后再做一次大提交。
- 一次提交应包含该小改动所需的代码、测试和文档，避免只提交半成品。
- 提交前运行与本次改动匹配的验证命令；文档-only 变更可不跑完整测试，但最终说明中必须写明未运行测试。
- 如果后续需要整理提交历史，应优先在合并前通过 review 或 rebase 处理，不在开发过程中牺牲小步提交记录。
- 提交信息使用 Angular / Conventional Commits 结构：`<type>(<scope>): <subject>`。
- `type` 使用英文固定标识，例如 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`、`build`、`ci`、`perf`、`style`、`revert`。
- `scope` 可选，使用英文短名标识影响范围，例如 `backend`、`frontend`、`docs`、`db`、`materials`、`courses`。
- 除模板字段和固定标识外，`subject`、正文和说明性内容使用中文。
- 文档类提交使用 `docs`，不要使用非 Angular 规范的 `doc`。
- 示例：`docs(engineering): 明确提交信息使用中文说明`、`fix(api): 修正未登录错误响应`。

## 数据库和 migration 约定

- 结构变化通过 Alembic 管理。
- 常规业务数据操作优先使用 SQLAlchemy 2 ORM 实现，保持实体关系、权限过滤和状态流转清晰可维护。
- 复杂统计查询、学习进度聚合、排行榜计算或特殊性能优化场景，可以结合 SQLAlchemy Core 或原生 SQL 处理，但必须保留清晰的 repository / service 边界和必要测试说明。
- 该策略兼顾 ORM 的开发效率和原生 SQL 的灵活性，适合本系统在课程项目中的快速开发与后续扩展。
- 不手工修改共享数据库结构。
- migration 不承载业务生成逻辑。
- 新字段优先按兼容方式演进：先可空，再回填，再收紧约束。
- 删除数据优先软删除，默认不在前端列表展示。

## 文档更新约定

- 产品行为变化更新 `docs/product/`。
- 架构、模块边界或核心依赖变化更新 `docs/architecture/`。
- API、字段、状态、错误码或数据契约变化更新 `docs/api-data/`。
- 工程约定、测试方式或协作方式变化更新 `docs/engineering/`。
- 当前状态、实现路线、技术债和共享优化计划更新 `docs/planning/`。
- 具体模块进入开发且边界稳定后，才更新或创建 `docs/domains/` 下的模块文档。
- 插件开发、Agent 执行草稿和 superpowers 运行产物放入本地目录 `docs/superpowers/`，该目录不进入 git；其中形成共享规划或长期决策时，必须迁移到 `docs/planning/` 或上述正式文档分区。

## 禁止事项

- 禁止不读 `docs/index.md` 就直接修改长期架构或契约。
- 禁止只在聊天记录中保留长期决策。
- 禁止绕过 `user_id` 归属校验访问业务数据。
- 禁止生成没有真实资料关联的引用来源。
- 禁止把 `StudyPlan` 改成本期多课程计划。
- 禁止在首页今日待办或首页大日历中加入计划创建 / 编辑职责。
- 禁止在计划保存阶段提前生成今日讲义或任务测试题正文。
