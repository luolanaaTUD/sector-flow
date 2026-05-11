# Deploy Sector Flow on Tencent Cloud

This guide documents how to deploy this project on Tencent Cloud CVM using Docker Compose, with Tencent Docker mirrors enabled.

## 1) Recommended CVM spec

- CPU/RAM: `2C4G` (minimum workable for app + TimescaleDB in one host)
- Disk: `>= 50GB`
- OS: `TencentOS` / `OpenCloudOS` / `Ubuntu` (64-bit x86)
- Public bandwidth: `>= 5Mbps` recommended

> Note: this repo pins backend container platform to `linux/amd64`, so choose an x86_64 CVM.

## Quick path (TencentOS 4)

If your CVM uses TencentOS Server 4, run this first:

```bash
sudo dnf update -y
sudo rm -f /etc/yum.repos.d/docker-ce.repo
sudo dnf clean all
sudo dnf makecache
sudo dnf install -y docker docker-compose-plugin git
sudo systemctl enable --now docker
docker version
docker compose version
```

If `docker-compose-plugin` is not found:

```bash
sudo dnf install -y docker-compose git
docker-compose version || docker compose version
```

## 2) Security group

Open inbound ports:

- `22` (SSH)
- `80` (HTTP)
- `443` (HTTPS, if enabled)
- Optional for direct debugging:
  - `3000` (frontend)
  - `8000` (backend)

Do NOT expose `5432` publicly.

## 3) Connect to server

```bash
ssh root@<CVM_PUBLIC_IP>
```

## 4) Install Docker + Compose plugin

### TencentOS / OpenCloudOS (recommended)

Use TencentOS native repos first (more stable in mainland network):

```bash
# IMPORTANT: type normal ASCII parentheses, e.g. dnf update -y
sudo dnf update -y

# If you previously added docker-ce repo and hit errors, remove it first
sudo rm -f /etc/yum.repos.d/docker-ce.repo
sudo dnf clean all
sudo dnf makecache

# Install Docker from TencentOS repos
sudo dnf install -y docker docker-compose-plugin

sudo systemctl enable --now docker
docker version
docker compose version
```

If `docker-compose-plugin` is unavailable in your image, install `docker-compose`:

```bash
sudo dnf install -y docker-compose
docker-compose version || docker compose version
```

Official fallback (when native `docker` package is unavailable or too old):

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce --nobest
sudo systemctl enable --now docker
docker version
```

For Ubuntu (Tencent mirror):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

### Troubleshooting TencentOS install errors

If you saw errors like:

- `https://download.docker.com/linux/rhel/4/...`
- `404 repomd.xml`
- `SSL connect error`

Root cause is usually an incompatible/blocked `docker-ce` repo for TencentOS `releasever=4`.
Use either:

- TencentOS native installation commands above, and remove `/etc/yum.repos.d/docker-ce.repo`, or
- Tencent mirror Docker CE repo (`mirrors.cloud.tencent.com`) with `docker-ce --nobest`.

## 5) Configure Docker registry mirrors (optional, mainland network)

Public mirror endpoints change over time; treat them as **acceleration only**, not a guaranteed source of truth.

- On Tencent Cloud CVM, `mirror.ccs.tencentyun.com` is commonly used; if pulls still time out, add other mirrors your org trusts or use **Alibaba Cloud ACR “镜像加速器”** (per-account URL in console).
- For **production consistency**, build once (CI or build machine), push **`backend` / `frontend` (and optionally Timescale)** to **Tencent TCR**, then deploy only from TCR using [`compose.tencent.yaml`](compose.tencent.yaml) (see step 8b).

Create or edit `/etc/docker/daemon.json` (example — adjust mirrors to what works today):

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
```

Restart Docker:

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
docker info | rg -n "Registry Mirrors" || docker info
```

## 6) Get project code

```bash
sudo dnf install -y git || sudo apt-get install -y git
cd /opt
git clone <YOUR_REPO_URL> sector-flow
cd sector-flow
```

## 7) Configure environment

```bash
cp .env.example .env
```

Default root `.env` already fits compose startup. Adjust only if needed (passwords, ports, etc.).

For **production from TCR**, add to `.env` on the server (see root `.env.example`):

- `BACKEND_IMAGE` — e.g. `ccr.ccs.tencentyun.com/<namespace>/sector-flow-backend:<tag>`
- `FRONTEND_IMAGE` — e.g. `ccr.ccs.tencentyun.com/<namespace>/sector-flow-frontend:<tag>`
- Optional: `TIMESCALE_IMAGE` if you mirrored TimescaleDB to TCR (avoids Docker Hub on the CVM).

## 8) Build and start

### 8a) Build on the CVM (simplest; pulls base images from Hub/mirrors)

Uses only [`compose.yaml`](compose.yaml) (database port published for local `psql` from host; still keep security group closed on `5432`).

```bash
docker compose up -d --build
docker compose ps
```

### 8b) Production-style: pre-built images from TCR (recommended)

Build and push images from a machine with reliable registry access (CI, office, etc.), then on the CVM:

```bash
docker compose -f compose.yaml -f compose.tencent.yaml pull
docker compose -f compose.yaml -f compose.tencent.yaml up -d
docker compose -f compose.yaml -f compose.tencent.yaml ps
```

`compose.tencent.yaml` clears published `db` ports and uses `BACKEND_IMAGE` / `FRONTEND_IMAGE` instead of `build:`.

**Build hints (before `docker push` to TCR):**

- Backend: `docker build --platform linux/amd64 -t $BACKEND_IMAGE ./backend`
- Frontend: bake public API URL —  
  `docker build --platform linux/amd64 -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL=http://<CVM_PUBLIC_IP>:8000 -t $FRONTEND_IMAGE ./frontend`  
  (replace with your domain + TLS when fronted by Nginx.)

View logs:

```bash
docker compose logs -f backend
docker compose logs -f db
```

## 9) Verify service

- Frontend: `http://<CVM_PUBLIC_IP>:3000`
- Backend docs: `http://<CVM_PUBLIC_IP>:8000/docs`
- Health: `http://<CVM_PUBLIC_IP>:8000/health`

Verify TimescaleDB extension:

```bash
docker compose exec db psql -U sector_flow -d sector_flow -c "\dx"
```

## 10) Common operations

Restart:

```bash
docker compose restart
```

Pull latest code and redeploy:

```bash
git pull
docker compose up -d --build
```

If you use the TCR overlay (step 8b), rebuild/push images elsewhere, then on the CVM:

```bash
git pull
docker compose -f compose.yaml -f compose.tencent.yaml pull
docker compose -f compose.yaml -f compose.tencent.yaml up -d
```

Reset all data (destructive):

```bash
docker compose down -v
docker compose up -d --build
```

With TCR overlay:

```bash
docker compose -f compose.yaml -f compose.tencent.yaml down -v
docker compose -f compose.yaml -f compose.tencent.yaml up -d
```

## 11) Production hardening checklist

- Put Nginx/Caddy in front of `frontend` and `backend`.
- Expose only `80/443` publicly.
- Keep `5432` private.
- Enable TLS (Let's Encrypt) after domain + ICP requirements are satisfied.
- Add periodic database backups (`pg_dump` or volume snapshots).
