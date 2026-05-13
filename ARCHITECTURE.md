# 项目架构设计文档

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层 (React)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 作业批改页面 │  │  错题本页面  │  │ 教案生成页面 │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                      后端 API 层 (FastAPI)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │/api/grader  │  │/api/notebook│  │/api/lessonplan│        │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              统一 AI 模型调用客户端                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                │
│  ┌─────────────┐              ┌─────────────┐              │
│  │ SQLite 数据库 │              │  文件存储   │              │
│  │ (用户/作业/错题)│              │ (图片上传)  │              │
│  └─────────────┘              └─────────────┘              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       AI 服务层                               │
│  ┌─────────┐  ┌─────────  ┌───────────┐  ┌───────────┐   │
│  │ OCR 模型  │  │ 解题模型 │  │变式题生成  │  │ 教案生成   │   │
│  └─────────  └─────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 2. 核心模块设计

### 2.1 作业批改模块

**流程：**
1. 前端上传图片（支持多张）
2. 后端保存文件并返回临时路径
3. 调用 OCR 模型识别图片文字
4. 调用解题模型进行批改
5. 返回结构化批改结果
6. 前端展示结果和统计

**API 设计：**
```python
POST /api/grader/upload
- Input: files[], reference_answer, subject
- Output: submission_id, ocr_result, grading_result

GET /api/grader/{submission_id}
- Output: 完整批改详情
```

**数据模型：**
```python
HomeworkSubmission:
  - id: int
  - assignment_id: int (FK)
  - user_id: int (FK)
  - image_paths: JSON
  - ocr_result: Text
  - grading_result: JSON
  - wrong_count: int
  - score: float
  - status: str
  - created_at: datetime
```

### 2.2 错题本模块

**流程：**
1. 上传错题图片
2. OCR 识别题目内容
3. 提取知识点标签
4. 调用 AI 生成变式题
5. 保存到错题数据库
6. 支持筛选和复习

**API 设计：**
```python
POST /api/notebook/upload
- Input: file, knowledge_point, subject
- Output: question_id, variant_questions

GET /api/notebook/list
- Input: knowledge_point, subject, limit, offset
- Output: questions[]

POST /api/notebook/{id}/mastered
- Output: success message
```

### 2.3 教案生成模块

**流程：**
1. 输入课题名称和参数
2. 构建教案生成 Prompt
3. 调用 AI 生成教案内容
4. Markdown 格式渲染
5. 支持导出 Word/PDF

**API 设计：**
```python
POST /api/lessonplan/generate
- Input: title, period, student_level, requirements
- Output: lesson_plan_id, content

GET /api/lessonplan/{id}
- Output: 完整教案详情
```

## 3. 数据库设计

### 3.1 ER 图

```
User (用户)
  ├─ HomeworkSubmission (作业提交)
  ├─ WrongQuestion (错题)
  └─ LessonPlan (教案)

Class (班级)
  └─ HomeworkAssignment (作业布置)
      └─ HomeworkSubmission (作业提交)
```

### 3.2 核心表结构

详见 `backend/models.py`

## 4. AI 模型集成

### 4.1 统一客户端

```python
class AIClient:
  - ocr_image(image_path) -> str
  - grade_homework(ocr_result, reference_answer) -> Dict
  - generate_variant_questions(question, knowledge_point) -> List
  - generate_lesson_plan(topic, period, level) -> str
```

### 4.2 模型配置

支持通过环境变量切换：
- AI_API_BASE_URL
- AI_MODEL
- OCR_MODEL

## 5. 前端架构

### 5.1 组件结构

```
src/
├── components/
│   ├── Navbar.jsx       # 导航栏
│   └── ClassStats.jsx   # 班级统计组件
├── pages/
│   ├── HomeworkGrader.jsx    # 作业批改
│   ├── WrongNotebook.jsx     # 错题本
│   └── LessonPlanGenerator.jsx # 教案生成
├── utils/
│   └── api.js            # API 封装
└── store/
    └── index.js          # 状态管理
```

### 5.2 状态管理

使用 Zustand 进行全局状态管理：
- 当前页面路由
- 用户信息
- 主题设置

## 6. 部署架构

### 6.1 Docker 部署

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: [uploads, data]
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

### 6.2 生产环境建议

1. 使用 Nginx 反向代理
2. 配置 HTTPS
3. 使用 PostgreSQL 替代 SQLite
4. 配置 Redis 缓存
5. 使用对象存储（如 OSS）存储图片

## 7. 安全考虑

1. JWT 用户认证（待实现）
2. 文件上传大小限制
3. 文件类型白名单
4. API 限流（待实现）
5. CORS 跨域配置
6. 敏感信息环境变量隔离

## 8. 扩展计划

### 8.1 短期
- [ ] 用户认证系统
- [ ] 作业布置功能
- [ ] 成绩导出 Excel

### 8.2 中期
- [ ] 多科目支持（物理、化学）
- [ ] 学情分析报告
- [ ] 家长端小程序

### 8.3 长期
- [ ] 自适应学习推荐
- [ ] 大规模并发支持
- [ ] 私有化模型部署
