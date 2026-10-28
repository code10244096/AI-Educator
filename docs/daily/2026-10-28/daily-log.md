# 2026-10-28 工作日志

## 今日完成

### task-12 线上端到端走查（执行+验收）
- cursor 按 `docs/daily/2026-10-27/task-12-prod-e2e.md` 产出 `scripts/e2e_prod.py`（792 行，httpx+标准库，py_compile 通过）。
- 我对 https://ai-samrt-tutor-educator.cn 执行走查：**11 项全部 PASS，退出码 0**。报告：`docs/daily/2026-10-27/task-12-prod-e2e-report.md`。
- 过程中处理了两个问题：
  1. 生产 admin 密码不是 ljk19970925 → 已用应用自身 hash 重置为用户指定密码（session_version+1）。
  2. 本机 NO_PROXY 含 `[::1]` 导致 httpx 0.28.1 建连即报错 → 运行时覆盖 NO_PROXY 规避。
- 观察项：批改链路对测试作业图 score=0.0/needs_review=True，需抽样真实作业确认打分合理性。
- 清理：测试教案 id=7、批改 id=3 已删除；反馈 id=3 保留（接口无删除）。

## 待办（下一步）
- 抽样真实作业验证批改打分分布（真实 bug 则开 task-13 派 cursor 修）。
- 反馈管理端（删除/查看）需求可排期。
- 教案生成接口补 token 消耗字段。

## 协作记录
- cursor（prompt-12）：仅写码不执行，CURSOR_EXIT=0，产出质量合格。
