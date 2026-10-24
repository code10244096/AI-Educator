# Cursor 任务书：管理员用量统计——自定义时间段 + 全面测试打磨

> 背景：管理员（admin）在「用量统计」页（`frontend/src/pages/UsageStats.jsx`）查看每个模块（ocr/grade/lessonplan/variant 等）的调用次数和 token 消耗。后端 `backend/usage_api.py` 的 `/api/usage/summary` 等接口**已支持 `since`/`until` 参数（ISO 时间）**，前端目前只有固定区间（今天/7天/30天/全部，`RANGES` 常量）。本次任务：**加自定义时间段选择 + 补自动化测试 + 排查打磨**。只动下列相关文件。

## 1. 前端：自定义时间段（UsageStats.jsx）

- 在现有区间按钮组旁（或下方）加「自定义」入口：两个日期选择器（开始日期、结束日期，用 `<input type="date">`，Tailwind 样式与现有筛选一致）+「查询」按钮。
- 选中自定义区间后调用 summary/accounts 相关接口时带上 `since`（开始日 00:00:00）和 `until`（结束日 23:59:59），其余图表和表格按返回数据正常渲染；无数据的区间沿用现有的空态提示（参考 `historyHint` 的写法）。
- 校验：开始日期不能晚于结束日期，否则 Toast 提示且不请求。
- 切换固定区间时清空自定义选择；浏览器后退等场景下状态保持一致即可，不做复杂处理。

## 2. 测试（重点，请认真做）

### 2.1 后端测试

- 参照现有 `backend/tests/test_usage_stats.py` 的写法（先读它，跟随其 fixture 风格），在 `backend/tests/` 下补充 `test_usage_stats_range.py`：
  1. 造 3 条不同时间（如 3 天前、1 天前、现在）的调用记录（含 feature 与 prompt/completion tokens），断言 `since` 过滤后统计的 calls 和 total_tokens 精确等于预期值；
  2. 断言 `until` 单独过滤、`since`+`until` 组合过滤都正确；
  3. 断言按 feature 分组的次数与 token 加总与明细一致（排查前端图表与总数对不上的隐患）；
  4. 边界：空结果区间返回 0 而不是报错；非法时间格式返回 422。
- 若造数据需要用到现有测试辅助（`backend/tests/helpers.py`），直接复用。
- 运行：`cd backend && python -m pytest tests/test_usage_stats.py tests/test_usage_stats_range.py -v`，全部通过才算完成；若发现现有测试失败，如实报告，不要静默改断言。

### 2.2 前端冒烟

- `cd frontend && npm run build` 通过。

### 2.3 产品体检（你来当用户找毛病）

- 通读 UsageStats.jsx 的渲染逻辑，列出你发现的 3-5 个真实问题（如：切区间时反馈区块数据没跟着刷、token 单位换算不一致、加载态遮挡、移动端溢出、自定义区间未纳入历史提示等——以你实际读代码发现的为准），并在**不引入新依赖**的前提下把其中明确的 bug 修掉；拿不准的不改，写进最终回复让我判断。

## 验收标准

1. 管理员登录 → 用量统计页 → 选「2026-10-01 至 2026-10-15」→ 各模块次数/token 与该区间后端数据一致（可人工构造日志验证一次，写明方法）。
2. 新增后端测试文件通过，原有测试无新增失败。
3. 前端 build 通过。
4. 最终回复包含：改动清单、测试输出摘要、你发现并修复的问题列表、未修复但认为可疑的点。
