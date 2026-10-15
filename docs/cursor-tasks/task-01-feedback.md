# Cursor 任务书：体验版「使用改进意见」收集功能

> 交接方式：在 Cursor 聊天中输入「@docs/cursor-tasks/task-01-feedback.md 按这份任务书实现」。
> 本项目为 React 18 + Vite 5 + Tailwind 3.4 前端，Python FastAPI + SQLAlchemy 2 异步 + SQLite 后端。
> **只做本文件列出的改动，不要动 `backend/llm/`、`config.example.json` 等无关文件。**

## 需求背景

产品当前处于公测体验阶段：访客点「开始体验」即可获得体验账号（`is_guest` 用户，走 `POST /auth/enter`）。
需要收集体验客户（中小学教师）的改进意见：先对**常用问题做选择题**（多选），再留一个**自由文本**写具体意见。
体验账号和正式账号都要能提交。

## 前端改动

### 1. 新增反馈弹窗组件 `frontend/src/components/FeedbackDialog.jsx`

- 结构照抄现有 `frontend/src/components/ConfirmDialog.jsx`（遮罩 + 居中卡片 + 动画），样式用 Tailwind，与现有风格一致。
- 表单内容：
  - **选择题（多选 checkbox）**，选项写死在前端常量里：
    1. 教案不符合课标或教材版本
    2. 作业批改有误判 / 评分不准
    3. 手写识别（OCR）不准确
    4. 变式题难度或质量不合适
    5. 生成速度太慢
    6. 页面操作不方便
    7. 其他（选中后必须填写文本）
  - **自由文本 textarea**：「还有什么想告诉我们的？（选填，300 字以内）」，限制 300 字并显示字数。
  - 按钮：提交 / 取消。未选任何选项且文本为空时禁止提交。
- 提交中按钮置灰防重复点击；成功后用全局 `useToast().addToast('感谢反馈，我们会认真改进', 'success')` 提示并关闭弹窗、清空表单；失败用 `addToast(getErrorMessage(err), 'error')`。

### 2. API 层 `frontend/src/utils/api.js`

- 新增 `feedbackAPI.submit(payload)`，POST `/feedback`，body 为 `{ topics: string[], content: string, page: string }`，`page` 由前端取 `window.location.pathname`。沿用文件内现有 axios 实例与导出风格。

### 3. 入口

- 在 `frontend/src/components/Sidebar.jsx` 的菜单数组（第 23-27 行附近）末尾加一项「意见反馈」（icon 用 `lucide-react` 的 `MessageSquarePlus` 或类似），点击打开 `FeedbackDialog`（不走路由）。
- 入口对体验账号和正式账号都可见，不做权限区分。

## 后端改动

### 4. 数据表 `backend/models.py`

- 新增 `Feedback` 模型，照抄 `ClassInfo`（第 29-43 行）的写法：
  - `id` 主键；`topics = Column(Text)`（存 JSON 字符串数组）；`content = Column(Text, default="")`；`page = Column(String(200), default="")`；`user_id = Column(ForeignKey("users.id"))`；`created_at = server_default(func.now())`。
- 启动时自动建表（`Base.metadata.create_all` 已有机制），无需手写迁移。

### 5. 接口 `backend/routers/feedback.py`（新建）

- 照抄 `backend/routers/classes.py` 的「新建班级」模板（第 19-22 行请求体、第 86-93 行 POST 接口）：
  - `class FeedbackCreate(BaseModel): topics: list[str] = []; content: str = ""; page: str = ""`
  - `POST /feedback`：校验 `topics` 与 `content` 至少其一非空、`content` 截断到 300 字、单个选项文字截断到 50 字；写入 `Feedback` 表；返回 `{"ok": True}`。
- 在 `backend/api.py` 中 import 并 `business.include_router(feedback.router)`（参考第 22、31-37 行现有写法），挂进 `business` 路由器即自动获得登录鉴权，体验账号可提交。
- 轻量防刷：同一用户 60 秒内重复提交返回 429（可用内存字典记 user_id → 上次提交时间即可，不需要引入新依赖）。

### 6. 管理端查看（简单做）

- 加一个 `GET /feedback/list` 挂到管理员路由（参考 main.py 第 67 行 `usage_router` 的 `Depends(require_admin)` 模式），按时间倒序返回最近 200 条（含提交人 id、是否体验账号）。不需要做前端管理页面。

## 验收标准

1. 体验账号登录后，侧栏出现「意见反馈」，点击弹出表单。
2. 勾选 2 个选项 + 填写文本 → 提交成功出现 Toast；SQLite 中 `feedback` 表能看到对应记录（topics 为 JSON、page 为当前路径）。
3. 什么都不填时提交按钮不可用；选「其他」但不填文本时提交被前端拦截并提示。
4. `npm run build`（frontend）通过；`pytest backend/tests` 不引入新失败。
5. 全中文 UI 文案，语气符合教师用户习惯。
