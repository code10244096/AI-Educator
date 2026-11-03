# Cursor 任务书 task-16：题库页极简化（只显示本学科）

> 产品背景见 qa-reports/2026-11-03-题库产品分析.md。只改 `frontend/src/pages/BankBrowse.jsx`，后端与 RAG 不动。不要 git commit。

## 改动（全部在 BankBrowse.jsx）

1. **移除学科 Tab 区**：删除 visibleSubjects 的计算与整段学科 Tab 渲染（含 `role="tablist"` 的 div）。`pickedSubject` 状态及切换逻辑一并移除。
2. **学科固定为本学科**：subject 直接取 `user?.subject`，若不在 BANK_SUBJECTS（语文/数学/英语/科学）内则回退「数学」。注意 BANK_SUBJECTS 的引入路径参照现有 `../utils/stageSubjects`。
3. **标题体现本学科**：页头副标题「按学科浏览、检索题目，用于教案生成参考」改为「{subject}题库 · 检索题目，用于教案生成参考」；左侧列表标题仍保留 subject · 学段显示。
4. **移除教学提示区块**：删除 `{detail.teaching_tips ? (...)}` 整段渲染（约 373-378 行）。common_mistakes（常见错误）保留。
5. **学段下拉保留**，默认用户学段不变；搜索、分页、详情其余部分不动。
6. 顶部「去个人资料填写任教学段学科」提示保留。
7. 本学科+本学段无题时空态文案改为「你的学科在当前学段下暂无题目，可切换学段或搜索其他关键词」。

## 验收
- 高中数学老师进入题库：页面无学科 Tab、无任何其他学科名称，只看到数学题。
- 详情无「教学提示」区块。
- `cd frontend && ./node_modules/.bin/vite build` 通过。
