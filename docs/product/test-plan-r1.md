# 第 1 轮验收测试计划（test-plan-r1）

> 维护：测试 agent。依据：`docs/product/PRD.md` v1.0（第 2 章上线标准、第 4 章 R1-001~R1-012/R1-014、第 6 章第 1 轮范围）。
> 分支：`feat/ai-teaching-launch`。产品决策 Q1~Q13 按 PRD 第 5 章推荐默认执行。
> 缺陷记录：`docs/product/defects.md`。本计划随开发分组提交持续更新（§6 进度表）。

## 0. 范围

- 需求：R1-001 ~ R1-011（P0），R1-012（公式渲染，P1），R1-014（三态与 404，P1）。共 13 条。
- 本轮检验的上线标准（PRD §6）：L-F01（模拟模式）、L-F02~F05、L-U01~U03、L-U05~U08、L-S01~S08、L-P01、L-P03（单份）、L-P04、L-D01~D05、L-Q01、L-Q04、L-Q05。
- 不在本轮：R1-013、R1-015~R1-023（第 2 轮），L-U04、L-Q02 的 E2E 脚本部分、L-Q03 作为上线门槛（本轮先跑一次真实评测，结果记入第 7 章，正式判定在第 2 轮上线评审）、L-O*（R1-020 第 2 轮）、L-P02。

## 1. 验证方式与约定

### 1.1 四类验证方式

| 代号 | 方式 | 说明 |
|---|---|---|
| **A** | 自动化接口/静态用例 | `backend/tests/acceptance/test_r1_<分组>.py`，离线（临时库 + 假模型）。运行：仓库根目录 `python -m pytest backend/tests/acceptance`；随全量回归 `python -m pytest backend/tests` 一起跑，验收用例排在最后执行 |
| **B** | 浏览器手工验收 | 内置浏览器（`mcp__Claude_Browser__*`），新开标签页。桌面 1366×768 和手机 375×812 两种宽度，截图比例 0.5~0.7。服务：后端 8041、前端 3041，数据放在 scratch/qa |
| **C** | 命令检查 | `npx vite build`、`bash -n`、`git grep`、备份/恢复演练等，结果写入 §6 |
| **D** | 真实模型 | 整轮预算 ≤20 次调用。用于 L-Q03 评测（≥5 份）和 L-P03 单份耗时，脚本复用 `backend/tests/e2e_real_model.py` |

### 1.2 负责方

- **测试**：测试 agent 编写并执行用例，结论写入本文件和 defects.md。
- **开发**：开发 agent 提供可测性钩子和随功能写的单元测试（R1-021 要求第 1 轮就随功能一起写）。表中写“开发+测试”的条目，表示开发先提供钩子或实现，测试负责最终判定。
- 除特别说明外，最终“通过/不通过”都由测试判定。

### 1.3 与开发约定的测试钩子（2026-09-26 已确认）

- 开通账号用 `python backend/manage.py create-user --username U --name N [--role admin] [--school S] [--password P] [--no-force-change]`，输出固定有一行 `初始密码: <pwd>`。也可以在代码里调用 `from manage import create_user`，它返回 `(user_id, password)`。另有 `reset_password`、`disable_user`、`assign_orphans`、`list_users`。
- `must_change_password=true` 的账号访问 `/api/auth/*` 以外的业务接口时，一律返回 403 `请先修改初始密码`。
- 会话：Cookie 名 `aiedu_session`（httpOnly、SameSite=Lax，生产环境加 Secure）。有效期取 `settings.SESSION_EXPIRE_MINUTES`，签发时读取。可以用 `auth.create_access_token(user_id, expires_delta=...)` 造过期 token，也接受 `Authorization: Bearer`。改密、重置、停用都会让旧会话失效。
- `GRADING_CONCURRENCY`、`DAILY_GRADING_QUOTA`、`MOCK_LLM_DELAY_SECONDS` 都在用到时从 settings 读取（验收用例用 monkeypatch 调整）。
- `APP_ENV`、`JWT_SECRET`、`LLM_API_KEY`、`CORS_ORIGINS`（逗号分隔）、`SEED_DEMO_DATA`、`SESSION_EXPIRE_MINUTES` 都从环境变量读取。
- 公开接口只有 `/`、`/health`、`POST /api/auth/login`、`POST /api/auth/logout`（未登录也返回 200，只清 Cookie）。
- 待确认（第⑤组前）：前端“文件名 → 学生”自动对应逻辑请导出为纯函数（例如 `src/utils/matchFiles.js` 里的 `matchFilesToStudents(files, students)`），供 `js/ssr_call.mjs` 离线调用。

### 1.4 验收测试骨架

| 分组 | 文件 | 覆盖 |
|---|---|---|
| ① 账号与鉴权 | `test_r1_auth.py` | R1-001、R1-002、L-S01~S03、L-S07（越权下载） |
| ② 安全与部署 | `test_r1_security_deploy.py` | R1-003、R1-009、L-S04~S07、L-D01~D05（静态 + 模拟） |
| ③ 数据清理 | `test_r1_data_cleanup.py` | R1-005、R1-011、L-S08、L-F03（代码） |
| ④ 批改可信 | `test_r1_grading_trust.py` | R1-008、L-F04、L-F05 |
| ⑤ 批量上传 | `test_r1_batch_upload.py` | R1-007、L-P04 |
| ⑥ 信息架构 | `test_r1_ia.py` | R1-006、R1-004 |
| ⑦ 前端质量 | `test_r1_frontend_quality.py` | R1-010、R1-012、R1-014、L-P01、L-U08 |
| 公共 | `conftest.py`、`qa_helpers.py`、`_qa_runner.py`（子进程：生产启动、迁移、崩溃重启）、`js/ssr_call.mjs`（通过 Vite SSR 离线调用前端函数、渲染组件） | — |

每个分组开发前，对应模块整体标记 `xfail(reason="待开发…", run=False)`；分组提交后去掉标记并按实际接口修正。想看当前真实的失败情况时，加 `--runxfail`。

## 2. 需求验收标准 → 验证方式

