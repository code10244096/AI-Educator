# AI 教学助手 后端 API

- 所有接口前缀 `/api`（`config.json -> api.prefix`）。
- 错误统一返回 `{"detail": "<中文原因>"}`。
- 通用状态码：`400` 参数不合法；`401` 未登录 / 登录已过期；`403` 需先修改初始密码 / 仅管理员可访问；`404` 资源不存在（**包括属于其他教师的资源**）；`409` 冲突（重复 / 任务进行中）；`413` 文件过大；`422` FastAPI 参数校验失败；`429` 登录尝试过多；`502` AI 模型调用失败（`detail` 为 `llm.LLMError` 的中文消息）。

## 鉴权与数据隔离（R1-001 / R1-002）

- **登录方式**：`POST /api/auth/login` 成功后写入会话 Cookie `aiedu_session`（JWT，httpOnly、`SameSite=Lax`，生产环境 `Secure`），浏览器自动携带；脚本 / 测试也可用请求头 `Authorization: Bearer <token>`。
- **有效期**：`SESSION_EXPIRE_MINUTES`（默认 10080 = 7 天），签发时读取。令牌内带 `sv`（`users.session_version`），**改密、管理员重置密码、停用账号**都会让旧会话立即失效。
- **公开接口**（无需登录）：`GET /`、`GET /health`、`POST /api/auth/login`、`POST /api/auth/logout`（只清 Cookie）。其余所有 `/api/*` 未登录一律 `401`：
  - 没带会话：`{"detail": "请先登录"}`；会话过期 / 失效：`{"detail": "登录已过期，请重新登录"}`。
- **初始密码**：`must_change_password=true` 的账号只能调用 `/api/auth/*`，其他业务接口一律 `403 {"detail": "请先修改初始密码"}`（前端据此只显示“设置新密码”页）。
- **管理员**：`/api/usage/*` 需要 `role=admin`，教师 `403 {"detail": "仅管理员可访问"}`。
- **按教师隔离**：班级、学生、作业、批改记录（含原始文件下载）、错题、教案、任务全部按当前教师过滤；按 ID 访问别人的资源一律 `404`（不用 403，避免暴露存在性），列表中也不可见。题库（`/questionbank/*`）是全校共用资源，只要求登录。
  - 归属字段：`classes.teacher_id`、`homework_assignments.teacher_id`、`homework_submissions.teacher_id`（新增）、`wrong_questions.user_id`、`lesson_plans.teacher_id`。
  - 后台任务（批改、教案、错题同步）使用任务记录上的教师 ID，不依赖请求上下文；每次模型调用的日志 `task_meta` 带 `teacher_id`。
- **登录限流**：同一账号（按输入的账号字符串，不区分是否存在）5 分钟内失败 10 次，锁定 15 分钟，期间登录返回 `429 {"detail": "尝试次数过多，请 15 分钟后再试"}`（单进程内存计数，重启清零）。
- **密码**：bcrypt 哈希（`$2b$`）；新密码 8~64 位，且同时包含字母和数字。

### 账号接口 `routers/auth.py`

| 方法 | 路径 | 请求 | 响应 / 状态码 |
|---|---|---|---|
| POST | `/auth/login` | JSON `{username, password}` | 200 `User` + `Set-Cookie`；401 `账号或密码错误`（账号不存在 / 密码错误 / 已停用，提示相同）；429 锁定 |
| POST | `/auth/logout` | – | 200 `{"message"}`，清除 Cookie |
| GET | `/auth/me` | – | 200 `User`（初始密码状态也可访问）；401 |
| PUT | `/auth/me` | JSON `{display_name?, school?}`（账号不可改） | 200 `User`；400 姓名为空 / 过长；403 需先改密 |
| POST | `/auth/change-password` | JSON `{old_password, new_password}` | 200 `{"message","user"}`（同时刷新当前 Cookie，其他设备会话失效）；400 `当前密码不正确` / 密码规则 / 与当前密码相同 |

User：`{id, username, display_name, school, role("teacher"|"admin"), must_change_password}`

### 管理命令 `backend/manage.py`（不开放注册，由管理员在服务器上执行）

