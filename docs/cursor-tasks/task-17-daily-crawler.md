# Cursor 任务书 task-17：题库每日爬虫（0:00-8:00 窗口）

> 目标：每天 0:00-8:00（北京时间）增量爬取公开题目源扩充 question_bank，零 LLM 调用（不花 token）。
> 代码你来写，调度与监控由验收方配置。不要 git commit。

## 现状（先读这些文件复用，不要重造轮子）

- `backend/crawl_province_gaokao.py`：gk100.com 省份高考卷爬虫（httpx + BeautifulSoup，async）。
- `backend/import_open_math.py` / `import_open_round*.py`：开放数据集（GitHub：cn-math-taxonomy、XiaoMi/cmath 等）导入，**按 source_url 去重**的模式照抄。
- `backend/models.py` 的 QuestionBank 表结构、`backend/database.py` 的 AsyncSessionLocal。

## 交付物：`backend/crawler/daily_crawl.py`（新建目录与文件）

一个可直接 `python /app/crawler/daily_crawl.py` 运行的异步脚本，行为：

### 1. 时间窗口自控制
- 启动时读取当前北京时间；若不在 00:00-08:00 窗口内且没有 `--force` 参数则直接退出（打印原因）。
- 每处理完一个题目源/批次检查时间，**到达 07:50 停止抓取新页面**，把已抓取的内容入库后退出（08:00 前必须结束）。
- 支持 `--source gaokao|open|all`（默认 all）、`--force`、`--dry-run`（只抓不写库，打印统计）。

### 2. 题目源（先实现两个，架构留扩展）
- `gaokao`：复用 ProvinceGaokaoCrawler 抓 gk100.com 的省份卷（北京/上海/天津，年份 2020-2026），学科先数学。若该站结构变化导致解析失败，记日志跳过，不要整任务崩掉。
- `open`：检查 cn-math-taxonomy / cmath 的 GitHub 仓库是否有更新（比较远端最新 commit 或文件 hash 与本地记录），有更新才下载并走 import_open_math 的去重导入逻辑。

### 3. 抓取礼仪（必须）
- 请求间隔 ≥3 秒，单源失败重试 ≤2 次（指数退避），带真实 UA；
- 遵守 robots.txt：抓取前获取并检查， disallow 的路径跳过；
- 单源单晚最多 500 个页面（防失控），总量上限 2000 题/晚。

### 4. 入库与去重
- 与现有导入脚本同一套 QuestionBank 字段（subject/education_level/knowledge_points/source_url 等）；
- **两级去重**：source_url 唯一 + question_text 规范化（去空白/标点）后的 hash 唯一，重复跳过；
- 每批 100 条事务提交，单题失败不影响整批。

### 5. 监控输出（验收方每天要看）
- 日志：`logs/crawler/YYYY-MM-DD.log`（含每个源的新增/跳过/失败数）；
- 汇总：`logs/crawler/YYYY-MM-DD-summary.json`，结构：
  ```json
  {"date": "2026-11-04", "started_at": "...", "ended_at": "...",
   "sources": {"gaokao": {"new": 0, "dup": 0, "error": 0, "pages": 0}, "open": {...}},
   "total_new": 0, "status": "success|partial|failed", "notes": "..."}
  ```
- 退出码：全部成功 0，部分失败 2，完全失败 1。

## 验收
1. `python backend/crawler/daily_crawl.py --dry-run --force` 在本地能跑通（有网络时），不触碰数据库。
2. 不引入项目没有的新依赖（httpx/bs4/sqlalchemy 已有）。
3. 只新增 `backend/crawler/` 目录文件；如确需小改 import_open_math 复用函数，列出改动点。
4. 汇报：文件清单、dry-run 输出样例、建议的 cron 写法。