表中“用例”列：A 类写 `文件::用例名`，B 类写浏览器用例编号（步骤见 §4），C 类写命令编号（见 §5）。

### R1-001 真实登录、退出、改密、命令开通账号（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | `manage.py create-user` 开通 → 用初始密码登录 → 先进“设置新密码”页 → 改完进工作台，顶栏显示“王老师” | A+B | `test_r1_auth.py::test_create_user_cli_initial_password_must_change`；B-001-1 | 测试 |
| 2 | 错误密码和不存在的账号都提示“账号或密码错误”，返回 401 | A+B | `::test_login_failure_message_identical`；B-001-2 | 测试 |
| 3 | 连续 10 次错误后，第 11 次即使密码正确也返回 429“尝试次数过多，请 15 分钟后再试” | A | `::test_login_lockout_after_10_failures`（15 分钟解锁在代码评审中确认） | 测试 |
| 4 | 未登录访问 `/class` → `/login?redirect=%2Fclass` → 登录后回到 `/class` | B | B-001-4 | 测试 |
| 5 | 退出后按后退，页面不显示业务数据，接口返回 401 | A+B | `::test_logout_then_business_api_401`、`::test_logout_anonymous_is_harmless`；B-001-5 | 测试 |
| 6 | 会话过期后点任意按钮 → 跳登录页，提示“登录已过期，请重新登录” | A+B | `::test_expired_session_returns_401`、`::test_frontend_handles_401`（静态）；B-001-6（用过期 Cookie） | 测试 |
| 7 | `password_hash` 以 `$2b$` 开头；全站不出现“123456”“演示账号”“演示密码” | A+B | `::test_password_hash_is_bcrypt`、`::test_frontend_has_no_demo_password`；B-001-7（页面文本检索） | 测试 |
| 8 | 改密：旧密码错误提示“当前密码不正确”；新密码不合规时提示具体规则；改成功后新密码能登录、旧密码不能 | A+B | `::test_change_password_rules`；B-001-8 | 测试 |
| 方案 | 登录响应字段；httpOnly/SameSite Cookie；`PUT /api/auth/me`；`reset-password`/`disable-user`/`list-users` | A | `::test_login_success_cookie_and_body`、`::test_update_profile_me`、`::test_manage_reset_disable_list` | 测试 |

### R1-002 接口鉴权与按教师隔离（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 遍历 `app.routes`，不带凭证请求每个 `/api/*` 业务接口，全部返回 401 | A | `test_r1_auth.py::test_all_api_routes_require_auth` | 测试 |
| 2 | 教师 B 对 A 的班级/学生/作业/提交/错题/教案执行 GET/PUT/DELETE/子资源请求，全部 404；B 的列表不含 A 的数据 | A | `::test_cross_teacher_reads_return_404`、`::test_cross_teacher_mutations_rejected`、`::test_cross_teacher_lists_are_empty` | 测试（开发同时维护自己的隔离单测） |
| 3 | B 直接请求 A 的原始作业文件 URL → 404 | A | `::test_cross_teacher_reads_return_404`（包含 `/grader/{id}/files/0`） | 测试 |
| 4 | 在 `teaching_assistant.db` 副本上迁移，并 `assign-orphans` 给 A：A 能看到全部旧数据，新教师 C 看不到 | A | `::test_assign_orphans_on_real_db_copy`（只读方式复制源库，迁移前后行数一致，两次执行幂等） | 测试 |
| 5 | 前端：任一接口 401 都跳登录页 | B | B-001-6 | 测试 |
| 方案 | 归属字段写当前教师；后台任务用任务所属教师；大模型调用带 `teacher_id` | A | `::test_ownership_columns_and_llm_teacher_id` | 测试 |

### R1-003 生产安全基线（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | `APP_ENV=production` 没有 `JWT_SECRET`（或仍是示例值）时启动失败，提示“生产环境必须设置 JWT_SECRET”；没有有效 `LLM_API_KEY` 同样失败 | A+C | `test_r1_security_deploy.py::test_production_refuses_without_jwt_secret`、`::test_production_refuses_without_llm_key`；C-003-1（用 uvicorn 在 8041 实际启动一次） | 测试 |
| 2 | 镜像 `/app` 内没有 `config.json`、`*.db`、`uploads/` 旧文件、`venv/`、`api_runs/` | A（模拟） | `::test_dockerignore_present_and_complete`、`::test_docker_build_context_excludes_secrets_and_data`（按 moby 规则模拟构建上下文）、`::test_simulated_image_boots_with_env_only`。**本机没有 Docker**，`docker run … ls /app` 留到上线评审时补测 | 测试 |
| 3 | 生产配置下 `/docs`、`/openapi.json` 返回 404；非白名单 Origin 不放行 CORS | A | `::test_production_docs_cors_debug_cookie` | 测试 |
| 4 | 教师访问 `/api/usage/summary` → 403；菜单中没有“用量统计”；管理员可以看 | A+B | `::test_usage_api_admin_only`、`::test_usage_menu_hidden_for_teacher_static`；B-003-4 | 测试 |
| 5 | `.exe` 改名 `.jpg` → 400“文件内容与格式不符”；单份 11 个文件 → 400 | A | `::test_upload_magic_bytes_mismatch_rejected`、`::test_upload_more_than_10_files_rejected` | 测试 |
| 6 | 现有 `tests/test_security.py` 全部通过 | A | 全量回归 | 测试 |
| 方案 | 已跟踪文件无明文密钥；`.env.example` 完整；生产 debug=false、不打印 SQL、Cookie 带 Secure | A | `::test_no_plaintext_secrets_tracked`、`::test_env_example_documents_required_vars`、`::test_production_docs_cors_debug_cookie` | 测试 |