```
python manage.py create-user --username 13800000001 --name 王老师 [--role admin] [--school 某中学] [--password <初始密码>] [--no-force-change]
python manage.py reset-password --username 13800000001 [--password <新初始密码>]
python manage.py disable-user --username 13800000001      # 停用（数据保留），enable-user 恢复
python manage.py list-users
python manage.py assign-orphans --username 13800000001    # 把无归属的历史数据归到该教师（幂等、无损）
```
- 不给 `--password` 时随机生成 10 位初始密码，输出中固定一行 `初始密码: <密码>`；老师首次登录后必须设置新密码（`--no-force-change` 仅供测试）。
- `assign-orphans` 的“无归属”= 归属为空、归属账号不存在、或归属于无法登录的历史占位账号（密码不是 bcrypt 哈希，如旧版播种的 `teacher`）。已属于真实教师的数据不动；作业先跟随所在班级、提交先跟随所属作业的真实归属，其余归到目标教师。
- 同名函数可直接 `import manage` 调用（同步函数）：`create_user(username, name, role='teacher', school=None, password=None, must_change_password=True) -> (user_id, password)`、`reset_password`、`disable_user`、`enable_user`、`list_users`、`assign_orphans`。
- 未配置 AI Key（或 `LLM_API_KEY=your_api_key_here`）时进入模拟模式：OCR / 批改 / 教案 / 变式题均返回本地模拟结果，不访问网络。
- 环境变量覆盖：`DATABASE_URL`、`UPLOAD_DIR`、`API_OUTPUT_ROOT`、`LLM_API_KEY`、`JWT_SECRET`、`SESSION_EXPIRE_MINUTES`、`COOKIE_SECURE`、`BCRYPT_ROUNDS`（相对路径的 SQLite 库按 `backend/` 目录解析）。
- 启动（FastAPI lifespan）：`create_all` + 幂等增量迁移（仅 `ALTER TABLE ADD COLUMN` / 新建索引，绝不删表/删数据）→ 静态演示数据播种（库中已有用户或班级时跳过；不调用 AI）→ 归属补齐（作业没有 `teacher_id` 时取班级的、提交没有时取作业的；只填空值）→ 把上次中断仍为 `processing` 的任务标记为 `failed`。

## 生产环境与配置（R1-003）

- 配置来源优先级：环境变量 > `config.json`（可选，镜像内不含）> 默认值。生产部署只用环境变量（`.env`，见仓库根目录 `.env.example` 与 `DEPLOY_2GB.md`）。
- 主要环境变量：`APP_ENV`（`development`/`production`）、`JWT_SECRET`、`SESSION_EXPIRE_MINUTES`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` / `LLM_MODEL_OCR|GRADE|VARIANT|LESSONPLAN`、`LLM_FALLBACK_<功能>`（逗号分隔）、`LLM_LOG_REQUEST_CONTENT`、`CORS_ORIGINS`（逗号分隔）、`DATABASE_URL`、`UPLOAD_DIR`、`API_OUTPUT_ROOT`、`GRADING_CONCURRENCY`、`DAILY_GRADING_QUOTA`、`MOCK_LLM_DELAY_SECONDS`、`SEED_DEMO_DATA`、`SQL_ECHO`、`COOKIE_SECURE`、`MAX_FILES_PER_SUBMISSION`。
- `APP_ENV=production` 时：
  - 启动前检查，不通过则**拒绝启动**并打印原因：未设置 `JWT_SECRET`（或是示例值 / 短于 32 位）→“生产环境必须设置 JWT_SECRET…”；`LLM_API_KEY` 为空或占位值（`your_api_key_here`、`sk-xxxx` 等）→“生产环境必须配置有效的 LLM_API_KEY（生产禁止模拟模式…）”。
  - 关闭 `/docs`、`/redoc`、`/openapi.json`（404）；`DEBUG=false`；不打印 SQL；会话 Cookie 带 `Secure`；不播种演示数据。
  - CORS 只放行 `CORS_ORIGINS` 中的域名；未设置时不放行任何跨域请求（前后端经 nginx 同域访问不需要跨域）。
- 启动日志第一行打印实际使用的数据库路径及来源；未显式设置 `DATABASE_URL` 时额外打印醒目警告。`manage.py` 同样在 stderr 打印所用数据库。
- `GET /` 只返回 `{"name","status"}`（不再暴露版本号）。

## 后台任务模式（作业批改 / 教案生成）

真实模型单次 20–60 秒，多图可达数分钟，因此：

1. `POST` 创建任务，立即返回 `status: "processing"` 与记录 ID；
2. 服务端在 asyncio 后台任务中执行（独立 DB 会话；图片 OCR 并发，信号量 3）；
3. 前端轮询 `GET` 详情接口，直到 `status` 为 `completed` 或 `failed`；进度文字在 `progress_stage`（`排队中` → `识别中 i/n` → `批改中` → `批改完成`；教案：`排队中` → `检索题库中` → `AI 生成中` → `生成完成`），失败原因在 `error_message`。

兼容/测试用：表单字段 `wait=true` 时接口同步执行完再返回（失败时 `502` + `detail=error_message`）。

---

## 作业批改 `routers/grader.py`

### 上传文件规则
- 允许扩展名：`png jpg jpeg gif bmp webp pdf docx txt md`，否则 `400`。
- 扩展名 + 文件头双重校验：内容与扩展名不符（如 `.exe` 改名 `.jpg`、伪造的 PDF、二进制文件冒充 `.txt`）→ `400 {"detail": "文件内容与格式不符"}`，不会送进模型。
- 一份作业（一次上传请求）最多 10 个文件（`MAX_FILES_PER_SUBMISSION`），超出 → `400`“一份作业最多上传 10 个文件…”；批量上传请按学生拆成多个请求。
- 单文件不超过 `settings.MAX_FILE_SIZE`（默认 10MB），否则 `413`；空文件 `400`。
- 存储名为 `uuid4().hex + 扩展名`（原始文件名仅用于展示，存于 `original_filenames`），不存在路径穿越。
- PDF：优先 PyMuPDF（文字层 + 扫描页渲染后 OCR），其次 pypdf（仅文字层）；两者都未安装时该文件解析失败（提示转为图片）。

### `POST /grader/upload` (multipart)
| 字段 | 说明 |
|---|---|
| `files` (必填, 可多个) | 作业文件 |
| `reference_answer` | 参考答案；为空时使用作业（assignment）的参考答案 |
| `subject` | 默认 `数学` |
| `assignment_id` | 关联班级作业（不存在 → 404） |
| `submission_id` | 覆盖重批某条提交（不存在 → 404；正在批改 → 409） |
| `student_name` | 学生姓名；与 `assignment_id` 同时给出且该学生已有提交时，复用那条提交 |
| `wait` | `true` 同步等待（默认 `false`） |

响应 200：
```json
{"submission_id": 550, "assignment_id": 14, "student_name": "小明",
 "status": "processing", "grading_status": "批改中", "progress_stage": "排队中",
 "error_message": null, "ocr_result": null, "grading_result": null, "image_count": 1}
