# task-20 新增 GAOKAO-Bench 高考真题数据源（重点补高中解答题）

## 背景

题库 27 万条里 94% 是小学题；高中数学仅 2 239 条，且**没有解答题**（只有选择 1 535 + 填空 704）。现有爬虫的 open 源（cn-math-taxonomy、XiaoMi/cmath）都是小学数据源且已抓完（每晚 dup 7867、new 0）。

需要给 `crawler/daily_crawl.py` 的 OPEN_REPOS 新增 OpenLMLab/GAOKAO-Bench 仓库，把 2010–2022 高考数学真题（含解析）入库。

## 数据源结构（已核实）

仓库 `OpenLMLab/GAOKAO-Bench`，分支 main，6 个数据文件：

```
Data/Objective_Questions/2010-2022_Math_I_MCQs.json          → 选择题
Data/Objective_Questions/2010-2022_Math_II_MCQs.json         → 选择题
Data/Subjective_Questions/2010-2022_Math_I_Fill-in-the-Blank.json   → 填空题
Data/Subjective_Questions/2010-2022_Math_II_Fill-in-the-Blank.json  → 填空题
Data/Subjective_Questions/2010-2022_Math_I_Open-ended_Questions.json   → 解答题 ★
Data/Subjective_Questions/2010-2022_Math_II_Open-ended_Questions.json  → 解答题 ★
```

每个文件格式：

```json
{"keywords": "...", "example": [
  {"year": "2010", "category": "（新课标）", "question": "17. (12 分) 设数列满足 $a_{1}=2...$",
   "answer": "解：...", "analysis": "（I）由题意得...", "index": 0, "score": 12}
]}
```

- `question`：LaTeX 用 `$...$` 定界，开头有题号与分值（如 `17. (12 分) `、`13. (5 分) `），入库前用正则剥掉 `^\s*\d+\s*[.、]?\s*[（(]?\s*\d+(\.\d+)?\s*分\s*[)）]?\s*` 前缀；
- `answer`：解答题是完整解题过程（填到 solution 也合适）；填空/选择是答案；
- `analysis`：解析/评分标准；
- `score`：分值（float/int）。

## 任务

1. **入库映射**（新增解析函数，放 `import_open_math.py` 或 `crawler/daily_crawl.py` 内，跟随现有 `cmath_records`/`taxonomy_records` 的模式）：
   - question_text = 剥前缀后的 question；answer = answer；solution = analysis；
   - question_type：按文件映射 选择题/填空题/解答题；
   - subject=数学，education_level=高中，exam_type=高考，year=int(year)，region=category（去掉括号），score=score；
   - knowledge_points=[]；source_url 用 `https://github.com/OpenLMLab/GAOKAO-Bench/blob/main/<文件路径>#q<index>` 形式保证唯一；
   - difficulty 默认 3；grade=None。
2. **注册仓库**：OPEN_REPOS 新增一项 key=`gaokao-bench`，repo=`OpenLMLab/GAOKAO-Bench`，6 个文件按现有 `files` 结构配置（match_names + remote_paths）。确认 `_github_skip` 逻辑不会跳过 `Data/` 目录（现有 skip 名单是 `.git/.github/node_modules/assets/docs/screenshots` 等，不冲突）。
3. **走现有管道**：records 必须经 `filter_new_rows`（去重 + 脏数据拦截）再 `insert_batch`，不要绕开。
4. **测试** `backend/tests/test_daily_crawl_gaokao_bench.py`：
   - 用真实文件头两行级别的样例（截短的真实 question/answer/analysis）验证映射：题型、学段、exam_type=高考、year、前缀剥除（`17. (12 分) ` → 题干开头是"设数列"）；
   - 前缀剥除对无前缀题干幂等；
   - 整个 records 函数可被 crawl_open 的现有机制消费（模拟跑一遍 filter_new_rows，脏样例被拦截）。
5. `py -m pytest tests/test_daily_crawl_gaokao_bench.py tests/test_daily_crawl_dirty.py tests/test_review_daily.py -q` 全过。

## 约束

- 预计新增 1 000+ 行（解答题约 130-160 道是重点），不得超出 MAX_QUESTIONS_PER_NIGHT=2000；
- 不改 insert_batch / filter_new_rows / review_daily 的逻辑；
- 完成后输出：新增题数预估、改动摘要、测试结果。
