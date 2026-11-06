# task-19 每日题库数据审核脚本（review_daily.py）

## 背景

`crawler/daily_crawl.py` 每天 00:00–08:00 爬题入库（cron: `0 0 * * * docker exec ai-teaching-backend python /app/crawler/daily_crawl.py --source all`）。入库已有源头脏数据拦截（`looks_like_dirty_row`），但还需要**每日审核任务**评审新增数据的有效性：拦截漏网的脏数据、检查题目质量、出审核报告。

昨晚（2026-11-06）实例：gaokao 源 new=9、open 源 new=0/dup=7867。

## 任务

新建 `backend/crawler/review_daily.py`，由 cron 每天 **08:40（北京时间，容器为 UTC 则 00:40）** 运行一次：

```
docker exec ai-teaching-backend python /app/crawler/review_daily.py >> /opt/ai-teaching/logs/crawler/review.log 2>&1
```

功能要求：

1. **确定评审范围**：读取 `/app/logs/crawler/<昨天日期>-summary.json` 拿到 `total_new`；从 question_bank 查 `created_at` 最近 24 小时内入库的行（以 created_at 为准，不依赖 summary）。若 summary status != success 或 total_new=0，仍执行审核（兜底），但报告标注。
2. **规则审核（不调模型，零成本）**，对范围内每行检查：
   - `looks_like_dirty_row` 漏网（复用 daily_crawl 的函数）→ 命中即 **隔离**（从 question_bank 删除并备份到 `/app/data/backups/review_quarantined_<date>.json`，同我手工清洗的格式）；
   - 空 answer + 空 solution → 标记 low_quality（不删，记录 id 与题干前 60 字）；
   - 题干 <15 字或 >2000 字 → 标记 low_quality；
   - question_type 不在 (选择题, 填空题, 解答题, 判断题) → 标记 anomaly。
3. **Jev 语义抽检（有成本，控制量）**：从通过规则审核的行中随机抽最多 10 行，用 `jev_client.get_jev_client()` 逐行判断"这条文本是不是一道完整、可作答的题"（相关度概率≥0.5 视为通过）。真实调用必须走 `trial_quota.before_call/add_tokens`（jev_client 已内置），feature 日志会记为 questionbank_search 也无妨（在 task_meta 里加 `review: true` 区分）。若 Jev 不可用/超时，跳过抽检并在报告标注，**不阻断审核**。
4. **输出报告** `/app/logs/crawler/review-<昨天日期>.json`：
   ```json
   {"date": "...", "scope_total": N, "quarantined": [{"id":..,"reason":"dirty","sample":".."}], "low_quality": [...], "anomaly": [...],
    "jev_sample": {"sampled": 10, "passed": 9, "failed_ids": [...], "skipped": false},
    "token_usage": {"calls": n, "input_tokens": n, "output_tokens": n}, "status": "ok|warn|error"}
   ```
   status 规则：有隔离或 Jev 抽检失败>0 → warn；脚本异常 → error。
5. 控制台 log 输出一行摘要：`[review] 2026-11-06 scope=9 quarantined=1 low_quality=0 jev=9/10 status=warn`。
6. 幂等：同一天重复运行不产生重复报告内容（重跑覆盖同名报告文件即可）；已隔离的行不会重复计数（查不到即跳过）。

## 测试

新建 `backend/tests/test_review_daily.py`（用 tmp_path + 内存 SQLite 或 monkeypatch，参考 test_daily_crawl_dirty.py 风格）：
- 脏行被隔离并写入备份文件；
- 空答案行进入 low_quality 不删除；
- Jev 客户端失败时报告 skipped=true 且 status 不为 error；
- 报告 JSON 结构完整。

`py -m pytest tests/test_review_daily.py tests/test_daily_crawl_dirty.py -q` 全过。

## 约束

- 只新增 `backend/crawler/review_daily.py` + `backend/tests/test_review_daily.py`；复用 daily_crawl / jev_client / database 的现有函数，不改动它们；
- Jev 抽检每次调用最多 10 题，绝不全量调模型；
- 完成后输出：改动摘要 + 测试通过结果 + 运行方式说明。
