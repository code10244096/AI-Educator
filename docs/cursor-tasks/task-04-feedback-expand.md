# Cursor 任务书：反馈弹窗——逐项展开意见框 + 弹窗滚动

> 背景：现有 `frontend/src/components/FeedbackDialog.jsx`（7 项多选 + 底部统一意见框 + 联系方式），后端 `backend/routers/feedback.py` 的 topics 是字符串数组（JSON 入库）。本次做交互升级，**只动下列文件，不要碰无关代码**。

## 1. 交互改动（FeedbackDialog.jsx）

- **勾选即展开**：每个问题选项是一个卡片，勾选该选项后，卡片内部下方平滑展开一个独立文本框，placeholder「具体说说这个问题（选填）」，限 200 字；取消勾选时收起并清空该框内容。
- 「其他」选项同样展开文本框，但**必填**（沿用现有校验：选了其他没填则 Toast 拦截）。
- 底部保留通用的「还有什么想告诉我们的？」textarea（300 字）和「联系方式（选填）」，保持不变。
- **弹窗滚动**：头部（标题区）和底部按钮栏固定不动；中间内容区 `overflow-y-auto`，弹窗整体最大高度约 85vh，内容超高时右侧出现滚动条可滚动；内容区右侧留出滚动条位置避免文字被遮挡。
- 展开/收起加简单过渡动画（高度或 opacity 均可，参考项目现有动画风格）。

## 2. 提交数据结构（前后端同步改）

- 前端提交 payload 的 `topics` 从字符串数组改为对象数组：`topics: [{ name: "作业批改有误判 / 评分不准", detail: "用户填的具体内容（可为空串）" }]`。
- 后端 `backend/routers/feedback.py`：`FeedbackCreate.topics` 改为 `list[TopicInput]`，`TopicInput` 含 `name: str`、`detail: str = ""`；校验 name 截断 50 字、detail 截断 200 字；「topics 至少一项或 content 非空」的总校验不变；仍 JSON 入库（表结构不用动）。
- `GET /feedback/list` 原样返回 topics。

## 3. 管理端展示（UsageStats.jsx 用户反馈区块）

- 渲染 topics 时**兼容两种形态**：字符串（旧数据）直接显示标签；对象（新数据）显示 name 标签，若 detail 非空则在标签下方用小一号灰色文字展示 detail。

## 验收标准

1. 勾选任一选项，卡片内展开对应文本框；取消勾选收起且内容清空；「其他」不填文本提交被拦截并提示。
2. 选项全部勾上 + 各填内容时，弹窗头部和底部按钮固定，中间区域可滚动，右侧有滚动条。
3. 提交后数据库 feedback 表 topics 为对象数组 JSON，detail 正确落库。
4. UsageStats 反馈区块对新旧两种数据都能正常渲染。
5. `cd frontend && npm run build` 通过。