```
`wait=true` 时 `status=completed`，`ocr_result` / `grading_result` 为完整结果（旧版同步接口的字段都在）。

### `GET /grader/submissions`
查询：`status`、`assignment_id`、`student_name`（模糊）、`include_seed`（默认 false：只列真正提交过批改任务的记录）、`limit`(1–200, 默认20)、`offset`。
响应：`{"items": [SubmissionSummary + assignment_title/class_slug/homework_id], "total": n}`

SubmissionSummary：`id, submission_id, assignment_id, student_name, subject, status, grading_status, progress_stage, error_message, score, wrong_count, file_names[], file_count, image_count, submit_time, is_test_data, dataset_file_id, created_at, finished_at`

### `GET /grader/{submission_id}`
批改详情 / 任务状态。404 不存在。响应 = SubmissionSummary +
`assignment_title, class_slug, homework_id, ocr_result, grading_result(对象, 未完成时为 {}), reference_answer`。

`status`：`pending`（演示数据中待批改）/ `processing` / `completed` / `failed`。
`grading_status`：`待批改` / `批改中` / `已批改`（失败后回到 `待批改`）。

`grading_result` 结构：
```json
{"total_questions": 5, "correct_count": 4, "wrong_count": 1, "score": 80,
 "questions": [{"question_number": 1, "question_text": "...", "student_answer": "...",
                "correct_answer": "...", "is_correct": true, "explanation": "..."}]}
