# Cursor 任务书 task-12：线上端到端测试脚本（生产环境 API 级走查）

> 背景：E:\AI-Educator「AI 教学助手」，生产环境 https://ai-samrt-tutor-educator.cn 刚部署完 task-08/09/11 的全部改动（新学科学科支持、题库索引、QA 6 项修复）。需要一个可重复执行的线上走查脚本，验证真实环境无恙。
> **你的任务：只写脚本，不要执行**（本机 shell 不可用；由总工执行）。不要 git commit。
> 运行环境：`py`（系统 Python 3.13，已有 httpx）。脚本放 `scripts/e2e_prod.py`，仅依赖 httpx + 标准库。

## 需求

`scripts/e2e_prod.py [--base https://ai-samrt-tutor-educator.cn] [--cleanup]`：

1. **登录**：POST 登录接口（用户名 admin，密码从环境变量 E2E_PASSWORD 读取，不给时跳过需登录的步骤并在报告标注）。拿到 token 后全程带认证。
2. **用量统计**：GET 用量摘要与调用记录，参数 since=2026-10-01、until=2026-10-27；断言：返回 200、summary 有数据、calls 每条都在时间区间内（重点验证 task-11 修复 2 的时间过滤参数被接受且生效）。
3. **题库学科接口**：GET /api/questionbank/subjects（task-08 新增）；断言 200 且包含 语文/数学/英语/科学。
4. **题库列表四学科**：分别按 subject=语文/数学/英语/科学 请求列表（limit=5）；断言：各学科都返回非空、字段含 id/question_text/answer/difficulty；**记录首包大小**（response body bytes，验证 task-10 问题 6 的负载情况，不要求阈值，只记录）。
5. **题库搜索翻页**（task-11 修复 4）：选一个学科搜一个常见字/词（如语文搜"的"），先取第一页（limit=20），再用 offset=20 取第二页；断言：第二页非空且与第一页 id 无交集。若后端返回"结果过多"类提示或 offset 被截断，记为 WARN 不算 FAIL。
6. **keyset 分页**（task-09）：列表 limit=3 取第一条 id 作 after_id 再请求；断言返回不含该 id（验证生产环境游标分页正确，这是之前微秒精度 bug 的场景）。
7. **教案生成**（真实调用 1 次，验证 task-11 修复 1）：POST 生成教案，参数：课题"秋天的雨"、subject=语文、wait=true；断言 200、返回内容里 subject 字段为"语文"、正文不含明显数学跑题信号（简单判断：正文含"语文/朗读/课文/段落"等任一语文词，且不含"函数/导数/方程"）。记录耗时与 token 消耗（若接口返回）。
8. **批改链路**（可选，缺图则 SKIP）：本地存在 `qa-reports/model-eval-2026-10-15/homework_test.png` 时，上传并走一次批改（wait=true）；断言 200 与返回结构完整（有分数或待复核标志）。不存在则 SKIP。
9. **反馈提交**（task-11 相关）：POST 反馈接口提交一条"【自动化走查】…"（选一个预置问题项+一句文字）；断言 200；管理端 GET 反馈列表能查到这条。
10. **权限**：无 token 访问 /api/usage 系接口应 401/403，断言状态码。
11. **静态页**：GET / 返回 200 且 HTML 含 root 挂载点；GET 主 JS bundle 200（从 HTML 解析 script src）。

## 输出要求
- 终端人类可读：每步 PASS/FAIL/SKIP/WARN + 关键数据（耗时、行数、字节数）。
- `--cleanup` 时删除本脚本创建的教案/反馈记录（如果接口支持删除；不支持就打印遗留 id 清单）。
- 进程退出码：全部 PASS=0，有 FAIL=1。
- 异常处理：单步失败不中断，继续后续步骤，最后汇总。

## 最终回复格式
脚本路径、各步骤的实现要点（接口路径与断言）、如何运行、你预判在线上可能 FAIL/WARN 的点。
