# CourseNexus Backend

FastAPI + SQLAlchemy + Alembic 后端项目骨架。

## 目录

```text
app/
├── api/
├── core/
├── db/
├── integrations/
├── modules/
└── shared/
migrations/
tests/
```

当前已创建 SQLAlchemy models 和 baseline migration，但业务 API / service / repository 仍未实现。

## 安装

推荐使用项目专属 conda 环境：

```powershell
cd backend
conda env create -f environment.yml
conda activate course-nexus
```

如果环境已经存在，更新依赖：

```powershell
cd backend
conda env update -f environment.yml --prune
```

`environment.yml` 会创建 Python 3.12 环境，并通过 `pip -e ".[dev]"` 安装后端运行依赖和测试依赖。若未使用 conda，也可以在 Python 3.12 环境中手动安装：

```powershell
python -m pip install -e ".[dev]"
```

## 命令

```powershell
python -m uvicorn app.main:app --reload
python -m pytest
python -m alembic upgrade head
```

## 环境变量

后端读取仓库根目录 `.env`，示例见 `../.env.example`。API Key、`SECRET_KEY`、模型服务地址、文件存储路径等服务端配置只放在根目录 `.env`，不要放入前端 `VITE_` 变量。

## 数据库

默认数据库为当前目录下的 SQLite 文件：

```text
sqlite:///./course_nexus.db
```

本地数据库文件被 `.gitignore` 忽略。表结构以 `migrations/` 为准，字段契约见 `../docs/api-data/table-schema.md`。
