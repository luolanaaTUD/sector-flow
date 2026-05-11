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

可选：复制 `compose.override.example.yaml` 为 `compose.override.yaml`，写入仅本机需要的覆盖（该文件已加入 `.gitignore`）。

### Compose 文件说明

| 文件 | 用途 |
|---|---|
| [`compose.yaml`](compose.yaml) | 默认栈：本机 `build` + 暴露端口；本地与 **腾讯云 CVM 现编** 都用这一份即可 |
| [`compose.override.example.yaml`](compose.override.example.yaml) | 可选覆盖模板；复制为 `compose.override.yaml`（已 gitignore）后与 `compose.yaml` 自动合并 |

**腾讯云 CVM**：在服务器 `/etc/docker/daemon.json` 配置 **Docker Hub 镜像加速**（如 `https://mirror.ccs.tencentyun.com`）后，`docker compose build` / `pull` 会自动走加速，**不需要**单独的 Compose 覆盖文件。部署：`docker compose up -d --build`。详见 [`DEPLOY_TENCENT_CLOUD.md`](DEPLOY_TENCENT_CLOUD.md)。

如需 **CI 预构建镜像**、或在生产环境 **取消映射数据库端口**，可在服务器自建 `compose.override.yaml`；示例见 [`DEPLOY_TENCENT_CLOUD.md`](DEPLOY_TENCENT_CLOUD.md) 文末 Optional 各节。

- 前端看板：http://localhost:3000
- 后端文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- Docker 模式会自动执行 Alembic 迁移，并启用 TimescaleDB hypertable + compression policy。
- 后端容器固定 `linux/amd64`，确保同花顺依赖的 `py-mini-racer` 轮子在 Docker 中可用。
- 概念板块支持通过 allowlist 控制采集范围，避免默认抓取近 400 个概念板块。
- 前端首次加载会自动预选一组重点行业/概念板块，直接展示图表。

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
├── compose.yaml              # 默认 Docker Compose（本地 / CVM 现编）
├── compose.override.example.yaml
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

## 时区与历史数据说明

- 当前版本会将采集时间统一按 **Asia/Shanghai** 交易分钟写入和查询。
- 若你在旧版本中写入过 UTC-like 时间（例如交易日出现 `01:xx/02:xx`），图表可能缺线。服务端已兼容读取，但建议做一次性回填，避免历史数据混杂。

```bash
# 将明显偏移的分钟记录（01:00-07:59）回拨到上海交易时间（+8小时）
docker compose exec db psql -U sector_flow -d sector_flow -c "
UPDATE sector_fund_flow_minute
SET ts = ts + interval '8 hour'
WHERE ts::time >= time '01:00:00'
  AND ts::time <  time '08:00:00';
"
```

## 环境变量（backend/.env）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://sector_flow:sector_flow@localhost:5432/sector_flow` | PostgreSQL/TimescaleDB 连接串 |
| `TZ` | `Asia/Shanghai` | 容器时区（backend/db/frontend 统一中国时区） |
| `PGTZ` | `Asia/Shanghai` | PostgreSQL 会话时区（db 容器） |
| `COLLECTOR_ENABLED` | `true` | 是否启动采集 Worker |
| `SECTOR_TYPES` | `industry,concept` | 采集板块类型 |
| `AKSHARE_REQUEST_DELAY` | `2` | 两次请求间隔（秒） |
| `CONCEPT_ALLOWLIST_ENABLED` | `true` | 是否启用概念板块白名单过滤 |
| `CONCEPT_ALLOWLIST_FILE` | `backend/app/collector/data/concept_allowlist.txt` | 概念白名单文件路径（一行一个概念名） |