### R1-004 下线假功能（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 侧栏和页面里不出现题库管理的 3 个子页面；`/questionbank/ai` 跳到工作台 | A+B | `test_r1_ia.py::test_questionbank_hidden_and_redirected`；B-004-1 | 测试 |
| 2 | 设置页只有“个人资料”“修改密码”；改姓名后刷新、重新登录，顶栏都是新名字 | A+B | `::test_settings_only_profile_and_password`、`test_r1_auth.py::test_update_profile_me`；B-004-2 | 测试 |
| 3 | `frontend/src` 里没有用 `setTimeout` 模拟保存/上传/生成的代码（逐条人工确认） | A+C | `::test_settimeout_not_faking_success`；C-004-3（列出全部 setTimeout 并逐条写结论） | 测试 |
| 4 | 逐页点击全部按钮，没有“无反应”或“提示成功但数据没变”的控件 | B | B-004-4（与 L-F02 一起做，对照网络请求和数据库） | 测试 |
| 方案 | 死代码删除；顶栏去掉搜索按钮和假铃铛 | A | `::test_dead_code_and_fake_pages_removed`、`::test_navbar_logo_and_no_fake_buttons` | 测试 |

### R1-005 不播种、去开发概念、作业用主键（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 删掉数据目录后以生产配置启动：`classes`、`class_members`、`homework_*` 都是 0 行 | A | `test_r1_data_cleanup.py::test_fresh_start_no_demo_seed`、`::test_seed_only_when_flag_set` | 测试 |
| 2 | 教师可见页面全文检索，不出现 dataset、测试数据、测试集、调试模式、`class\d+`、`作业 #` | A+B | `::test_frontend_has_no_dev_concepts`（代码）；B-005-2（每个页面 `get_page_text` 检索，桌面和手机都做） | 测试 |
| 3 | 新建作业后 URL 里的 ID 等于主键；旧的 dataset 作业也按主键访问，不撞号 | A+B | `::test_new_homework_url_id_is_primary_key`、`::test_legacy_homework_accessed_by_primary_key`（真实库副本）；B-005-3 | 测试 |
| 4 | 已批改学生重新上传后，名录和批改记录里的时间变成当前时间 | A | `::test_reupload_updates_submit_time` | 测试 |
| 方案 | 生产环境不注册 `/homework/dataset*`、`/grader/upload-dataset/*`；批改横幅不显示 slug 和 `#ID` | A+B | `::test_fresh_start_no_demo_seed`（路由表）；B-005-2 | 测试 |

### R1-006 常驻导航 + 工作台 + 菜单重组（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 1366×768 下登录后看到常驻侧栏和工作台；点菜单侧栏不收起；当前项高亮 | B | B-006-1 | 测试 |
| 2 | 工作台 4 张卡片的数字与作业详情一致（构造 1 份待复核、1 份批改中、1 份失败、1 次作业有未上传），点卡片进入对应作业并已按状态筛选 | A+B | `test_r1_ia.py::test_dashboard_cards_match_homework`；B-006-2 | 测试 |
| 3 | 新账号工作台显示三步引导，照着引导能完成建班、导入、布置作业 | A+B | `::test_dashboard_new_teacher_is_empty`；B-006-3 | 测试 |
| 4 | 提交批改后，顶栏任务抽屉出现进行中的任务和进度；换一个浏览器登录同一账号也能看到 | A+B | `::test_task_drawer_is_server_side`；B-006-4（第二个会话用独立标签页并清空 localStorage） | 测试 |
| 5 | 从任意页面到“某作业的批量上传”不超过 3 次点击 | B | B-006-5 | 测试 |
| 6 | 教师菜单里没有“我的任务”“题库管理”“用量统计”；管理员能看到“用量统计” | A+B | `::test_sidebar_menu_items`；B-006-6（教师、管理员各登录一次） | 测试 |
| 7 | `/class` 可以新建、编辑、删除班级；设置页不再有班级管理 | B+A | B-006-7；`::test_settings_only_profile_and_password` | 测试 |
| 方案 | 取消 localStorage 任务；Logo 回工作台；死代码删除 | A | `::test_no_local_task_storage`、`::test_navbar_logo_and_no_fake_buttons`、`::test_dead_code_and_fake_pages_removed` | 测试 |

### R1-007 作业内批量上传 + 服务端批改队列（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 5 个文件按规则对应：陈晓明 2 页按 1、2 排序，林雨桐 1 页，王浩然（学号命名）1 页，`IMG_0231.jpg` 未对应 | A+B | `test_r1_batch_upload.py::test_file_matching_rules_basic`（通过 node 调前端纯函数）；B-007-1（真实选择文件） | 开发导出纯函数 + 测试 |
| 2 | 同名的两个陈晓明：`陈晓明.jpg` 不自动对应；`2025004_陈晓明.jpg` 对应学号 2025004 | A+B | `::test_file_matching_same_name_uses_student_no`；B-007-1 | 开发+测试 |
| 3 | 给已批改的学生分配文件时显示“将覆盖已有结果”，提交后旧结果被替换，旧的同步错题被移除 | A+B | `::test_reupload_replaces_result_and_old_wrong_questions`；B-007-3（提示文案） | 测试 |
| 4 | 一次提交 10 份（延迟模拟），任何时刻 processing ≤ 并发数，其余显示“排队中（前面还有 N 份）” | A | `::test_global_concurrency_cap_and_queue_position`（10 份，两位教师共享全局上限）、`::test_mock_llm_delay_env` | 测试 |
| 5 | 进度条、名录、工作台三处数字一致；刷新页面、换设备登录后进度仍正确 | A+B | `::test_progress_endpoint_matches_roster`、`::test_progress_eta_while_running`、`test_r1_ia.py::test_dashboard_cards_match_homework`；B-007-5 | 测试 |
| 6 | 批量进行中重启后端，排队的任务重启后继续完成 | A+C | `::test_queued_jobs_resume_after_restart`（子进程批量提交后 `os._exit` 模拟崩溃）；C-007-6（8041 上实际杀进程再重启） | 测试 |
| 7 | 在名录行内上传单个学生，全程不离开作业详情页 | B | B-007-7 | 测试 |
| 8 | 作业没有参考答案时显示黄色提示和“去填写参考答案”入口 | B | B-007-8 | 测试 |
| 9 | `DAILY_GRADING_QUOTA=2` 时同一教师当天第 3 份被拒并提示额度用完；调整后恢复 | A+B | `::test_daily_grading_quota`；B-007-9（页面提示文案） | 测试 |

