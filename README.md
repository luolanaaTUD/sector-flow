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
| [`compose.yaml`](compose.yaml) | 默认栈：本机 `build` + 暴露端口，适合本地与「在 CVM 上现编」 |
| [`compose.tencent.yaml`](compose.tencent.yaml) | 腾讯云生产覆盖：使用 TCR 镜像、**不**对外映射数据库端口 |
| [`compose.override.example.yaml`](compose.override.example.yaml) | 本地覆盖模板；复制为 `compose.override.yaml` 后由 Compose 自动合并 |

**腾讯云（推荐生产）**：镜像推送到 [TCR](https://cloud.tencent.com/product/tcr) 后，在服务器 `.env` 中设置 `BACKEND_IMAGE`、`FRONTEND_IMAGE`（可选 `TIMESCALE_IMAGE`），然后：

```bash
docker compose -f compose.yaml -f compose.tencent.yaml up -d
```

前端镜像构建时需带上公网可访问的后端地址，例如：

```bash
docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=http://<CVM_PUBLIC_IP>:8000 \
  -t <your-tcr>/sector-flow-frontend:<tag> \
  ./frontend
```

详细步骤见 [`DEPLOY_TENCENT_CLOUD.md`](DEPLOY_TENCENT_CLOUD.md)。

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
├── compose.yaml              # 默认 Docker Compose
├── compose.tencent.yaml      # 腾讯云 / TCR 生产覆盖
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
