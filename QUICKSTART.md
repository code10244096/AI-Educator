# 快速启动脚本

## Windows

### 启动后端
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 配置 API 密钥
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 启动前端
```bash
cd frontend
npm install
npm run dev
```

## 使用 Docker（推荐）

```bash
# 配置环境变量
cp backend\.env.example backend\.env
# 编辑 .env 配置 API 密钥

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问：
- 前端：http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档：http://localhost:8000/docs