### R1-008 批改结果可信（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 空白图片或无题号文本 → 显示“失败：未识别到题目…”；成绩档案、平均分、逐题正确率、错题本都不变 | A+B | `test_r1_grading_trust.py::test_unrecognized_submission_is_failed_not_zero`（空白图、少于 10 字、0 题、questions 为空、JSON 解析失败，共 5 种）、`::test_llm_failure_message_is_teacher_friendly`；B-008-1 | 测试 |
| 2 | 4 题对 2 题得 50；第 3 题改判为“对”→ 75，错题本少 1 条，逐题正确率、成绩档案同步更新，刷新后不变 | A+B | `::test_score_computed_from_is_correct`、`::test_override_recomputes_score_notebook_analysis_archive`；B-008-2 | 测试 |
| 3 | 原判“对”的题改判为“错”→ 错题本新增一条，来源标“老师改判” | A+B | `::test_override_to_wrong_adds_teacher_notebook_entry`；B-008-3 | 测试 |
| 4 | 对已改判的提交点“重新批改”→ 出现覆盖确认；确认后改判记录清除 | A+B | `::test_regrade_clears_overrides`；B-008-4（确认框文案） | 测试 |
| 5 | 名录“待复核”筛选只显示 pending_review；点“标记为已复核”后从筛选中消失，工作台“待复核”减 1 | A+B | `::test_review_status_flow`、`test_r1_ia.py::test_dashboard_cards_match_homework`；B-008-5 | 测试 |
| 6 | 模型返回 `reference_issue` 时，结果页显示黄色提示“AI 认为第 N 题参考答案可能有误：…” | A+B | `::test_needs_review_and_reference_issue_passthrough`、`::test_grading_prompt_asks_for_review_fields`；B-008-6（用假模型构造结果） | 测试 |
| 7 | 迁移后，原来“0 题 0 分”的记录显示为失败，不再拉低平均分 | A | `::test_migration_zero_question_records_become_failed`（构造 0 题记录；同时检查旧演示数据里“有分数但没有逐题明细”的记录不被误伤，见 §7 风险 R-3） | 测试 |
| 方案 | 改判接口参数校验（题号不存在返回 404；失败的提交不能改判） | A | `::test_override_validation` | 测试 |

### R1-009 部署：上传限制、compose、数据卷、备份恢复（P0，运维）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 在干净的 2 核 2GB Linux 上按文档部署，两个容器都 healthy；只对外开放 80/443 | A（静态）+待补测 | `test_r1_security_deploy.py::test_compose_backend_hidden_volumes_healthcheck`。**本机没有 Docker/WSL**，实际部署留到上线评审时在 Linux 服务器补测 | 测试 |
| 2 | 上传 8MB 照片、一个学生 3 张 5MB 照片都成功（不出现 413） | A（静态）+C | `::test_nginx_upload_limit_timeouts_headers`、`::test_nginx_security_headers_not_shadowed`；C-009-2（直连后端上传 8MB 和 3×5MB，验证后端单文件 10MB 上限和总量没有额外限制） | 测试 |
| 3 | `down && up` 后班级、作业、原始照片都在 | A（静态）+待补测 | `::test_compose_backend_hidden_volumes_healthcheck`（卷声明）；Docker 实测待补 | 测试 |
| 4 | 执行 `backup.sh` 生成备份；删掉数据目录后执行 `restore.sh`，数据与备份时一致 | A+C | `::test_backup_restore_scripts_present`；C-009-4（Git Bash 演练，本机没有 sqlite3 CLI，用 Python 写的 sqlite3 替身实现 `.backup`） | 测试 |
| 5 | 批量 45 份期间后端内存峰值 < 1.5GB | C（近似） | C-009-5：模拟延迟下在 8041 批量 45 份，用 `Get-Process` 采样后端进程峰值内存（替代 `docker stats`） | 测试 |
| 方案 | 部署文档包含 .env、账号命令、crontab 02:30、恢复步骤、升级步骤 | A | `::test_deploy_doc_consistent` | 测试 |

### R1-010 首屏性能（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 没有 >500KB 的 chunk；登录页 + 工作台首屏 JS 合计 gzip ≤ 300KB | A+C | `test_r1_frontend_quality.py::test_no_chunk_over_500kb`、`::test_initial_js_gzip_budget`（按 manifest 计算入口和登录页、工作台路由 chunk 的静态依赖闭包）；C-010-1 `npx vite build --outDir <scratch>/build` | 测试 |
| 2 | 登录页的网络请求里没有 html2pdf、KaTeX；点“导出 PDF”时才出现 | A+B | `::test_login_path_excludes_html2pdf_and_katex`、`::test_heavy_deps_not_in_entry_path`、`::test_pages_are_lazy_loaded`；B-010-2（`read_network_requests`） | 测试 |
| 3 | Fast 4G 下登录页可交互 ≤ 3 秒 | C（估算）+B | C-010-3：按首屏 gzip 体积和 Fast 4G 参数（约 9Mbps、RTT 60ms）估算；B-010-3 在 `vite preview` 构建版上用 Performance API 取 `domInteractive`/`loadEventEnd` 作参考。内置浏览器不能限速，结论标为“估算” | 测试 |

### R1-011 学号区分同名学生（P0）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 导入“陈晓明,男,2025001”“陈晓明,男,2025004”→ 两人都导入，提示“成功导入 2 名” | A+B | `test_r1_data_cleanup.py::test_import_same_name_different_student_no`；B-011-1 | 测试 |
| 2 | 两行“张三”（都没学号）→ 第二行跳过，提示“重名跳过 1 名：张三” | A | `::test_import_duplicate_name_without_no_skipped`、`::test_add_member_uniqueness_rules` | 测试 |
| 3 | 两个陈晓明分别上传批改后，名录、成绩档案、逐题做错名单里分开统计，姓名后带学号 | A+B | `::test_same_name_students_graded_separately`；B-011-3 | 测试 |
| 4 | 改学生姓名后，历史批改记录和成绩仍归这个学生 | A | `::test_rename_member_keeps_history` | 测试 |
| 方案 | 上传接口接受 `member_id`，不接受别的班的学生；存量数据回填 `member_id` | A | `::test_upload_by_member_id_and_foreign_member_rejected`、`::test_legacy_homework_accessed_by_primary_key` | 测试 |

