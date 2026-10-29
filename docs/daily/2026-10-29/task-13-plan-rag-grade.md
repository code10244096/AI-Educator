# task-13：教案生成参考题库内容（按学科 + 年级精准匹配）

## 背景（已实现，勿重复造轮子）

- 生产题库 `question_bank` 271,194 行，关键列：`subject`（有索引）、`education_level`（小学/初中/高中/大学，有索引）、`grade`（整数 1-12，可空）、`question_text`、`answer`、`solution`、`knowledge_points`(JSON)、`difficulty`。
- 教案生成已有基础 RAG：`backend/jobs.py` 的 `retrieve_question_context(db, title, subject, education_level)` → `rag_retriever.QuestionRetriever.keyword_search`（subject + education_level 等值过滤，**全标题 LIKE %title%**，limit 8）→ `format_for_rag` 文本 → `ai_client.generate_lesson_plan(question_bank_context=...)`（prompt 落点在 `ai_client.py:385-390`）→ 结果数存 `lesson_plans.retrieved_questions_count`。
- `LessonPlan` 模型（models.py:166-183）已有 `subject` 列，**没有 grade 列**；`User` 有 `education_stage` 但没有年级；年级目前只存在于 `classes.grade`（字符串如"高三"）。
- `education_level` 分布：小学 256,056 / 高中 6,918 / 初中 5,112 / 大学 3,108。命中样例：`秋天的雨`×小学语文=6 题，`一次函数`×初中数学=32 题。

## 缺口（本任务要解决的）

1. **不区分年级**：题库有 `grade` 列但检索完全没用到；教案生成表单也没有年级入参。
2. **全标题 LIKE 太脆**：标题不含题目原文时 0 命中（如课文标题被改写）；无降级策略，0 命中时教案完全没有题库参考。
3. **结果没留存题目 id**：只存了 count，教案与题库无法互相追溯。

## 需求

### 后端（backend/）

1. **模型与迁移**
   - `LessonPlan` 增加 `grade = Column(String(20))`（本课年级，如"三年级"，可空）。
   - `LessonPlan` 增加 `referenced_question_ids = Column(Text)`（JSON 数组字符串，可空）。
   - `backend/migrate_db.py` 加对应迁移（仿照现有 `lesson_plans.subject` 迁移的写法；只增列， SQLite 用 `ALTER TABLE ADD COLUMN` 即可，注意列已存在时跳过）。

2. **接口**
   - `POST /lessonplan/generate` 增加可选表单参数 `grade`（字符串，如"三年级"）。保存到 plan。
   - `_plan_to_dict` 增加 `grade` 与 `referenced_question_ids`（解析成 list，空为 []）。

3. **检索 v2（核心）**：改造 `backend/jobs.py::retrieve_question_context`，保持函数签名向后兼容（可新增可选参数），新逻辑：
   - **关键词提取**：把标题去《》书名号、去空白后作为候选；若长度 ≥4 且不含空格，再尝试从中提取 2-4 字的有意义片段（简单规则即可：优先完整标题，其次去掉常见课文后缀词如"教学""设计""教案""第一课时""第二课时"后的剩余部分）。每个候选词分别做 LIKE 查询后合并去重。
   - **年级→数字映射**：新增工具函数 `parse_grade_number(grade_str) -> int|None`："三年级"→3，"初一/七年级"→7，"高一/十年级"→10，"高三"→12；纯数字串直接返回；无法解析返回 None。放 `backend/bank_subjects.py`。
   - **过滤降级链**，每级 limit 8，合并去重后满 4 题即停止：
     a. subject + grade=数字（仅当解析出数字；题目 grade 为 NULL 时不命中此级）
     b. subject + education_level（年级数字映射到学段：1-6 小学 / 7-9 初中 / 10-12 高中）
     c. subject only
     d. education_level only
     e. 仍不足 4 题：接受当前已有结果（可为 0），不报错
   - **返回结构**：`{"context": str, "count": int, "question_ids": list[int]}`；`format_for_rag` 复用现有实现，但在每题前加 `[题库ID:xxx]` 标注便于追溯。
   - 失败/异常时保持现有行为：打日志、返回空 context、不影响生成。

4. **job 接线**：`_run_lesson_plan_job` 把 plan.grade 传入检索；生成成功后把 `rag["question_ids"]` JSON 存入 `plan.referenced_question_ids`。
   - `ai_client.generate_lesson_plan` 的 prompt 已有 `question_bank_context`，请确认 prompt 中明确要求模型把参考题目用于"课堂练习/例题"环节并在教案中标注 `[题库ID:xxx]`；如现有 prompt 语句不足则在 `ai_client.py` 中补强（只动与 question_bank_context 相关的段落）。

### 前端（frontend/src）

5. 教案生成表单增加**年级下拉**（可选）：按当前选择/档案学段联动——小学：一年级~六年级；初中：七年级~九年级；高中：高一~高三；无学段则显示 1-12 年级通用列表。值传中文（"三年级"）。已保存教案详情与生成结果页显示"参考题库 N 题"（用 `retrieved_questions_count` / `referenced_question_ids.length`）。
   - 先找到教案生成表单组件（grep `lessonplan/generate`），在其相邻位置改；风格与现有表单一致。

### 测试（backend/tests/，pytest，沿用现有 fixture 风格）

6. 新增 `backend/tests/test_lessonplan_rag.py`：
   - `parse_grade_number`：三年级→3、初一→7、高一→10、"12"→12、垃圾输入→None。
   - 降级链：造题（用现有 question bank fixture 风格或直接插库）验证 grade 级命中时不降级；grade 级 0 命中时落到 subject+education_level；全文无命中返回 count=0 且不抛异常。
   - 关键词提取：「《秋天的雨》第一课时」能命中含"秋天的雨"的题目。
   - 接口：`POST /lessonplan/generate` 传 grade="三年级" 后 plan.grade 与响应里带 grade；`_plan_to_dict` 含 referenced_question_ids 字段。

## 硬性约束

- 不改变现有 API 的行为兼容性：grade 为可选参数，不传时行为与现在一致（检索仍走 subject+education_level 降级链）。
- 检索必须保持 LIMIT 保护，不允许无 LIMIT 全表扫描。
- 不要 git commit / push；不要执行任何服务器命令；pytest 由我跑。
- 除上述文件外不要改动无关文件；发现需要额外改动时在最终回复里说明。
- 代码注释用中文，风格与现有代码一致。

## 最终回复格式

- 改动文件清单（路径 + 一句话说明）
- 每个需求的实现要点（对应上面编号）
- 新测试清单及如何单独运行
- 你认为我验收时最该关注的 3 个点
