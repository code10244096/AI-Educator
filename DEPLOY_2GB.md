# AI 教学助手 部署指南（2 核 2GB Linux 云服务器）

> 适用：单所学校、≤20 名教师（SQLite + 每日备份）。一条命令 `docker compose up -d --build` 启动；对公网只开放 80/443，后端端口不对外。
> 本文与 `docker-compose.yml`、`.env.example`、`scripts/backup.sh`、`scripts/restore.sh` 保持一致，改动其中任何一个请同步更新本文。

## 目录

1. 准备服务器
2. 获取代码
3. 配置 `.env`（密钥只放这里）
4. 启动服务
5. 开通账号（管理员 / 教师）
6. 启用 HTTPS（正式给老师使用前必须完成）
7. 每日备份与恢复
8. 升级
9. 日常运维与常见问题

---

## 1. 准备服务器

- 系统：Ubuntu 22.04 / Debian 12 等常见 Linux 发行版
- 配置：2 核 CPU、2GB 内存、≥40GB 磁盘
- 安全组 / 防火墙：**只放行 22（SSH）、80、443**

```bash
# 安装 Docker（含 docker compose 插件）
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version

# 2GB 内存建议加 2GB Swap，防止高峰期 OOM
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 2. 获取代码

```bash
apt install -y git sqlite3        # sqlite3 用于在线备份（没有也可以，备份脚本会改用 python3）
cd /opt
git clone <仓库地址> ai-teaching
cd ai-teaching
```

以下命令都在部署目录 `/opt/ai-teaching`（`docker-compose.yml` 所在目录）执行。

## 3. 配置 `.env`

```bash
cp .env.example .env
chmod 600 .env
openssl rand -hex 32              # 生成一段随机字符串，填到 JWT_SECRET
vi .env
```

必须填写的配置项：

| 配置项 | 说明 |
|---|---|
| `JWT_SECRET` | 会话签名密钥，**至少 32 位随机字符串**。未设置或仍是示例值时后端拒绝启动（日志提示“生产环境必须设置 JWT_SECRET”） |
| `LLM_API_KEY` | 大模型网关的 API Key。生产禁止模拟模式：没有有效 Key 时后端拒绝启动 |
| `CORS_ORIGINS` | 部署域名，如 `https://ai.your-school.cn`（逗号分隔）。前后端经 nginx 同域访问时可留空 |

可选配置项（有默认值）：

| 配置项 | 默认 | 说明 |
|---|---|---|
| `LLM_BASE_URL` | `https://yibuapi.com/v1` | OpenAI 兼容接口地址 |
| `LLM_MODEL_OCR` / `_GRADE` / `_VARIANT` / `_LESSONPLAN` | 见 `.env.example` | 分功能模型 |
| `SESSION_EXPIRE_MINUTES` | `10080`（7 天） | 登录有效期 |
| `GRADING_CONCURRENCY` | `4` | 全局同时批改的份数（2GB 服务器不建议调高） |
| `DAILY_GRADING_QUOTA` | `300` | 每位老师每天最多提交的批改份数 |
| `LLM_LOG_REQUEST_CONTENT` | `true` | 模型调用日志是否记录原文（含学生作业内容），隐私要求高时设为 `false` |

以下由 `docker-compose.yml` 固定，**不要**在 `.env` 里改：`APP_ENV`（固定为 `production`）、`SEED_DEMO_DATA`（固定为 `false`）、`DATABASE_URL`、`UPLOAD_DIR`、`API_OUTPUT_ROOT`。

> `.env` 含密钥，已被 `.gitignore` 和 `.dockerignore` 排除，不会进 git 仓库，也不会打进镜像。请另外妥善保存一份。

生产环境的其他安全设置（自动生效）：关闭 `/docs`、`/redoc`、`/openapi.json`；不打印 SQL；跨域只放行 `CORS_ORIGINS`；会话 Cookie 带 `Secure`（因此必须用 HTTPS 访问才能登录，见第 6 节）；不播种任何演示数据。

## 4. 启动服务

```bash
mkdir -p data uploads logs nginx/ssl backups
docker compose up -d --build
docker compose ps                  # 两个容器都应为 running (healthy)
docker compose logs -f backend     # 看到 Application startup complete 即正常
curl -s http://127.0.0.1/health    # {"status":"healthy"}
```

数据位置（都在宿主机上，重建容器不会丢）：

| 宿主机目录 | 内容 |
|---|---|
| `./data/teaching_assistant.db` | 数据库 |
| `./uploads/` | 学生作业照片等原始文件 |
| `./logs/` | 模型调用记录（`logs/api_runs/`）、备份日志 |

后端容器只在 docker 内部网络暴露 8000 端口，宿主机上 `ss -lnt` 只能看到 80/443（和 22）。

## 5. 开通账号

不开放注册，所有账号由管理员在服务器上用命令开通：

```bash
# 管理员账号（可以查看“用量统计”）
docker compose exec backend python manage.py create-user --username 13800000000 --name 信息中心张老师 --role admin

# 教师账号（账号用手机号或工号）
docker compose exec backend python manage.py create-user --username 13800000001 --name 王老师 --school 某某中学
```

命令会打印一行 `初始密码: xxxxxxxxxx`，**只显示这一次**，请当面交给老师。老师首次登录后必须设置自己的新密码（≥8 位，同时包含字母和数字）。

其他账号命令：

