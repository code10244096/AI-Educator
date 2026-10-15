# Cursor 任务书：AI 教学助手打磨（2026-10-15）

> 背景：本仓库是已上线的 AI 教学助手（FastAPI + React/Vite，生产部署 https://ai-samrt-tutor-educator.cn）。
> 以下任务基于 2026-10-15 模型对照实验的结论（见 `qa-reports/model-eval-2026-10-15/模型对照实验报告.md`）。
> 请按任务顺序逐项实施，**不要改动任务清单以外的文件**；每个任务完成后不要自行 git commit，由验收方统一提交。

---

## 任务 1：变式题主模型切换为 deepseek-v4.1-flash

文件：`backend/llm/__init__.py`

- `DEFAULT_MODELS["variant"]` 从 `"gemini-3.1-pro-preview"` 改为 `"deepseek-v4.1-flash"`。
- `DEFAULT_FALLBACKS["variant"]` 从 `["deepseek-v4-pro"]` 改为 `["gemini-3.1-pro-preview"]`。
- `DEFAULT_FALLBACKS["ocr"]` 从 `["deepseek-v4.1-flash"]` 改为 `["qwen3-vl-plus"]`（实验实测该视觉模型识别准确且最省 token；注意 deepseek-v4.1-flash 是纯文本模型，不能做 OCR 兜底，这是一个现存的配置错误）。
- 更新第 12~13 行的注释，说明 2026-10-15 实测结论（变式 flash 快 13 倍且数学全对；OCR 兜底 qwen3-vl-plus）。

## 任务 2：变式题 prompt 强化 LaTeX 格式

文件：`backend/ai_client.py` 的 `generate_variant_questions`

现状问题：实验发现多个模型返回的变式题用纯文本数学式（`f(x)=x^3-6x`）而不是 LaTeX，前端 KaTeX 无法渲染。

改动：在该方法构造的 prompt 中增加明确格式要求和一个 few-shot 示例，例如：

```
4. question_text 和 answer 中的数学公式必须用 LaTeX 表示，行内公式用 \( \) 包裹，例如：\( f(x)=x^3-3x \)。
错误示例：f(x)=x^3-3x（纯文本，前端无法渲染）
正确示例：\( f(x)=x^3-3x \)，递增区间为 \( (-\infty,-1) \) 和 \( (1,+\infty) \)
```

## 任务 3：无参考答案批改时，分数显示「待复核」而非 0 分

背景：当作业没有参考答案时，批改模型会把所有题判为 `is_correct=false` 且 `needs_review=true`，后端按「正确题数/总题数」算出 0 分，前端直接显示 0 分，给老师造成误导。

改动（前后端各一处）：

- 后端 `backend/jobs.py` 的 `compute_score`：若所有题目 `needs_review` 全为 true 且没有参考答案依据（即 questions 非空且每题 needs_review），在返回 dict 中增加字段 `"score_pending": true`（其余字段照常计算）。注意保持现有调用方兼容。
- 前端：找到展示批改分数的页面（批改详情/作业详情，搜索 `score` 的使用处），当 `grading_result.score_pending === true` 时，分数区域显示「待复核」文案（用现有样式，如灰色徽章），不显示 0 分。其余情况不受影响。

## 任务 4：体验反馈功能（使用改进意见收集）

### 4.1 后端

- `backend/models.py` 新增 `Feedback` 表：`id`、`teacher_id`（外键 users.id，可空）、`issues`（JSON 数组，存多选的问题项）、`suggestion`（TEXT）、`contact`（可空字符串）、`page`（提交时所在页面，可空）、`created_at`（UTC，风格与现有表一致）。同步在 `database.py` 的建表逻辑里登记（参照现有表的做法，注意线上已有数据库需要兼容——项目现有的迁移方式是什么就跟随什么，若是 create_all 自动建表则无需额外迁移脚本）。
- `backend/main.py`（或现有路由文件，跟随项目结构）新增：
  - `POST /api/feedback`：接收 `{issues: string[], suggestion: string, contact?: string, page?: string}`，登录用户带 teacher_id，未登录也允许提交（体验版场景）。校验：issues 非空或 suggestion 非空，至少一项；长度上限 suggestion 2000 字、contact 100 字。返回 `{ok: true}`。
  - `GET /api/feedback`：仅管理员/开发者可见（跟随项目现有的权限判断方式），返回最近 200 条，含提交人姓名与时间，按时间倒序。

### 4.2 前端

- 新增反馈入口组件 `frontend/src/components/FeedbackModal.jsx`：弹窗表单，包含：
  - 「遇到的问题（可多选）」复选：`批改结果不准确` / `作业照片识别不清` / `响应速度慢` / `教案不合用` / `找不到想要的功能` / `其他`
  - 「改进建议」textarea（placeholder：比如希望增加什么功能？哪里用着不顺手？）
  - 「联系方式（选填）」input
  - 提交按钮，提交成功用现有 Toast 提示「感谢反馈，我们会认真阅读」；失败提示重试。
  - 复用现有 Modal/Toast/按钮样式，风格与 `ConfirmDialog.jsx` 一致。
- 入口放两处：
  1. 设置页（`Settings.jsx`）加一张「使用反馈」卡片，点击打开弹窗；
  2. 工作台页（`Workbench.jsx`）右下角加一个固定悬浮按钮「反馈」。
- 管理端查看：`UsageStats.jsx` 页面底部加「用户反馈」区块，拉取 `GET /api/feedback`，列表展示时间、提交人、勾选的问题、建议内容、联系方式（无则显示 —）。如果该页现有权限不满足（普通教师也能看用量页），则反馈区块只在管理员身份下渲染。

### 4.3 约束

- 不要引入新依赖；样式用项目现有的 CSS 方案。
- 后端字段名、接口路径严格按上面定义；前端用现有的 api 封装（看现有页面怎么调接口就怎么调）。
- 改完后运行 `cd frontend && npm run build` 确认构建通过，把构建结果（成功/报错）写进你的最终回复。

---

## 验收方会用到的检查点（供你自测）

1. `git diff --stat` 只包含上述文件及新增文件。
2. `cd frontend && npm run build` 通过。
3. 后端 `python -c "import models"`（在 backend 目录、有依赖的环境下）不报错。
