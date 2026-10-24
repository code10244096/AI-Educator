# Cursor 任务书：测试套件卫生——消除用例间污染 + 修复 17 个失败（task-07）

> 背景：`E:\AI-Educator\backend` 是 FastAPI + SQLite（aiosqlite）后端，测试在 `backend/tests/`（含 `tests/acceptance/` 子目录），用 **系统 Python：`py -m pytest`**（不要用 `python`，那是另一个无 pytest 的环境）。运行目录 `backend/`。
> 不要 git commit，不要动 `config.json` / `.env`，不要改产品代码的业务语义（第 2 条里的分数舍入如果是产品 bug 可以修产品代码，但必须说清依据）。

## 已完成的铺垫（不要重复做）

- `backend/test_*.py` 根目录 6 个手工冒烟脚本已移到 `backend/manual_tests/` 并修好 sys.path。
- 已建 `backend/pytest.ini`：`testpaths = tests`，注册了 `slow` mark。

## 现象（实测于 2026-10-25）

1. **用例间污染（主要矛盾）**：`py -m pytest tests -q` 全量跑 = **192 failed, 131 passed**；`py -m pytest tests --ignore=tests/acceptance -q` = **17 failed, 258 passed**。即 acceptance 目录的测试跑完后会污染后续单测（推测：事件循环策略、monkeypatch 未还原、chdir、全局 client/DB 状态、env var 泄漏等）。先读 `tests/conftest.py`、`tests/testenv.py`、`tests/fakes.py`、`tests/helpers.py` 和 `tests/acceptance/` 的 conftest，找出并修复污染源，使得**全量跑与排除 acceptance 跑的失败集之差归零**（全量失败的文件分布应与单跑各自文件一致）。
2. **17 个单测失败**清单（--ignore=acceptance 下）：
   - `tests/test_grading.py`：`test_upload_dataset_md_with_reference[deepseek_*.md]` 参数化 11 条全部失败；`test_wait_true_is_synchronous`（assert 66.7 == 67）；`test_retry_and_delete`；`test_grade_existing_submission_updates_class_view`；`test_ai_failure_marks_submission_failed`；`test_ai_failure_wait_true_returns_502_with_message`。
   - `tests/test_dataset.py::test_upload_dataset_with_fake_model`（assert 66...，同为分数问题）。
   - `tests/test_classes.py::test_homework_crud_grading_and_analysis`。
   - 参考数据集：`backend/tests/` 下应该有 markdown 参考样例目录（搜 `deepseek_markdown` 定位）。

## 要求

### A. 污染修复
- 根因在 conftest/fixture 层的就修 fixture 层（如 function 级隔离、autouse 清理 env、事件循环 fixture 不跨目录共享）；是 acceptance 测试自身泄漏的就地修（try/finally、monkeypatch 代替裸赋值等）。
- 修复标准：`py -m pytest tests -q` 全量与 `--ignore=tests/acceptance` 的**失败数量差 ≤ 2** 且失败集合不再出现「单跑全过、合跑就挂」的文件（重点验证 `test_auth.py` 19 条在合跑下也全过）。
- 不允许的修法：给失败测试加 skip/xfail 蒙混；重排测试顺序掩盖问题。

### B. 17 个失败修复
- `assert 66.7 == 67` 这一类：查清产品代码里总分的舍入逻辑（找 grading 相关 router/service），判断是产品 bug（如分项 round 后再加 vs 加完再 round）还是测试期望值算错。修正确的一方，并在回复里写明取舍依据。注意 `test_wait_true_is_synchronous` 的语义：wait=true 应同步返回最终结果。
- 11 条 `deepseek_markdown` 参考测试：先搞清这些测试在比对什么（参考 markdown 是"AI 产出基准"还是 fixture 输入），失败是产品输出格式变了还是断言太脆（如对空白/标点的精确比对）。合理做法是更新参考基准或放宽脆弱断言（保持对关键字段的强断言）。
- `test_ai_failure_*`：AI 失败路径下作业状态机（failed 标记、502 语义）与断言不符，查清状态机真实实现再对齐断言或修实现（依据写清楚）。

## 验证（必须全部贴输出）

1. `py -m pytest tests --ignore=tests/acceptance -q` 的末尾统计行。
2. `py -m pytest tests -q` 的末尾统计行。
3. 改动文件清单（git status / diff --stat）。

## 最终回复格式

污染根因（具体到文件/行/fixture）、17 个失败的分类与各自修法（特别注明哪些动了产品代码、依据是什么）、两组验证输出、遗留风险。