```
批改完成后，错题自动同步到错题本（`source="grading"`，同一提交重批会先替换旧的同步错题），并刷新作业状态。

### `POST /grader/{submission_id}/retry` (form: `wait`)
用已保存的文件重新批改。404 / 409（进行中）/ 400（无可用文件）。响应同 upload。

### `DELETE /grader/{submission_id}`
删除提交及其同步的错题。409 进行中。响应 `{"message", "id"}`。

### `GET /grader/{submission_id}/files/{index}`
下载第 index 个原始文件（仅限上传目录 / dataset 目录）。只有提交所属教师能下载，其他教师 404。

### `GET /homework/dataset`
`{"items": [{"id","filename","title","question_count","file_size"}], "total"}`

### `GET /homework/dataset/{file_id}`
测试作业详情（`filename,title,question_count,student_content,reference_answer,full_content,file_size,id`）。404。

### `POST /grader/upload-dataset/{file_id}` (multipart)
字段：`subject, assignment_id, submission_id, student_name, class_slug, homework_id, wait`。
后台任务（跳过 OCR，直接用测试集文本）。响应同 upload，外加 `dataset_title, dataset_filename`。404 测试作业不存在。

---

## 错题本 `routers/notebook.py`

### `POST /notebook/upload` (multipart: `file`, `knowledge_point`(必填), `subject`)
同步：解析文件（图片走 OCR）+ 生成 3 道变式题（变式题失败不影响录入）。
- 成功：`{"id", "questions": [WrongQuestion + image_path], "knowledge_point", "variant_questions", "image_path"}`
- 业务性失败仍返回 200：`{"error", "error_type": "invalid_format"|"parse_failed"|"empty", "questions": []}`
- 413 文件过大；502 OCR 调用失败。

### `GET /notebook/list`
查询：`knowledge_point`(模糊), `subject`, `is_mastered`, `student_name`, `source`(`manual`/`grading`), `limit`(默认20, ≤500), `offset`。
响应：**数组** `[WrongQuestion]`，按时间倒序。
WrongQuestion：`id, question_text, user_answer, correct_answer, knowledge_point, subject, error_date, is_mastered, variant_questions[], student_name, submission_id, source, has_image`

### `GET /notebook/stats?subject=`
`{"total", "mastered", "unmastered", "knowledge_points": [{"name","count"}]}`

### `POST /notebook/{id}/mastered` / `POST /notebook/{id}/unmastered`
`{"message"}`；404。

### `POST /notebook/{id}/variants` (form: `count` 1–5，默认3)
同步调用 AI 重新生成变式题并保存。`{"id","variant_questions"}`；404；502。

### `DELETE /notebook/{id}`
`{"message","id"}`；404。

---

## 教案 `routers/lessonplan.py`

LessonPlan：`id, title, period, student_level, requirements, content(Markdown), status(processing|completed|failed), progress_stage, error_message, retrieved_questions_count, created_at, updated_at`（历史数据 status 为空时视为 `completed`）。

### `POST /lessonplan/generate` (form)
`title`(必填，空白 → 400), `period`(默认 `1 课时`), `student_level`(默认 `中等`), `requirements`, `wait`。
默认立即返回 LessonPlan（`status=processing`, `content=""`）；`wait=true` 返回完成的教案，失败 502。

### `GET /lessonplan/list`
查询：`keyword`（标题/要求模糊）, `status`, `limit`(默认20), `offset`。
响应：`{"items": [LessonPlan 去掉 content，加 preview(前120字), content_length], "total"}`

### `GET /lessonplan/{id}` → LessonPlan；404。
### `PUT /lessonplan/{id}` (JSON: `title?, content?, period?, student_level?, requirements?`) → LessonPlan；404；409 生成中；400 标题为空。
### `DELETE /lessonplan/{id}` → `{"message","id"}`；404；409 生成中。
### `POST /lessonplan/{id}/regenerate` (form: `wait`) → LessonPlan（processing）；409 生成中。
### `GET /lessonplan/{id}/export?format=md|txt|docx`
附件下载（`Content-Disposition` 带 `filename*=UTF-8''...`）。400 内容为空；422 format 非法。

---

## 班级 `routers/classes.py`

班级标识 `class_slug` 形如 `class{id}`（也接受纯数字 `id`）。不存在或不属于当前教师 → 404 `班级不存在`。

Class：`id, slug, name, students(=成员数), member_count, homework_count, subject, grade, created_at`

| 方法 | 路径 | 请求 | 响应 / 状态码 |
|---|---|---|---|
| GET | `/class/list` | – | `{"items":[Class]}` |
| POST | `/class` | JSON `{name, subject?, grade?}` | Class；400 名称为空 |
| GET | `/class/stats?class_slug=` | – | `{"total_students","average_wrong_count","common_wrong_questions":[{"question","count"}]}`（只统计已批改提交） |
| GET | `/class/{slug}` | – | Class |
| PUT | `/class/{slug}` | JSON `{name?, subject?, grade?}` | Class |
| DELETE | `/class/{slug}` | – | `{"message","deleted_assignments","deleted_submissions","deleted_members"}`（错题本保留） |

### 学生
Member：`id, class_id, name, gender, student_no, order_index, created_at`；列表项额外含 `avgScore, submittedCount, gradedCount, homeworkCount, trend(up|down|flat|null), status(优秀|良好|待提高|需关注|暂无成绩), rank`。

| 方法 | 路径 | 请求 | 响应 / 状态码 |
|---|---|---|---|
| GET | `/class/{slug}/members` | – | `{"items":[Member+统计]}` |
| POST | `/class/{slug}/members` | JSON `{name, gender?, student_no?}` | Member；400 空名；409 同名 |
| POST | `/class/{slug}/members/import` | multipart：`text` 和/或 `file`(.txt/.csv ≤1MB)；每行 `姓名[,性别][,学号]`，自动跳过表头 | `{"added_count","skipped_count","added","skipped","message"}`；400 |
| PUT | `/class/{slug}/members/{member_id}` | JSON `{name?, gender?, student_no?}`（改名同步该班提交记录上的姓名） | Member；404；409 |
| DELETE | `/class/{slug}/members/{member_id}` | – | `{"message"}`；404（提交记录保留） |

### 作业
Homework：`id`（展示 ID = dataset_file_id 或主键）, `assignment_id`（主键）, `title, date, deadline, submitted, total(=班级成员数), avgScore, status(待批改|已批改), description, datasetFileId, hasTestData, subject, referenceAnswer, gradedCount, pendingCount, processingCount`

| 方法 | 路径 | 请求 | 响应 / 状态码 |
|---|---|---|---|
| GET | `/class/{slug}/homework` | – | `{"items":[Homework]}` |
| POST | `/class/{slug}/homework` | JSON `{title, description?, reference_answer?, subject?, assign_date?, deadline?}` | Homework；400 标题为空 |
| GET | `/class/{slug}/homework/{homework_id}` | – | Homework；404 |
| PUT | `/class/{slug}/homework/{homework_id}` | JSON 同上（均可选） | Homework；404 |
| DELETE | `/class/{slug}/homework/{homework_id}` | – | `{"message","deleted_submissions"}`；404 |
| GET | `/class/{slug}/homework/{homework_id}/submissions` | – | `{"items":[StudentRow]}` |
| GET | `/class/{slug}/homework/{homework_id}/analysis` | – | `{"analyzed_count","graded_count","questions":[{"question_number","question_text","total","correct","correct_rate","wrong_students"}]}` |
| DELETE | `/class/{slug}/homework/{homework_id}/submissions/pending` | – | `{"message","deleted_count"}` |
| DELETE | `/class/{slug}/homework/{homework_id}/submissions/keep-first/{n}` | – | `{"message","deleted_count","kept_count"}` |
| GET | `/class/{slug}/homework-stats` | – | `{"currentHomework","submitRate","submitted","notSubmitted","total","gradedCount","pendingCount","pendingHomeworkCount","totalHomeworks","avgScore","passRate","gradedHomeworkCount"}` |
| GET | `/class/{slug}/grading-tasks` | – | `{"items":[{"id":"hw-{slug}-{hid}","type":"homework-grading","title","homeworkId","classId","status","progress","progressLabel","pendingCount","submitted","createdAt","priority"}]}` |
| GET | `/class/{slug}/alert-students` | – | `{"items":[{"name","score","trend","warning"}]}`（平均分<60、成绩骤降、当前作业未提交） |
| GET | `/class/{slug}/score-archive` | – | `{"items":[{"id","assignment_id","name","date","avgScore","highest","lowest","passRate","gradedCount","excellentCount","goodCount","passCount","failCount","distribution":[{"range","count","percentage"}],"topStudents":[{"name","score","rank"}]}]}` |

StudentRow：`id(序号), member_id, submission_id, name, submitStatus(已提交|未提交), submitTime, score, gradingStatus(已批改|待批改|批改中|未提交), wrongCount, fileCount, datasetFileId, isTestData, grading_result_id, status, progressStage, errorMessage`（含不在花名册但有提交的学生）

---

## 任务 `routers/tasks.py`
| 方法 | 路径 | 响应 |
|---|---|---|
| GET | `/tasks/all` | 所有班级的 grading-tasks 合并 `{"items":[...]}` |
| GET | `/tasks/jobs?limit=20` | 最近后台任务 `{"items":[{"job_type":"grader"|"lessonplan","id","title","status","progress_stage","error_message","created_at", "score"?}]}` |

## 题库 `routers/questionbank.py`（接口未变）
`POST /questionbank/add`(form)、`POST /questionbank/batch-add`(JSON 数组)、`GET /questionbank/list`、`GET /questionbank/stats`、`GET /questionbank/{id}`、`POST /questionbank/search`(form)。
（修复：`/questionbank/stats` 之前被 `/{question_id}` 抢先匹配返回 422，现已调整顺序。）

## 用量统计 `usage_api.py`（仅管理员）
`GET /usage/summary`、`GET /usage/calls`，需 `role=admin`，教师 403。响应不包含服务器上的日志目录路径（原 `log_root` 字段已移除）。见 `usage_api.py`。

## 其他
`GET /` → `{"name","version","status"}`；`GET /health` → `{"status":"healthy"}`（无 `/api` 前缀）。
