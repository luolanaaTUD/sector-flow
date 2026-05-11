# Deploy Sector Flow on Tencent Cloud CVM

Docker Compose deployment. Use an **x86_64** CVM (backend image is `linux/amd64`). Rough sizing: **2 vCPU / 4 GB RAM**, **≥50 GB** disk, **≥5 Mbps** egress if you pull images frequently. Configure a **Docker Hub mirror** on the server (`mirror.ccs.tencentyun.com`) so `docker compose build` pulls base images faster—no extra Compose file required for that.

## Security group

Inbound: `22`, `80`, `443`; optionally `3000` / `8000` for debugging. Do **not** expose `5432` to the internet.

## Install Docker + Compose

**TencentOS / OpenCloudOS** (typical on Tencent Cloud):

```bash
sudo dnf update -y
sudo rm -f /etc/yum.repos.d/docker-ce.repo
sudo dnf clean all && sudo dnf makecache
sudo dnf install -y docker docker-compose-plugin git || sudo dnf install -y docker docker-compose git
sudo systemctl enable --now docker
docker compose version
```

If the stock package is missing or too old, use Tencent’s Docker CE mirror:

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce --nobest
sudo systemctl enable --now docker
docker compose version || docker-compose version
```

**Ubuntu** (Docker CE from Tencent mirror):

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

If install fails with `download.docker.com` / `404` on TencentOS 4, remove `/etc/yum.repos.d/docker-ce.repo` and use the native `dnf install docker` flow above or the Tencent CE repo fallback.

## Registry mirror (recommended)

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker
docker info  # confirm Registry Mirrors
```

## Deploy

```bash
ssh root@<CVM_PUBLIC_IP>
cd /opt
git clone <YOUR_REPO_URL> sector-flow && cd sector-flow   # if GitHub is blocked, use Gitee mirror / scp / tarball — see README
cp .env.example .env
# Set NEXT_PUBLIC_API_URL to your public API URL if needed (e.g. http://<IP>:8000)
docker compose up -d --build
docker compose ps
```

**Logs:** `docker compose logs -f backend`

**Verify:** `http://<CVM_PUBLIC_IP>:3000`, `http://<CVM_PUBLIC_IP>:8000/docs`, `http://<CVM_PUBLIC_IP>:8000/health`

```bash
docker compose exec db psql -U sector_flow -d sector_flow -c "\dx"
```

## Common commands

```bash
docker compose restart
git pull && docker compose up -d --build
docker compose down -v && docker compose up -d --build   # resets DB volume — destructive
```

## Optional: hide Postgres on the host

Create `compose.override.yaml` (gitignored) beside `compose.yaml`:

```yaml
services:
  db:
    ports: !reset []
```

Then `docker compose up -d --build` picks it up automatically.

## Production notes

Put Nginx/Caddy in front; expose only `80`/`443`; keep DB private; TLS when you have a domain; back up the DB (`pg_dump` or snapshots).

## Optional: pre-built images (CI)

Requires Compose **v2.24+**. In `.env`: `BACKEND_IMAGE`, `FRONTEND_IMAGE`, optional `TIMESCALE_IMAGE`. Add `compose.override.yaml`:

```yaml
services:
  db:
    image: ${TIMESCALE_IMAGE:-timescale/timescaledb:2.17.2-pg16}
    ports: !reset []
  backend:
    image: ${BACKEND_IMAGE:?Set BACKEND_IMAGE in .env}
    build: !reset null
    platform: linux/amd64
  frontend:
    image: ${FRONTEND_IMAGE:?Set FRONTEND_IMAGE in .env}
    build: !reset null
```

On the build machine, then on CVM: `docker compose pull && docker compose up -d`.

Build examples:  
`docker build --platform linux/amd64 -t $BACKEND_IMAGE ./backend`  
`docker build --platform linux/amd64 -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL=http://<IP>:8000 -t $FRONTEND_IMAGE ./frontend`