### R1-012 公式统一用 KaTeX 渲染（P1）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 用真实批改结果（第 4 题含 `\displaystyle =\frac{x_2-x_1}{x_1x_2}>0`）渲染：生成 `.katex`，文本中没有 `\displaystyle`、`\frac`、`\(`、字面量 `\n` | A+B | `test_r1_frontend_quality.py::test_mathtext_renders_real_result`（Vite SSR 渲染 MathText，排除 MathML 注释里的 TeX 源码后检查可见文本）；B-012-1（结果页 `get_page_text`） | 测试 |
| 2 | 错题本和逐题正确率里同一道题渲染一致 | A+B | `::test_mathtext_used_on_all_math_surfaces`；B-012-2 | 测试 |
| 3 | 非法 LaTeX（`$\frac{1$`）显示原文，控制台没有未捕获异常 | A+B | `::test_mathtext_invalid_latex_falls_back`；B-012-3（读 console） | 测试 |

### R1-014 加载/空/错误三态与 404（P1）

| AC | 验收标准（摘要） | 方式 | 用例 | 负责 |
|---|---|---|---|---|
| 1 | 停掉后端后打开工作台、班级、作业详情、错题本、教案：都显示错误态和“重试”，不显示空状态；恢复后点重试正常 | B | B-014-1（停 8041 后端 → 逐页截图 → 重启 → 点重试） | 测试 |
| 2 | 慢网下打开批改页，加载期间不出现“还没有批改记录” | B | B-014-2（临时 vite 配置里给 `/api` 代理加 3 秒延迟，模拟 Slow 3G 的慢接口） | 测试 |
| 3 | 访问 `/no-such-page` 显示 404 页 | A+B | `::test_not_found_route`；B-014-3 | 测试 |
| 方案 | Loading/Empty/ErrorState 公共组件；不再有 `.catch(() => {})` | A | `::test_state_components_and_no_swallowed_errors` | 测试 |

## 3. 上线标准（本轮检验项）→ 验证方式

| 编号 | 标准（摘要） | 方式 | 用例 / 证据 | 负责 |
|---|---|---|---|---|
| L-F01 | 模拟模式走完主流程：登录 → 建班 → 导入 → 布置作业 → 批量上传 ≥3 人 → 逐题结果 → 改判 → 逐题正确率与做错名单 → 错题变式 → 教案生成与导出 | B | B-F01（第⑥⑦组完成后执行，桌面宽度；每步截图、读 console） | 测试 |
| L-F02 | 可见按钮、菜单、表单都有真实效果 | B | B-004-4（逐页点击，对照网络请求和数据库） | 测试 |
| L-F03 | 教师界面不出现开发/运维概念 | A+B | `test_r1_data_cleanup.py::test_frontend_has_no_dev_concepts`；B-005-2 | 测试 |
| L-F04 | 识别失败显示为“失败/需处理”，不产生 0 分、不计入统计 | A+B | R1-008 AC1 | 测试 |
| L-F05 | 改判后分数、错题本、逐题正确率、成绩档案同步 | A+B | R1-008 AC2/AC3 | 测试 |
| L-U01 | 桌面侧栏常驻、高亮；≤3 次点击到达核心功能 | B | B-006-1、B-006-5 | 测试 |
| L-U02 | 登录后首页是工作台，能看到待办并一键进入 | B | B-006-2 | 测试 |
| L-U03 | 列表/详情页三态区分 | B | B-014-1、B-014-2；空账号用 B-006-3 的新教师 | 测试 |
| L-U05 | 公式在批改结果、错题本、逐题分析、教案中统一用 KaTeX | A+B | R1-012；教案页 B-012-2 | 测试 |
| L-U06 | 批改、教案在后台跑，显示阶段/已用时间/预计剩余；离开再回来进度不丢；完成有提示；变式题进行中不阻塞页面 | B | B-U06（批改、教案、变式题各测一次，`MOCK_LLM_DELAY_SECONDS=10`） | 测试 |
| L-U07 | 破坏性操作有二次确认，并说明连带删除什么 | B | B-U07（删除班级/学生/作业/批改记录/教案） | 测试 |
| L-U08 | 未知路由显示 404 页 | A+B | R1-014 AC3 | 测试 |
| L-S01 | bcrypt；失败提示不区分；5 分钟内 10 次失败锁 15 分钟 | A | R1-001 AC2/AC3/AC7；“5 分钟窗口”和“15 分钟解锁”在代码评审中确认 | 测试 |
| L-S02 | 未登录全部 401；前端 401 跳登录并回原页面 | A+B | R1-002 AC1；B-001-4、B-001-6 | 测试 |
| L-S03 | 按教师隔离，一律 404 | A | R1-002 AC2/AC3 | 测试 |
| L-S04 | 运维接口仅管理员 | A+B | R1-003 AC4 | 测试 |
| L-S05 | 密钥不入库、不进镜像；有 `.dockerignore` | A（模拟） | R1-003 AC2、`::test_no_plaintext_secrets_tracked`；`docker run … ls` 待补测 | 测试 |
| L-S06 | 生产关闭 docs、debug=false、CORS 白名单；全站 HTTPS | A+静态 | R1-003 AC3；HTTPS 只检查 nginx 样例和文档（实际证书留到部署评审） | 测试 |
| L-S07 | 扩展名 + 文件头校验；≤10MB、≤10 个文件；存储名随机；原始文件只有所属教师能下载 | A | `test_security.py`（现有）+ R1-003 AC5 + R1-002 AC3 | 测试 |
| L-S08 | 生产首次启动数据库为空 | A | `test_r1_data_cleanup.py::test_fresh_start_no_demo_seed` | 测试 |
| L-P01 | 登录页 + 工作台首屏 JS gzip ≤300KB；按路由拆包 | A+C+B | R1-010 AC1/AC2 | 测试 |
| L-P03（单份） | 单份 1~3 页作业真实批改 P90 ≤120 秒 | D | 真实评测时记录每份耗时（样本少，按最大值判定） | 测试 |
| L-P04 | 全局并发上限（默认 4，可配置）；内存峰值 <1.5GB | A+C | R1-007 AC4；C-009-5 | 测试 |
| L-D01 | compose 一条命令启动；只对外开放 80/443 | 静态 + 待补测 | `::test_compose_backend_hidden_volumes_healthcheck` | 测试 |
| L-D02 | 5MB 照片、45 个文件不被 nginx 拦 | 静态 + C | `::test_nginx_upload_limit_timeouts_headers`；C-009-2 | 测试 |
| L-D03 | 数据在宿主机卷上，重建容器不丢 | 静态 + 待补测 | compose 卷声明 | 测试 |
| L-D04 | 每日备份（保留 14 天），恢复步骤演练过 | A+C | R1-009 AC4；C-009-4 | 测试 |
| L-D05 | 部署文档与实际一致 | A+C | `::test_deploy_doc_consistent`；C-D05 按文档在本机（非 Docker）走一遍：配置 .env → 建管理员/教师 → 启动 → 登录 | 测试 |
| L-Q01 | 后端 pytest 全过；鉴权、隔离、改判、批量上传、失败判定都有用例 | A | 全量回归 `python -m pytest backend/tests`，报告写入 §6 | 测试（开发保证既有用例） |
| L-Q04 | 没有未关闭的 P0/P1 缺陷 | 查清单 | `docs/product/defects.md` | 测试 |
| L-Q05 | 主流程中浏览器控制台没有未捕获错误（React 警告除外） | B | B-F01 全程 `read_console_messages(onlyErrors)` | 测试 |
| L-Q03（本轮先跑） | 真实模型 ≥5 份，逐题判定与人工答案一致率 ≥90% | D | §7 真实评测 | 测试 |

