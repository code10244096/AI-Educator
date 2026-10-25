# Cursor 任务书 task-08：题库功能支持新学科（语文/英语/科学）

> 背景：E:\AI-Educator 是「AI 教学助手」全栈项目（backend/ FastAPI + SQLite，frontend/ React）。
> 题库表 question_bank 已扩到 27 万行，新增大量 **语文（小学 7748）/ 英语（小初高 1.2 万）/ 科学（小学 3892）** 题（来源 import_open_round4.py）。
> 你负责调查并补齐产品里「学科选项写死数学」的地方，让新学科题能被浏览、检索、用于生成。
> **约束**：不要 git commit；不要动 backend/tests/conftest.py、tests/fakes.py（另一个 agent 在用）；不要动 backend/models.py（另一个 agent 在用）。后端如需改，只改题库相关 router/service。

## 步骤

1. 全局搜索学科硬编码：在 frontend/src 与 backend/ 搜 `"数学"`、`'数学'`、subject 相关的下拉/选项/常量（如 SUBJECTS、subjects、subjectOptions），重点看题库浏览页、组卷/出题入口、教案生成的学科选择、RAG 检索（rag_retriever.py 是否按学科过滤）。
2. 逐处判断：是产品上有意只支持数学（如某些模块只做了数学），还是漏改。把「用户能选到语文/英语/科学但后续流程报错或查不到题」的断点列出来。
3. 修复断点：学科选项数据源统一（建议前端从常量/接口取，后端校验合法学科集合），保证选了新学科后：题库列表能出数据、检索能命中、生成流程不报错。
4. 验证（你能跑 shell，用 py / npm）：
   - `cd E:\AI-Educator\backend && py -m pytest tests --ignore=tests/acceptance -q` 不新增失败（基线 275 passed）
   - `cd E:\AI-Educator\frontend && npm run build` 通过

## 最终回复格式

硬编码点清单（文件:行 + 处理与否及理由）、改动文件清单、两组验证输出、遗留断点（有意不做数学以外学科的模块要明确列出）。
