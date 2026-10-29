# 2026-10-29 工作日志

## 今日完成

### task-13：教案生成参考题库（按学科+年级）
- 需求书：`docs/daily/2026-10-29/task-13-plan-rag-grade.md`；cursor 开发（prompt-13，CURSOR_EXIT=0）。
- 改动：lesson_plans 新增 grade / referenced_question_ids 列 + 迁移；检索 v2 降级链（学科+年级→学科+学段→仅学科→仅学段）；标题关键词提取（去书名号/课时后缀）；parse_grade_number / grade_to_education_level；generate 接口接受可选 grade；前端教案表单加年级下拉、结果页显示参考题数。
- 验收：修复了 cursor 测试缺少 `app` fixture 导致 3 个用例连不上测试库的问题（补 app 参数）；全量 **348 passed**。
- 生产部署：推送 9d1e84f → 服务器 pull → compose 重建（BUILD_EXIT=0，双容器 healthy）→ 容器内跑 migrate_db.py 完成迁移。
- 生产实测：语文/三年级/「秋天的雨」生成 → 检索命中 6 题、返回题目 ID、正文含 5 处 `[题库ID:xxx]` 标注，测试数据已清理。

### 线上状态确认
- 网站 200，双容器 healthy；题库 271,194 行已在生产库。

## 待办（下一步）
- 抽样真实作业验证批改打分分布（上一轮走查发现 score=0/needs_review 观察项）。
- 前端年级下拉在真实浏览器里点一遍（本次只验证了 API 层）。

## 协作记录
- cursor（prompt-13）：产出合格；测试 fixture 使用不规范由我修正。

## 追加：性能诊断与 task-14 前端优化（16:56 用户反馈页面慢）

### 诊断结论
- 服务器新加坡，国内直连 RTT≈490ms，晚高峰吞吐~10KB/s；服务器本机回环 8ms，后端无瓶颈。
- 根因：跨境带宽 + 前端功能页静态依赖过重（教案页此前进入即拉 html2pdf 983KB + katex 261KB + markdown 132KB）。
- 注意：本机 shell 的 HTTPS_PROXY 会干扰测速，测速需 --noproxy '*'；用户浏览器如走 Clash 代理会更慢，建议域名直连。

### task-14 已完成并上线（ef2816f）
- html2pdf/katex/数学栈全部改动态按需加载；vendor-react 独立分包稳定缓存。
- 实测：首屏 ~103KB(gz)；教案页静态链从 ~520KB(gz) 降到 ~110KB(gz)，PDF 导出/公式渲染时再按需拉取。
- 遗留：根本解决需 CDN 或境内服务器（依赖域名 ICP 备案状态，待用户确认）。
