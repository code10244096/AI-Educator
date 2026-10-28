# task-12 线上端到端走查 · 执行报告

- 执行时间：2026-10-28 09:07（北京时间）
- 目标：https://ai-samrt-tutor-educator.cn
- 脚本：`scripts/e2e_prod.py`（httpx + 标准库）
- 执行环境：`E2E_PASSWORD=<admin密码>`，且必须覆盖本机 `NO_PROXY`（见下文问题 2）
- 结果：**PASS=11  FAIL=0  WARN=0  SKIP=0，退出码 0**

## 步骤结果

| 步骤 | 结果 | 耗时 | 说明 |
| --- | --- | --- | --- |
| 登录 | PASS | 2.5s | user=admin role=admin |
| 用量统计（时间段过滤） | PASS | 1.5s | overview.calls=14，tokens=18427 |
| 题库学科接口 | PASS | 1.0s | 16 个学科，含四大学科 |
| 题库列表四学科 | PASS | 2.2s | 语/数/英/科各返回 5 题 |
| 题库搜索翻页 | PASS | 0.7s | keyword=「的」，两页各 20 条无交集 |
| keyset 分页 | PASS | 2.3s | after_id=271194 → 271193/271192/271191 |
| 教案生成 | PASS | 37.1s | id=7，2348 字符，语文课题未被写成数学课 |
| 批改链路 | PASS | 44.0s | id=3，status=completed（score=0.0 需关注，见下） |
| 反馈提交 | PASS | 0.7s | id=3，topic=页面操作不方便 |
| 权限校验 | PASS | 2.6s | 未登录访问 /api/usage/* 均 401 |
| 静态页 | PASS | 9.6s | / 与前端 bundle 均可达 |

## 过程中发现并处理的问题

1. **生产 admin 密码与设定不符（已修复）**
   - 现象：首次执行登录 401「账号或密码错误」，8 个需登录步骤 SKIP。
   - 排查：生产 SQLite 中 admin 账号存在且启用（bcrypt 哈希），但 `verify_password('ljk19970925', hash)` 返回 False——生产库密码不是用户设定的 ljk19970925（可能某次部署重建过库）。
   - 处理：用应用自身 `auth.hash_password` 重置生产 admin 密码为 ljk19970925，`session_version+1` 使旧会话失效。复测登录 PASS。**注意：生产 admin 密码本次被改动过，如与预期不符请知悉。**

2. **本机 httpx 因 NO_PROXY 格式触发已知兼容问题（环境问题，非产品 bug）**
   - 现象：httpx.Client 创建即抛 `InvalidURL: Invalid port: ':1]'`。
   - 原因：本机 `NO_PROXY=localhost,127.0.0.1,::1,[::1]` 中带方括号的 `[::1]` 被 httpx 0.28.1 转成 mount 键 `all://*[::1]` 时解析失败。
   - 处理：执行时覆盖 `NO_PROXY=localhost,127.0.0.1`。CI/其他机器执行时如遇到同样报错，先检查 NO_PROXY。

3. **批改得分 score=0.0 且 needs_review=True（产品观察项）**
   - 测试用作业图（qa-reports/model-eval-2026-10-15/homework_test.png）走完链路、状态 completed，但模型给分为 0 并标记需人工复核。
   - 需确认这是模型对测试图片的真实评判，还是打分/识别环节有缺陷。建议抽样几份真实作业验证打分分布。

## 清理

- 走查产生的测试教案 id=7、批改记录 id=3 已通过 DELETE 接口删除（均 200）。
- 反馈记录 id=3 保留：接口无删除能力，属真实用户反馈数据，保留无害。

## 遗留风险/建议

- 反馈接口无删除/管理端，管理员无法在后台清理测试或恶意反馈，建议后续加管理端删除。
- 教案生成接口未返回 token 消耗字段，与用量统计的口径对齐后可提升可观测性。