## 4. 浏览器用例（B 类）

环境：后端 `uvicorn main:app --port 8041`（后台启动，`DATABASE_URL`、`UPLOAD_DIR`、`API_OUTPUT_ROOT` 都指向 scratch/qa），前端用 scratch 里的临时 vite 配置（root 指向 `E:/AI-Educator/frontend`，端口 3041，`/api` 代理到 8041）。每个用例在桌面 1366×768 下执行；标了 †的再在 375×812 下执行一遍，检查横向滚动和文字换行（L-U04 属于第 2 轮，本轮发现的问题只做记录）。

| 编号 | 步骤 | 期望 |
|---|---|---|
| B-001-1 | 命令开通 13800000001/王老师 → 登录页输入初始密码 | 进入“设置新密码”页，其他菜单不可用；设置后进工作台，顶栏显示“王老师” † |
| B-001-2 | 错误密码 / 不存在的账号 | 提示都是“账号或密码错误” |
| B-001-4 | 未登录直接打开 `/class` | 跳到 `/login?redirect=%2Fclass`；登录后回到 `/class` |
| B-001-5 | 登录 → 退出登录 → 浏览器后退 | 不显示业务数据；网络请求返回 401 |
| B-001-6 | 把 `aiedu_session` 换成过期 token（或 `SESSION_EXPIRE_MINUTES=1` 等 1 分钟），点任意按钮 | 跳登录页，提示“登录已过期，请重新登录” |
| B-001-7 | 登录页和各页面 `get_page_text` | 没有“123456”“演示账号”“演示密码”“返回首页” |
| B-001-8 | 设置 → 修改密码：旧密码错 / 新密码弱 / 成功 | 分别提示“当前密码不正确”、具体规则、成功；新密码能登录 |
| B-003-4 | 教师和管理员分别登录；教师直接访问 `/usage` | 教师菜单里没有“用量统计”，访问显示“无权限”；管理员能看到，且页面上没有服务器绝对路径 |
| B-004-1 | 侧栏检查；访问 `/questionbank/ai` | 没有题库相关入口；跳转到工作台 |
| B-004-2 | 设置页改姓名 → 刷新 → 退出重登 | 只有两个分区；顶栏姓名是新值 |
| B-004-4 | 逐页点击全部可交互元素（配合 `read_network_requests`） | 每个控件都有真实效果；没有“点了提示成功但没发请求” |
| B-005-2 | 逐页 `get_page_text` 检索 `dataset\|测试数据\|测试集\|调试模式\|class\d+\|作业 #\|token\|slug\|gpt\|gemini` † | 没有命中（管理员用量页除外） |
| B-005-3 | 新建作业并打开详情 | URL 里的 ID 等于接口返回的 `assignment_id` |
| B-006-1 | 1366×768 登录，依次点击每个菜单 | 侧栏常驻不收起，当前项高亮，折叠状态刷新后还在 |
| B-006-2 | 构造 1 份待复核、1 份批改中、1 份失败、1 次作业有未交（`MOCK_LLM_DELAY_SECONDS`）→ 看工作台 → 点每张卡片 | 数字与作业详情一致；进入对应作业并已按状态筛选 |
| B-006-3 | 新账号登录 | 显示三步引导；按引导完成建班 → 导入 → 布置作业 † |
| B-006-4 | 提交批改 → 打开顶栏任务抽屉；另开一个标签页清空 localStorage 后刷新 | 抽屉里有进度；两边一致 |
| B-006-5 | 从设置页出发到某作业的批量上传面板 | ≤3 次点击 |
| B-006-6 | 教师 / 管理员分别看菜单 | 教师没有“我的任务”“题库管理”“用量统计”；管理员有“用量统计” |
| B-006-7 | `/class` 新建、编辑、删除班级 | 都能完成；删除时二次确认说明连带删除什么 |
| B-007-1 | 批量上传面板选择 `陈晓明_1.jpg`、`陈晓明_2.jpg`、`林雨桐.jpg`、`2025003.jpg`、`IMG_0231.jpg`；再在有两个陈晓明的班级里试 | 对应结果符合 AC1/AC2；未对应的文件可以手动指定学生；点开始批改时提示“还有 N 个文件未对应学生，将被忽略” † |
| B-007-3 | 给已批改的学生分配文件 | 行上显示“将覆盖已有结果” |
| B-007-5 | 批量 10 份（延迟模拟），看进度条、名录、工作台；刷新；另一个会话登录 | 三处一致，每 4 秒刷新；刷新后进度不丢 † |
| B-007-7 | 名录行内点“上传” | 打开同一面板并预选该学生，不跳转到 /grader |
| B-007-8 | 没有参考答案的作业打开上传面板 | 黄色提示和“去填写参考答案”入口 |
| B-007-9 | `DAILY_GRADING_QUOTA=2` 启动，提交 3 份 | 第 3 份显示“今日批改额度已用完，明天再试或联系管理员” |
| B-008-1 | 上传空白 txt（或无题号文本） | 名录显示“失败：未识别到题目…”；成绩档案、逐题正确率、错题本不变 † |
| B-008-2 | 4 题对 2 题的结果页，把第 3 题改判为对 | 分数 50 → 75；顶部显示“老师已改判 1 题”；刷新后保持；逐题正确率、成绩档案、错题本同步 |
| B-008-3 | 把判对的题改判为错 | 错题本新增一条，来源“老师改判” |
| B-008-4 | 对改判过的提交点“重新批改” | 弹出“重新批改会覆盖你的改判，确定吗？” |
| B-008-5 | 名录“待复核”筛选 → 标记已复核 | 学生从筛选里消失；工作台待复核数减 1 |
| B-008-6 | 假模型返回 `reference_issue` 的结果页 | 黄色提示“AI 认为第 N 题参考答案可能有误：…” |
| B-010-2 | 清空网络记录后打开登录页 → 登录进工作台 → 在教案页点“导出 PDF” | 前两步没有 html2pdf/katex 相关 chunk；导出时才加载 |
| B-010-3 | 构建版（`vite preview`）打开登录页，读 Performance API | 记录 `domInteractive`、`loadEventEnd` 作参考 |
| B-011-1/3 | 导入两个陈晓明 → 分别上传批改 → 看名录、成绩档案、做错名单 | 两人分开显示，姓名后带学号 |
| B-012-1/2/3 | 结果页、错题本、逐题正确率、教案页检查公式；构造非法 LaTeX | 显示 `.katex`；可见文本里没有 LaTeX 源码；非法公式显示原文，console 没有未捕获异常 |
| B-014-1 | 停 8041 → 逐页打开工作台、班级、作业详情、错题本、教案 → 重启 → 点重试 | 显示错误态、中文原因和“重试”；恢复后正常 |
| B-014-2 | 代理加 3 秒延迟打开批改页 | 加载期间显示骨架或 spinner，不出现“还没有批改记录” |
| B-014-3 | 访问 `/no-such-page` † | 404 页，带“回到工作台”按钮 |
| B-F01 | L-F01 全流程（模拟模式），全程读 console | 每步无报错、无死链；控制台没有未捕获错误 |
| B-U06 | `MOCK_LLM_DELAY_SECONDS=10`：批改、教案、变式题各一次；中途离开页面再回来 | 显示阶段、已用时间、预计剩余；进度不丢；完成后抽屉或工作台有提示；变式题进行中不阻塞其他操作 |
| B-U07 | 删除班级、学生、作业、批改记录、教案 | 都有二次确认，并说明会连带删除什么 |

