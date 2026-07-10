# CourseNexus Frontend

CourseNexus 的 React + TypeScript/TSX + Vite 前端。本文只作为前端协作开发入口；产品行为、接口字段和验收口径以仓库 `docs/` 为准。

## 当前范围

已经落地的最小集成工作台包括：

- 登录页、token 保存和受保护路由；
- 首页课程列表；
- 课程详情加载与资料区、问答区、生成内容区、学习计划入口的页面骨架；
- 统一 API client、错误处理和基础测试环境。

资料上传、课程问答、生成内容和计划学习的完整交互仍按第一阶段前端任务书实施。不要把页面骨架或 `features/` 目录视为对应业务已经完成。

## 目录边界

```text
src/
├── api/          # 通用 HTTP client 和错误处理
├── app/          # 应用装配
├── components/   # 跨业务复用组件
├── features/     # 按业务能力组织的 API、状态和组件
├── hooks/        # 通用 React hooks
├── pages/        # 路由页面组合
├── router/       # 路由与访问控制
├── types/        # 前端共享类型
└── utils/        # 无业务归属的工具
tests/            # 与 src 结构对应的 Vitest 测试
```

- 业务代码优先进入对应 `features/<domain>/`，页面只负责组合。
- 不在前端复制后端业务规则、直接查询数据库或调用模型服务。
- API 路径、字段、状态和错误码不得自行猜测，以接入文档和后端 schema 为准。

## 开发命令

推荐从仓库根目录运行：

```powershell
pnpm install
pnpm frontend:dev
pnpm frontend:test
pnpm frontend:build
```

也可以在 `frontend/` 目录运行：

```powershell
pnpm dev
pnpm test -- --run
pnpm build
```

提交前至少运行与改动匹配的前端测试；页面、路由、类型或构建配置变更还应运行 `pnpm frontend:build`。

## 环境变量

Vite 读取仓库根目录 `.env`，示例见 [../.env.example](../.env.example)。

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

`VITE_API_BASE_URL` 是后端服务根地址，API client 自己附加 `/api/v1` 路径。只有 `VITE_` 开头的变量会进入浏览器；任何 API Key、`SECRET_KEY` 或模型服务地址都不得使用 `VITE_` 前缀。

## 协作入口

- [第一阶段前端任务书](../docs/planning/phase-1-task-books/README.md)
- [前端接入契约](../docs/api-data/frontend-integration.md)
- [API 与数据契约](../docs/api-data/index.md)
- [工程与协作规范](../docs/engineering/index.md)
- [产品需求](../docs/product/index.md)

接口或字段发生变化时先同步 `docs/api-data/`；不要只修改前端类型来掩盖契约不一致。
