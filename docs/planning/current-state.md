# Current State

## 状态摘要

- 日期：2026-10-01
- 发布目标：可靠的单机 V1
- 集成基线：`dev` 已合并 PR #30～#40；M07 文档收口随当前 PR 合并生效
- 正式完成清单：[v1-completion-matrix.md](v1-completion-matrix.md)
- 临时评审稿：`tmp/v1-closeout-plan-review.md` 只作为历史输入，不是状态或契约权威来源

CourseNexus 已从早期 walking skeleton 进入可发布的单机 V1 候选阶段。注册登录、课程、资料、问答引用、独立生成、学习计划、待办日历、任务执行、打卡和既定导出已经形成浏览器与 API 闭环；前端不再只是课程详情空壳。

## 当前已具备

### 产品闭环

- 用户可注册、登录、退出、修改密码；修改密码通过 `token_epoch` 撤销该用户既有 Token。
- 创建课程后进入详情页并展示一次性上传引导；URL 资料不再提供新增入口，历史记录只读兼容。
- 资料工作区支持上传、一级目录归类、显式选择、解析状态、重解析和删除。
- 项目级统一文件预览器直接只读查看 PDF、DOCX、PPTX、图片和文本；私有文件不交给第三方在线预览服务，失败时保留原文件下载。
- 课程问答和任务问答保存真实引用；PDF 可靠页码可定位，其他来源展示有效片段，删除资料后历史快照仍可读。
- Quiz、Flashcard、Mindmap、复习提纲和知识点清单按实际资料范围生成并保存。
- 学习计划继承课程详情页本次显式资料快照；空范围阻止继续，配置解析、诊断、预览和保存使用同一范围。默认名包含目标与日期，保存前可编辑。
- 首页待办、全局/课程日历、计划执行、任务讲义、任务测试题、完成状态和打卡可用。讲义支持 PDF，任务测试题支持 Markdown；测试题 PDF 明确延期。

### 安全与运行边界

- 带认证信息的前端业务请求只接受受信 `/api/v1/...` 路径，Blob 下载与 JSON 请求复用同一 URL 校验。
- `APP_ENV` 仅允许 `development|test|production`；Mock 默认关闭，只能在 development/test 显式开启。缺 Provider 返回 `503 MODEL_PROVIDER_NOT_CONFIGURED`，production 错误配置拒绝启动。
- Health 只公开环境与 Mock 状态；日志统一脱敏 Secret、API Key 和 Bearer Token。
- SQLite、上传、Chroma 和日志相对路径统一相对仓库配置根目录解析；SQLite 启用外键、WAL、30 秒 busy timeout 和连接健康检查。
- FastAPI 生命周期通过进程级 `RagIndexManager` 管理 Chroma；维护命令与 API 使用同一 Settings。

### 数据可靠性

- 材料解析使用 `building -> active / failed -> retired` 候选版本流程。解析、索引、完整性校验或切换失败不会破坏旧生效版本。
- 问答、生成内容和学习计划记录实际使用的材料版本；候选和退休版本不会进入当前检索结果。
- 上传数据库失败会幂等回收已写文件；补偿失败返回 `UPLOAD_COMPENSATION_FAILED`。
- 问答、生成、计划和任务内容在发布前复核用户、课程、材料与版本，迟到结果不能重新发布已删除或失效资源。
- `python -m app.commands.reconcile_storage` 提供只读文件、数据库、解析版本与 Chroma 对账；默认不删除、不修复。

## 发布验收基线

PR #40 候选提交 `2d9f1a8` 的验证结果：

- 后端：726 passed，1 skipped。
- 前端：247 passed。
- `pnpm frontend:build`：通过。
- GitHub Actions：后端测试、空库迁移、旧库升级、前端测试和构建全部通过。
- 无隐私 TXT、PDF、DOCX、PPTX 样本：格式有效、生产解析器可读取、浏览器预览通过。
- 真实模型验收：Mock 关闭，17 个步骤全部通过，覆盖上传解析、课程问答引用、复习提纲、学习计划保存和只读对账；最终对账为 clean。

可复现入口见 [../engineering/v1-release-acceptance.md](../engineering/v1-release-acceptance.md)。临时数据库、日志、截图和报告位于被 Git 忽略的 `tmp/`，不构成长期文档。

## 已接受的 V1 延期项

以下事项没有伪装成已完成，也不阻塞当前单机 V1：

- P03：任务测试题 PDF；当前只导出 Markdown。
- P10：作答历史、服务端判分、错题本、学习笔记等产品扩展。
- R01：SQLite 持久化后台 Job、独立 Worker、取消与恢复。
- R03：完整任务化的一致性状态机，以及资料理解流水线剩余的完整性/检索质量升级。
- S02：服务端会话表与 HttpOnly Cookie；当前改密使用 `token_epoch` 整体撤销。
- S04：统一输入、解压、并发与模型额度预算。
- S05：讲义 PDF Chromium 网络隔离。
- M01：大型模块拆分及 Handout 私有校验函数解耦。
- M02：全站服务端状态统一迁移到 Query。
- M03：路由和重型组件全面懒加载及首屏预算。
- M05：对话、消息、生成内容和计划列表分页。
- M06：任务、Provider、成本和积压指标的完整可观测性。
- 图片 OCR 质量、复杂 Office/PDF 像素级版式与 Office 动画/编辑能力。

## 当前发布边界

- 当前目标是可信本地、小规模、单机运行，不是公网多人生产部署。
- SQLite 和本地文件是权威存储，Chroma 是可重建派生索引。
- Mock 只证明确定性回归，不能代替真实模型发布验收。
- `dev -> main` 发布 PR、部署和真实数据迁移仍需单独授权。

## 日常验证入口

```powershell
pnpm test
pnpm frontend:build
pnpm backend:migrate

cd backend
python -m app.commands.reconcile_storage --json
python scripts/run_v1_release_acceptance.py
```

真实模型脚本会创建独立 `tmp/v1-release-validation-*`，不会复用日常 SQLite、上传目录或 Chroma collection。
