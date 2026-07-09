# CourseNexus Frontend

React + TypeScript/TSX + Vite 前端项目骨架。

## 目录

```text
src/
├── api/
├── app/
├── components/
├── features/
├── hooks/
├── pages/
├── router/
├── types/
└── utils/
```

`features/` 按业务能力分区，当前只保留目录占位，不实现业务页面。

## 命令

从仓库根目录：

```powershell
pnpm frontend:dev
pnpm frontend:build
pnpm frontend:test
```

从 `frontend/` 目录：

```powershell
pnpm dev
pnpm build
pnpm test -- --run
```

## 环境变量

前端 Vite 已配置为读取仓库根目录 `.env`，示例见 `../.env.example`。只有 `VITE_` 开头的变量会暴露给浏览器；API Key、`SECRET_KEY` 等敏感配置不要放入 `VITE_` 变量。