```bash
docker compose exec backend python manage.py list-users                               # 查看所有账号
docker compose exec backend python manage.py reset-password --username 13800000001    # 老师忘记密码：重置（打印新初始密码）
docker compose exec backend python manage.py disable-user --username 13800000001      # 老师离职：停用（数据保留）
docker compose exec backend python manage.py enable-user --username 13800000001       # 恢复
```

**从旧版本升级、库里已有历史数据时**：旧数据没有归属教师，开通账号后执行一次（幂等，重复执行不会改动已有归属，不删任何数据）：

```bash
docker compose exec backend python manage.py assign-orphans --username 13800000001
```

登录失败 10 次（5 分钟内）会锁定该账号 15 分钟；急用时可以 `docker compose restart backend` 解除。

## 6. 启用 HTTPS（必须）

会话 Cookie 带 `Secure`，浏览器只会在 HTTPS 下发送——用 `http://` 访问时登录不上，这是预期行为。

1. 准备证书（任选其一）：
   - 有域名：云厂商免费证书，或 Let's Encrypt（`certbot certonly --standalone -d ai.your-school.cn`，申请前先 `docker compose stop frontend`）。
   - 暂时没有域名、仅内测：自签证书
     `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -subj "/CN=ai-teaching"`
2. 把证书放到 `nginx/ssl/fullchain.pem` 与 `nginx/ssl/privkey.pem`。
3. `cp frontend/nginx-https.conf.example nginx/https.conf`，把其中两处 `server_name` 改成你的域名。该样例已包含 `listen 443 ssl`、HTTP→HTTPS 跳转、HSTS 与安全响应头、`client_max_body_size 100m`、`/api` 300 秒超时。
4. `docker compose -f docker-compose.yml -f docker-compose.https.yml up -d`。之后用 `scripts/deploy.sh` 升级时，只要证书和 `nginx/https.conf` 还在，会自动带上这份 HTTPS 配置。
5. 浏览器访问 `https://你的域名`。

> 只在内网临时用 HTTP 测试时，可以在 `.env` 加 `COOKIE_SECURE=false`（正式使用前务必删掉）。

上传限制：nginx 允许单次请求 100MB、`/api` 读写超时 300 秒；后端单个文件 ≤10MB、单份作业 ≤10 个文件。

## 7. 每日备份与恢复

### 备份

`scripts/backup.sh`：SQLite 在线备份（`.backup`，服务运行中也能得到一致副本并做完整性校验）+ 打包 `uploads/`，按时间命名存到 `backups/`，**保留最近 14 天**。

```bash
bash scripts/backup.sh            # 手动执行一次，确认输出“备份完成”
ls backups/                       # 20260926_023000/ 下有 teaching_assistant.db、uploads.tar.gz
```

设置每天 02:30 自动备份（`crontab -e`）：

```
30 2 * * * cd /opt/ai-teaching && bash scripts/backup.sh >> logs/backup.log 2>&1
```

建议再把 `backups/` 定期同步到另一台机器或对象存储（服务器整体损坏时本机备份也会丢）。可用 `BACKUP_DIR=/mnt/backup bash scripts/backup.sh` 指定备份目录，`KEEP_DAYS` 调整保留天数。

### 恢复

```bash
bash scripts/restore.sh backups/20260926_023000
```

脚本会：停止后端 → 把当前 `data/teaching_assistant.db`、`uploads/` 改名为 `*.before-restore-<时间>`（不删除）→ 用备份覆盖 → 启动后端。核对数据无误后再手动删除 `*.before-restore-*`。

### 恢复演练（上线前做一次）

```bash
bash scripts/backup.sh
B=$(ls -d backups/20* | tail -1)
docker compose stop backend
mv data data.drill && mv uploads uploads.drill           # 模拟数据丢失
bash scripts/restore.sh "$B" --yes
docker compose ps && curl -s http://127.0.0.1/health     # 登录后核对班级、作业、原始照片都在
rm -rf data.drill uploads.drill
```

## 8. 升级

代码推到 GitHub 的 `feat/ai-teaching-launch` 分支后，在服务器上执行一条命令。脚本会克隆该分支，覆盖程序文件，并保留 `.env`、数据库、上传文件、日志和 HTTPS 证书，然后重建容器。

```bash
bash /opt/ai-teaching/scripts/deploy.sh
```

换分支或仓库时：`DEPLOY_BRANCH=main bash /opt/ai-teaching/scripts/deploy.sh`。

数据库在启动时自动补齐新字段（只加不删）。如果新版本启动异常，用第 7 节的恢复步骤回到升级前的备份，再把 `DEPLOY_BRANCH` 指回上一版所在分支重新部署。

## 9. 日常运维与常见问题

| 场景 | 处理 |
|---|---|
| 查看状态 / 内存 | `docker compose ps`、`docker stats`（后端内存上限 1GB，前端 256MB） |
| 查看日志 | `docker compose logs --tail=200 backend` |
| 后端拒绝启动，日志提示“生产环境必须设置 JWT_SECRET / LLM_API_KEY” | 按第 3 节补全 `.env` 后 `docker compose up -d` |
| 登录总提示“登录已过期” / 登录后又回到登录页 | 用了 `http://` 访问：按第 6 节启用 HTTPS |
| 上传照片报“文件过大” | 单个文件 ≤10MB；手机照片请用普通画质 |
| 模型用量 | 管理员登录后访问 `/usage` 页面（教师看不到该菜单） |
| 清理 Docker 旧镜像 | `docker image prune -f` |

本版本不再包含：演示数据、`dataset/` 测试集挂载、后端 8000 端口对外映射。
