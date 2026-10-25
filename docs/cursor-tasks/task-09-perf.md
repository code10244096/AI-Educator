# Cursor 任务书 task-09：question_bank 27 万行查询性能与索引

> 背景：E:\AI-Educator，FastAPI + SQLite（aiosqlite）。question_bank 已有 27 万行且会继续增长。
> 你负责调查并改善题库相关查询性能。**约束**：不要 git commit；不要动 backend/tests/conftest.py、tests/fakes.py；前端文件不要动（另一个 agent 在用）。可以改 backend/models.py、rag_retriever.py、题库 router、迁移脚本。

## 步骤

1. 读 backend/models.py 的 QuestionBank 定义：现有索引有哪些？常用过滤字段（subject/education_level/grade/question_type/difficulty/knowledge_points？）有没有索引？
2. 读 rag_retriever.py 和题库相关 router：检索 SQL 是精确匹配还是 LIKE？是否全表扫？分页怎么做（LIMIT/OFFSET 还是 keyset）？
3. 用数据验证：本地 backend/teaching_assistant.db 有 27 万行真实数据。写个计时脚本（放 backend/scripts_bench.py 或临时文件，跑完可留档）对比优化前后的典型查询耗时（如按 subject+grade 过滤、按 knowledge_points 搜索、随机翻页）。
4. 实施优化（按收益排序，至少做前两项）：
   - 缺的单列/复合索引（SQLite 用 CREATE INDEX IF NOT EXISTS，走项目现有迁移机制；先找项目怎么管迁移——搜 Alembic 或 init_db 里的 CREATE INDEX）
   - LIKE 前缀搜索确认有索引可用；全文需求评估 FTS5 是否值得（值得就做，注意中文分词问题——没分词就用 FTS5 的 simple tokenizer 或保持 LIKE，写清取舍）
   - 深分页改 keyset 或限制最大 OFFSET
5. 加测试：backend/tests/ 新增 test_questionbank_perf.py——验证索引存在（查 sqlite_master）、验证典型查询有 LIMIT、迁移幂等（重复执行不报错）。测试不得依赖 27 万真实数据（用小表验证结构）。
6. 验证：`cd E:\AI-Educator\backend && py -m pytest tests --ignore=tests/acceptance -q` 不新增失败（基线 275 passed）。

## 最终回复格式

现状索引清单、发现的慢查询（附计时数据）、做的优化与未做的取舍、迁移方式说明、测试输出、风险点。