## 5. 命令检查（C 类）

| 编号 | 命令 / 做法 | 判定 |
|---|---|---|
| C-003-1 | `APP_ENV=production` 不设 `JWT_SECRET`，在 8041 用 uvicorn 实际启动 | 进程退出，日志里有“生产环境必须设置 JWT_SECRET” |
| C-004-3 | `grep -rn setTimeout frontend/src` | 逐条写出用途结论（§6） |
| C-007-6 | 8041 上用 `MOCK_LLM_DELAY_SECONDS=5`、`GRADING_CONCURRENCY=1` 批量提交 6 份 → `Stop-Process` 杀后端 → 重启 | 排队中的任务自动完成；进行中的那份标为失败，可以重试 |
| C-009-2 | 直连后端 8041 上传 8MB 图片 1 张、3 张 5MB 图片 1 份 | 后端单文件上限 10MB 下都成功（nginx 限制用静态检查判定） |
| C-009-4 | Git Bash 执行 `scripts/backup.sh`（数据目录指向 scratch 副本；用 Python sqlite3 替身）→ 删除数据目录 → `scripts/restore.sh` → 启动核对行数和上传文件 | 数据与备份时一致；按保留天数清理旧备份 |
| C-009-5 | 8041 上用 `MOCK_LLM_DELAY_SECONDS=2` 批量 45 份，`Get-Process` 每秒采样 WorkingSet | 峰值 < 1.5GB（近似替代 docker stats） |
| C-010-1 | `cd frontend && npx vite build --manifest --outDir <scratch>/build` | 构建成功；chunk 列表和首屏 gzip 合计写入 §6 |
| C-010-3 | 按首屏 gzip 体积估算 Fast 4G 下的下载时间 | ≤3 秒（估算） |
| C-D05 | 按 DEPLOY_2GB.md 的非 Docker 部分（.env、manage.py 命令、启动）在 scratch 里从零走一遍 | 文档中的命令都能照做 |
| C-Q01 | `python -m pytest backend/tests` | 全部通过（xfail 须有理由） |

## 6. 执行记录与进度

| 分组 | 开发提交 | 回归（全量） | 验收用例 | 浏览器 | 结论 | 缺陷 |
|---|---|---|---|---|---|---|
| 基线（开发前） | d3af4d3 | 191 passed, 1 xfailed（101s） | 骨架 92 项全部 xfail（run=False） | — | — | — |
| ① 账号与鉴权 | 0332f1e、ce4ce36 | 236 passed、74 xfailed（277s，含验收 19 项） | `test_r1_auth.py` 19/19 通过 | B-001-1/2/4/5/6/7/8、B-003-4（教师“无权限访问”、管理员可看）、B-004-2（个人资料保存后刷新、重新登录均为新值）；登录页 375px 无横向滚动 | R1-001 通过（AC6 有 1 个 P2 例外，见 D-001）；R1-002 通过 | D-001（P2） |
| ② 安全与部署 | 待提交 | | | | | |
| ③ 数据清理 | 待提交 | | | | | |
| ④ 批改可信 | 待提交 | | | | | |
| ⑤ 批量上传 | 待提交 | | | | | |
| ⑥ 信息架构 | 待提交 | | | | | |
| ⑦ 前端质量 | 待提交 | | | | | |

