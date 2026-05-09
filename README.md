# A股板块资金流向看板

实时 Web 看板 – 板块主力资金分时走势、多曲线叠加对比。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 API | Python 3.12, FastAPI, SQLAlchemy, PostgreSQL/TimescaleDB |
| 数据采集 | AkShare + APScheduler |
| 包管理 | **uv** |
| 前端 | Next.js 15, TailwindCSS, Apache ECharts, SWR |

## Docker 快速启动（推荐）

```bash
# 在项目根目录
cp .env.example .env
docker compose up --build
```

- 前端看板：http://localhost:3000
- 后端文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- Docker 模式会自动执行 Alembic 迁移，并启用 TimescaleDB hypertable + compression policy。
- 后端容器固定 `linux/amd64`，确保同花顺依赖的 `py-mini-racer` 轮子在 Docker 中可用。

### 初始化与重置

```bash
# 查看 TimescaleDB 扩展是否安装
docker compose exec db psql -U sector_flow -d sector_flow -c "\dx"

# 重置数据库卷（会删除数据）
docker compose down -v
```

## 本地开发（不使用 Docker）

本地模式同样依赖 PostgreSQL/TimescaleDB（不再支持 SQLite）。可以仅启动数据库容器：

```bash
docker compose up -d db
```

### 1. 后端

```bash
cd backend

# 安装依赖（需 uv，首次自动创建 .venv）
uv sync

# 复制环境变量
cp .env.example .env

# 如数据库在本机 Docker 暴露的默认端口，保持 .env 默认 DATABASE_URL 即可

# 启动 API 服务
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

看板地址：http://localhost:3000

## 目录结构

```
sector-flow/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由
│   │   ├── collector/    # AkShare 采集 Worker
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── services/     # 查询与时间轴服务
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic/          # 数据库迁移
│   ├── scripts/          # 工具脚本
│   └── pyproject.toml    # uv 项目配置
└── frontend/
    ├── app/              # Next.js App Router
    ├── components/       # FundFlowChart, SectorSelector, RankingPanel, TopBar
    ├── hooks/            # useFundFlow (SWR)
    └── lib/              # api.ts
```

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/sectors` | 所有板块列表 |
| POST | `/api/fund_flow/intraday` | 指定日期+板块的分时序列 |
| GET | `/api/fund_flow/ranking` | 最新分钟资金排行 |

## 采集风控

- 采集频率严格 ≥ 1分钟/次（APScheduler 交易时段专用 Cron）。
- 前端所有请求仅访问自建 FastAPI，不直连 AkShare。

## 环境变量（backend/.env）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://sector_flow:sector_flow@localhost:5432/sector_flow` | PostgreSQL/TimescaleDB 连接串 |
| `COLLECTOR_ENABLED` | `true` | 是否启动采集 Worker |
| `SECTOR_TYPES` | `industry,concept` | 采集板块类型 |
| `AKSHARE_REQUEST_DELAY` | `2` | 两次请求间隔（秒） |
