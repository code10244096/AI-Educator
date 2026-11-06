# task-18 题库入库脏数据过滤（公告/网页残留拦截）

## 背景

线上 question_bank 表（27 万+ 行）混入了公告类和网页抓取残留的脏数据，已在库里手工删除 9 条（id 271633–271641，备份于服务器 /opt/ai-teaching/data/backups/dirty_questions_20261105_133312.json）。需要**在入库源头拦截**，防止每日爬虫（crawler/daily_crawl.py）再次写入同类垃圾。

脏数据特征（全部为空 answer + 空 solution，被标记成"选择题/数学/高中"）：

1. `.htm` 文件名残留开头：`7006319. htm下文是2024年北京高考各科试卷及答案解析：…`
2. 考后公告/建议文案：`1. 平稳心态，积极面对：…`、`3. 合理利用考后时间：…`、`5. 家庭沟通，共商未来：…`（编号 + 冒号 + 建议语气，无 A/B/C/D 选项）
3. 导航/来源残留：`下一页`、`上一页`、`点击进入`、`本文整理`、`本文来源`、`新东方在线`、`无忧考网`、`gkxx`、`www.`、`http`

## 任务

修改 `backend/crawler/daily_crawl.py`（不要动其他文件）：

1. 新增 `looks_like_dirty_row(row: dict) -> bool`：命中上述任一类即视为脏数据。注意**不要误伤正常题**：
   - 合法题即使含"http"（题干里引用网页）也不该被误删，所以规则要组合判断：命中"公告建议/导航残留"关键词，**且**题干不含选项标记（`A.`/`A、`/`\nA `）或数学公式特征（`$$`、`\(`,`\[`）时才算脏；
   - `.htm` 开头残留规则：题干前 20 字符内出现 `\d+\.\s*htm` 即判脏（这是抓取列表页的标题拼接残留，正常题不可能以它开头）。
2. 在 `filter_new_rows`（约 440 行）里接入：被拦截的行计入返回统计（扩展返回或在函数内 log warning，含行数与样例前 60 字）。
3. `normalize_question_text` 保持不动。
4. 新增测试 `backend/tests/test_daily_crawl_dirty.py`：
   - 上述 3 类脏样例（用线上真实文本）均被拦截；
   - 正常题（含"http://example.com 参考网站"或"考后"字样的合法应用题、带 A./B./C./D. 选项的题）不被误拦；
   - `filter_new_rows` 把脏行过滤掉且统计正确。
5. 运行 `py -m pytest tests/test_daily_crawl_dirty.py -q` 和 `py -m pytest tests/test_questionbank_jev.py tests/test_questionbank_notebook.py -q` 确认全过。

## 约束

- 只改 crawler/daily_crawl.py + 新增测试文件；
- 完成后输出：改动摘要、测试通过截图（文本即可）、拦截规则清单。
