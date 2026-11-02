# 2026-11-02 早间值班报告

> 无人值守早班巡检 + 续跑任务。执行时间 2026-11-02 08:43–08:58（UTC+8）。

## 一、巡检结果

### 站点可用性
| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 首页 `GET /` | ✅ 200（1.1s） | 正常 |
| `GET /api/` | ⚠️ 404 | 无根路由属预期（`/api` 下无 index 端点） |
| `GET /docs` | ✅ 200 | FastAPI 在线，后端存活 |
| 前端容器 | ✅ Up 3 days (healthy) | 80/443 正常 |
| 后端容器 | ✅ Up 3 days (healthy) | 无异常日志（近 24h 无 error/traceback） |
| 磁盘 | ✅ 63%（50G 用 30G） | 余量充足 |

### 定时任务（crontab）
- ✅ 每日备份 02:30：11-02 已执行，数据库 183M + 上传文件 24K，正常。
- ✅ 月归档 03:10（每月 1 日）：`2026-10.tar.gz`（34MB）已在服务器本地生成。
- ❌ **COS 异地同步 03:40：失败**。11-01 起报错 `UnavailableForLegalReasons: account is arrears`——**腾讯云 COS 账号欠费**，上传被冻结。当前备份仅存于服务器本地单副本。

### 线上端到端走查（scripts/e2e_prod.py）
**9 PASS / 2 FAIL**：
- ✅ 登录、用量统计、题库学科/列表/搜索/翻页/keyset 分页、反馈提交、权限 401、静态页。
- ❌ **教案生成、批改链路：502（AI 模型 401 - Invalid token）**。后端日志显示 11-02 起主备模型（gemini-3.1-pro-preview → deepseek-v4.1-flash；gpt-5.5 → qwen3-vl-plus）全部 401。**生产环境的 AI 功能当前全部不可用**，根因是 `LLM_API_KEY`（第三方中转 key，sk-TBL…）失效或欠费，非代码问题。

## 二、今日完成事项

1. **线上巡检 + e2e 走查**（见上）。
2. **本地 pytest 全量回归**：346 passed + 2 failed。2 个失败均为同一根因——`test_auth.py::test_every_api_route_requires_login` 与 `acceptance/test_r1_auth.py::test_all_api_routes_require_auth` 直接遍历 `app.routes`，而新版 Starlette（≥1.x，本地 1.8.0 / 生产 1.10.0）的 `include_router` 改为懒加载 `_IncludedRouter` 占位对象，遍历结果为空导致断言失败。**HTTP 层行为不受影响**（e2e 实测接口鉴权全部正常），属测试代码兼容性缺陷。
   - 修复：`tests/testenv.py` 新增 `iter_concrete_routes` / `api_routes` 递归展平 helper；上述两个用例改用 helper。修复后 2 用例单独重跑通过。提交 `ff4d61e`（随本报告一并推送）。
3. **批改打分分布调查（只读聚合查询生产库）**：`homework_submissions` 仅 2 条——id=2 真实批改 score=66.7（合理非零）；id=3 为今日凌晨 e2e 走查遗留的失败记录（因上述 401）。**真实样本不足以下结论**，打分分布验证继续挂起，待真实作业积累后复查。
4. **未执行清理**：生产库中 e2e 遗留的失败测试记录（id=3）未删除（约束：不删生产数据），已如实记录。

## 三、未完成任务及原因

| 事项 | 原因 |
| --- | --- |
| 抽样真实作业验证批改打分分布 | 生产库仅 1 条真实批改记录，样本不足；待真实使用积累 |
| 前端年级下拉真实浏览器验证 | 无浏览器环境，e2e 已覆盖 API 层；需人工点验 |
| COS 异地备份同步 | 账号欠费，需用户充值（见下） |
| 生产 AI 功能恢复 | 模型 key 失效，需用户续费/更换（见下） |

## 四、待用户决策清单

1. **【高优先】模型 API key 失效（401）**：生产所有 AI 功能（教案生成、批改、OCR）11-02 起不可用。需续费或更换中转平台 `LLM_API_KEY`（涉及花钱，未代执行）。
2. **【高优先】COS 账号欠费**：每日备份的异地同步已中断 1 天，目前备份仅服务器本地单副本，有容灾风险。需给腾讯云 COS 账户充值。
3. CDN / 境内服务器（task-14 遗留的根本解法，依赖域名 ICP 备案状态确认）。
4. 反馈管理端（删除/查看）需求排期。
5. 教案生成接口补 token 消耗字段排期。

## 五、代码变更

- `backend/tests/testenv.py`：新增路由展平 helper（兼容 Starlette ≥1.x 懒加载路由）。
- `backend/tests/test_auth.py`、`backend/tests/acceptance/test_r1_auth.py`：改用 helper 遍历接口。
- 仅测试代码变更，无产品代码改动，无需部署。