**第①组验收记录（2026-09-27）**
- 自动化：R1-001 AC1/2/3/5/7/8 和方案项、R1-002 AC1~AC4 和方案项全部通过。其中 AC4 在真实库副本上执行：迁移前后行数一致，`assign-orphans` 执行两次结果相同，A 能看到 3 个旧班级和全部旧批改，新教师 C 看到的所有列表都为空。
- 代码评审：锁定窗口 5 分钟、阈值 10 次、锁定 15 分钟（`auth.LoginLimiter`），账号不存在也计数；改密、重置、停用时 `session_version` 加 1，旧会话失效；鉴权统一挂在 `api.py` 的 `business` 路由上，`/api/usage/*` 挂 `require_admin`。已知限制：限流计数在进程内存里，重启后清零（部署为单进程，可以接受）。
- 浏览器（桌面 1366×768）：
  - 未登录访问 `/class` 会跳到 `/login?redirect=%2Fclass`；
  - 错误密码和不存在的账号都提示“账号或密码错误”；
  - 用初始密码登录后进入“设置新密码”，直接访问 `/settings` 也被拦回；初始密码输错提示“当前密码不正确”；保存后回到 redirect 页面，顶栏显示“王老师”；
  - 修改密码：弱密码被拒，改成功后旧密码不能登录、新密码可以；
  - 退出后按后退回到登录页，`/auth/me` 返回 401；
  - 会话失效后在“修改密码”点提交，跳登录页并提示“登录已过期，请重新登录”；但在“个人资料 → 保存修改”不跳转（D-001）；
  - 登录页和设置新密码页没有“123456”“演示密码”。
- 本组不判定的项：侧栏仍有“题库管理”“我的任务”，设置页仍有“班级管理”，属于第⑥组范围。

**环境事故（2026-09-26，已报告 main）**：QA 启动脚本里 `-replace '','/'` 写成了非法正则，`DATABASE_URL` 没设置上，8041 后端因此两次连到了真实库 `backend/teaching_assistant.db`，执行了开发新代码的无损启动迁移：加了 7 列，`homework_submissions.teacher_id` 的空值被补成 1。没有删除，业务数据没有改动。启动脚本已经修正，现在启动前会校验解析出的路径必须在 scratch 下，否则拒绝启动。

开发前预检发现（已通知开发，放在第②组处理，不单独登记缺陷）：
- 两个已跟踪文件里有明文模型密钥：`backend/test_api_call.py:5`、`backend/test_grader_flow.py:6`（`sk-4d1a…`）。已进入 git 历史，建议轮换。
- `config.py` 在 import 时强制读取 `config.json`；`.dockerignore` 排除它以后，镜像必须改为只靠环境变量启动，或者明确挂载配置文件。
- `backend/.env` 存在（被 git 忽略），但会进 docker 构建上下文。
- 本机 passlib 1.7.4 + bcrypt 5.0.0 不兼容（`CryptContext.hash` 抛 ValueError），开发已改为直接用 bcrypt。

## 7. 真实模型评测方案（L-Q03、L-P03）

- 样例：`dataset/测试集/批改作业` 的 10 个 md 文件中取 ≥5 份（优先选题型混合的：填空 + 解答）。
- 人工答案：测试 agent 逐题独立判定学生答案对错，形成“人工判定表”，数据集中已知的参考答案错误以人工判定为准。判定表入库到 `backend/tests/acceptance/real_eval/`，包含文件名、题号、学生答案、参考答案、人工判定、备注。
- 执行：设置 `LLM_API_KEY`（来自本机 config.json，不打印），通过 `e2e_real_model.py` 或等价脚本走 `POST /api/grader/upload`（批改前 OCR 由文本直通，不消耗识别调用），每份 1 次批改调用；预算 ≤20 次，计划 5~6 份 + 1 次图片上传（识别 + 批改，覆盖 L-F01“真实模型至少走通一次”和 L-P03 单份耗时）。
- 指标：逐题一致率 = 模型 `is_correct` 与人工判定一致的题数 / 总题数（≥90% 为通过）；单份耗时；失败或接口错误的份数；`reference_issue` 命中已知参考答案错误的情况。
- 注意：调用日志写入临时目录，不写入真实的 `api_runs/`；不修改 `backend/teaching_assistant.db`。

## 8. 风险与环境限制

- **R-1 没有 Docker/WSL/Linux 环境**：R1-009 AC1/AC3/AC5、L-D01、L-D03、L-S05 的镜像实测只能做静态检查和模拟（构建上下文模拟、非 Docker 启动、进程内存采样）。上线评审前须在 2 核 2GB Linux 服务器补测，这一项作为遗留风险写入第 7 章。
- **R-2 不能限速**：内置浏览器不能设置 Fast 4G 或 Slow 3G。R1-010 AC3 用体积估算加本地 Performance 数据；R1-014 AC2 用代理延迟模拟慢接口。
- **R-3 迁移口径**：真实库里有 473 条旧演示记录状态为 completed、有分数，但 `grading_result` 为空（没有逐题明细）。R1-008 的迁移规则“completed 且 0 题 → failed”如果把“没有明细”也当成 0 题，会把这批旧分数全部改成失败，影响“无损迁移”的承诺。验收用例按“只改确实是 0 题的记录，不动没有明细的旧记录”判定，如果开发另有口径，需要在第 7 章记录产品决策。
- **R-4 真实模型预算**：整轮 ≤20 次调用；为防超支，评测脚本在调用前打印预计次数，达到预算即停止。
