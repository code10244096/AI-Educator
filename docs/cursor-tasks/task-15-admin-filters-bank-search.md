# Cursor 任务书：管理后台表格增强 + 题库学科过滤与模糊搜索（2026-11-02）

> 分两个独立批次实施，不要 git commit，由验收方统一提交。构建用 `cd frontend && ./node_modules/.bin/vite build`。
> 约束：不引入新依赖；样式沿用项目现有 Tailwind 风格。

## 批次 A：管理员用量统计页（frontend/src/pages/UsageStats.jsx）

页面现状：多个 Card 表格区块（各模块用量 / 今日额度 / 按账号 / 使用记录 / 按功能 / 按模型 / 用户反馈）。

### A1 全部卡片默认折叠 + 展开箭头
- 每个 Card 增加折叠能力：标题行右侧加 `ChevronDown`（lucide-react）箭头按钮，点击切换展开/收起，箭头随状态旋转 180°。
- **默认全部折叠**，用户点击某一项才展开其内容。
- 若 Card 是通用组件（看现有实现），在组件层加 `collapsible`/`defaultOpen` 属性，保持非管理页复用处行为不变。

### A2 每个表格支持按列筛选
- 在每个表格表头下方加一行筛选行：每列一个小 input（样式轻量，`text-xs`），输入即对该列做**不区分大小写的包含匹配**过滤（前端过滤当前已加载的数据即可，不改后端）。
- 多列筛选条件之间为 AND。空输入不过滤。
- 数字列（tokens、次数）也按字符串包含匹配即可。
- 筛选行只在表格展开时可见；有筛选条件时显示一个「清除筛选」小按钮。

### A3 用量占比饼图
- 在「按功能」卡片内（表格上方）新增一张**按功能 tokens 消耗占比饼图**：
  - 用纯 SVG（或 conic-gradient）实现，不引入图表库；配色用项目现有色板（蓝/青/紫/橙等）。
  - 每个扇区对应一个功能（ocr/grade/variant/lessonplan 等），图例显示功能名 + 百分比（保留 1 位小数）。
  - 鼠标悬停扇区显示该功能的 tokens 数值（title 提示即可）。
- 数据直接用该卡片表格已有的数据，不新增接口。

## 批次 B：题库（backend/routers/questionbank.py + frontend/src/pages/BankBrowse.jsx）

### B1 按教师任教学科过滤
- 进入题库页时**只展示当前用户任教学科**（`user.subject`，体验账号默认「数学」）的题目：
  - 学科 Tab 默认选中本学科；列表与搜索请求都带上该 subject。
  - 保留切换到其他学科的能力（Tab 仍可点），但首次进入必须是本学科，不得出现「全部学科」。
  - 若 `user.subject` 不在题库学科列表（BANK_SUBJECTS）里，回退到「数学」。

### B2 模糊搜索增强
现状问题：`build_search_query` 只做 `question_text LIKE %keyword%`。实测「三角函数」在 question_text 仅命中 1 条，而 knowledge_points 字段命中 150 条、question_text 含「三角」有 5085 条——用户搜「三角函数」几乎搜不到东西。

改动：
1. **多字段匹配**：`WHERE (question_text LIKE %kw% OR knowledge_points LIKE %kw% OR search_keywords LIKE %kw%)`。
2. **空格分词**：关键词按空格拆成多个词，词间 AND，每个词按上面多字段 OR。
3. **常见主题同义词扩展**（后端常量表，放在 questionbank.py 顶部或 bank_subjects.py）：
   ```python
   SEARCH_SYNONYMS = {
       "三角函数": ["三角函数", "三角", "正弦", "余弦", "正切", "sin", "cos", "tan"],
       "导数": ["导数", "微分", "f'(x)", "切线"],
       "二次函数": ["二次函数", "抛物线"],
       "立体几何": ["立体几何", "三视图", "空间向量"],
       "数列": ["数列", "等差", "等比"],
       "概率": ["概率", "排列组合", "古典概型"],
   }
   ```
   命中映射时，这些词之间用 OR 连接（即「三角函数」= 任一相关词命中即可），不同空格分词之间仍 AND。大小写不敏感（对 sin/cos 等英文词，用 LOWER() 或 SQLite LIKE 默认行为即可，注明 SQLite LIKE 对 ASCII 不区分大小写）。
4. **相关度排序**：knowledge_points 命中的排前面，question_text 命中的排后面（CASE WHEN 实现），再按现有 id 倒序。
5. 保持现有限流/分页逻辑不变。

### B3 前端搜索提示
- 搜索框 placeholder 改为「输入知识点或关键词，如：三角函数、导数、二次函数」。
- 搜索无结果时显示「没有找到相关题目，试试更短的关键词（如：三角、导数）」。

## 验收标准
1. 管理页所有卡片默认折叠，点击箭头展开；每个表格可按列筛选。
2. 饼图正常渲染且百分比合计 100%。
3. 数学老师进入题库默认只看数学题；搜「三角函数」能返回多条相关题（knowledge_points 命中）。
4. `cd frontend && ./node_modules/.bin/vite build` 通过。
5. 后端改动不涉及数据库结构变更。
