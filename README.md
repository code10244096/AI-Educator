# AI 教学助手系统

一个基于 AI 的智能教学辅助平台，提供作业批改、错题本管理、教案生成三大核心功能。

## ✨ 功能特性

### 1. AI 作业批改助手
- 📸 支持多张图片上传
- 🔍 自动 OCR 识别题目和答案
- ✅ 智能批改并给出解析
- 📊 班级统计分析
- 📈 高频错题统计

### 2. AI 错题本管家
- 📷 拍照录入错题
- 🏷️ 按知识点筛选
- 💡 自动生成变式题
- ✅ 标记已掌握状态
- 📜 错题历史记录

### 3. AI 教案生成
- 📝 自定义课题名称
- ⏱️ 选择课时数和学生基础
- 🎯 添加额外要求
- 📄 一键生成完整教案
- 💾 支持导出 Word/PDF

## 🛠️ 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **SQLAlchemy** - 异步 ORM
- **SQLite** - 开发数据库
- **AI Model API** - OCR、解题、教案生成

### 前端
- **React 18** - UI 框架
- **Vite** - 快速构建工具
- **Tailwind CSS** - 样式框架
- **React Router** - 路由管理
- **Zustand** - 状态管理
- **Axios** - HTTP 客户端

### 部署
- **Docker** - 容器化
- **Docker Compose** - 服务编排

## 🚀 快速开始

### 方法一：Docker Compose（推荐）

1. **克隆仓库**
```bash
git clone https://github.com/YOUR_USERNAME/ai-teaching-assistant.git
cd ai-teaching-assistant
```

2. **配置环境变量**
```bash
cp backend/.env.example backend/.env
# 编辑 .env 文件，填入你的 AI API 密钥
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问应用**
- 前端：http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档：http://localhost:8000/docs

### 方法二：本地开发

#### 后端
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

## 📁 项目结构

```
ai-teaching-assistant/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI 应用入口
│   ├── config.py        # 配置管理
│   ├── database.py      # 数据库连接
│   ├── models.py        # 数据模型
│   ├── api.py           # API 路由
│   ├── ai_client.py     # AI 模型客户端
│   └── requirements.txt # Python 依赖
│
├── frontend/            # 前端应用
│   ├── src/
│   │   ├── App.jsx     # 主应用组件
│   │   ├── main.jsx    # 入口文件
│   │   ├── components/ # 可复用组件
│   │   ├── pages/      # 页面组件
│   │   ├── utils/      # 工具函数
│   │   └── store/      # 状态管理
│   └── package.json    # Node 依赖
│
├── docker-compose.yml   # Docker 编排
├── README.md            # 项目文档
└── .gitignore          # Git 忽略文件
```

## 📖 API 接口

### 作业批改
- `POST /api/grader/upload` - 上传作业并批改
- `GET /api/grader/{submission_id}` - 获取批改结果

### 错题本
- `POST /api/notebook/upload` - 录入错题
- `GET /api/notebook/list` - 获取错题列表
- `POST /api/notebook/{question_id}/mastered` - 标记已掌握

### 教案生成
- `POST /api/lessonplan/generate` - 生成教案
- `GET /api/lessonplan/{plan_id}` - 获取教案详情

### 班级统计
- `GET /api/class/stats` - 获取班级统计信息

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| AI_API_KEY | AI 模型 API 密钥 | 必填 |
| AI_API_BASE_URL | AI 模型 API 地址 | https://api.openai.com/v1 |
| AI_MODEL | 主模型名称 | gpt-4 |
| OCR_MODEL | OCR 模型名称 | gpt-4-vision-preview |
| DATABASE_URL | 数据库连接字符串 | sqlite+aiosqlite:///./teaching_assistant.db |

## 📝 使用示例

### 1. 作业批改
1. 访问 http://localhost:3000
2. 拖拽或点击上传作业图片
3. （可选）填写参考答案
4. 点击"开始批改"
5. 查看详细结果和解析

### 2. 错题本
1. 切换到"错题本"页面
2. 点击"上传"按钮
3. 选择错题图片
4. 选择知识点分类
5. 查看生成的变式题

### 3. 教案生成
1. 切换到"教案生成"页面
2. 填写课题名称
3. 选择课时数和学生基础
4. 添加额外要求
5. 点击"生成教案"

## 🔧 开发计划

- [ ] 用户认证系统
- [ ] 多科目支持（物理、化学）
- [ ] 批量作业批改
- [ ] 学情分析报告
- [ ] 移动端适配
- [ ] 离线模式

## 📄 License

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请通过 Issue 或邮件联系。

---

**Made with ❤️ by AI Teaching Assistant Team**
