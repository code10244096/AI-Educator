# Cursor 任务书：反馈功能补完——联系方式字段 + 工作台悬浮入口 + 管理端反馈区块

> 背景：仓库已有一版「使用改进意见」反馈功能（commit 6ac1058）：前端 `frontend/src/components/FeedbackDialog.jsx`（7 项多选 + 300 字意见，侧栏入口），后端 `backend/routers/feedback.py`（POST /feedback，60s 防刷）+ `models.py` 的 `Feedback` 表 + 管理员 `GET /feedback/list`。
> 本任务在现有实现上**增量补充**，不要推倒重写。不要改动无关文件。

## 1. 后端：Feedback 表加联系方式

- `backend/models.py` 的 `Feedback` 模型加列：`contact = Column(String(100), default="")`。
- 注意**线上已有数据库**：项目启动时有幂等补列迁移机制（参照 models.py / database.py 中其他表补列的现有写法），按同样方式给已有库补 contact 列，不要只改模型定义。
- `backend/routers/feedback.py` 的 `FeedbackCreate` 加 `contact: str = ""`，入库前截断到 100 字。其余校验逻辑不变。
- `GET /feedback/list` 的返回里带上 contact 字段。

## 2. 前端：FeedbackDialog 加联系方式输入框

- `frontend/src/components/FeedbackDialog.jsx`：在 textarea 下方加「联系方式（选填）」input，placeholder 写「微信或手机号，方便我们回访（选填）」，限 100 字。
- 提交 payload 加 `contact` 字段。不改变现有校验规则。

## 3. 前端：工作台悬浮反馈入口

- `frontend/src/pages/Workbench.jsx` 右下角加固定悬浮按钮「反馈」（圆形或胶囊形，lucide-react 图标 MessageSquarePlus，Tailwind 样式与项目现有风格一致，z-index 不遮挡现有抽屉/弹窗）。
- 点击打开同一个 `FeedbackDialog`。Workbench 页面自行引入组件并管理 open 状态，参考 Sidebar.jsx 现有用法。

## 4. 前端：管理端反馈区块

- `frontend/src/pages/UsageStats.jsx` 页面底部加「用户反馈」区块：拉取 `GET /feedback/list`，按时间倒序列表展示：时间、提交人（含是否体验账号）、勾选的问题项（标签样式）、意见内容、联系方式（无则显示 —）。
- **只在管理员身份下渲染**：参照该页面或项目里现有的管理员判断方式；普通教师不显示该区块（接口本身已有 require_admin，前端区块也要做身份判断，避免普通用户看到报错）。
- 空列表时显示「暂无反馈」。

## 验收标准

1. `git diff --stat` 只涉及：backend/models.py、backend/routers/feedback.py、frontend/src/components/FeedbackDialog.jsx、frontend/src/pages/Workbench.jsx、frontend/src/pages/UsageStats.jsx（以及 api.js 如需调整）。
2. 已有数据库启动后自动补上 contact 列，不报错。
3. 侧栏和工作台悬浮按钮都能打开反馈弹窗；填写联系方式提交后，数据库记录含 contact。
4. 管理员在 UsageStats 页能看到反馈列表；普通教师看不到该区块。
5. `cd frontend && npm run build` 通过。
