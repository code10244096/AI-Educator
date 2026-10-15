# Cursor 任务书：模型 A/B 试跑配置（config.example.json 注释更新）

> 交接方式：在 Cursor 聊天中输入「@docs/cursor-tasks/task-02-model-ab-config.md 按这份任务书执行」。
> 本任务**只改注释和文档，不改任何运行时代码、不改现有生效配置**。

## 背景

模型选型研究结论（2026-10）：现有配置（ocr=gpt-5.5，其余=gemini-3.1-pro-preview，备用 deepseek-v4.1 系列）继续保留为「现配置」；新增一套「试验配置」用于 A/B 对比。

## 改动

### 1. `backend/config.example.json`

在 `llm` 段的 `_comment_models` 注释之后，新增一个 `_comment_ab_test` 字段（纯注释，程序不读取，不影响 `load_llm_config`），内容为：

```
"试验配置（2026-10 选型研究，用 backend/tests/acceptance/real_eval 做 A/B 对比后决定是否转正）：
 grade（批改）: qwen3.8-max，fallback gemini-3.1-pro-preview —— 幻觉控制/指令遵循国产最强，批改最怕误判；
 variant（变式出题）: deepseek-v4-flash，fallback deepseek-v4-pro —— 数学推理强且最便宜，注意 DeepSeek 峰谷计价（北京时间 9-12/14-18 点翻倍），批量任务排低谷；
 lessonplan（教案）: kimi-k3，fallback qwen3.8-max —— 1M 上下文可吃下整份课标教材，中文行文好；
 ocr（识别）: gpt-5.5 保留，fallback 可试 glm-5.3-flash（原生多模态、便宜）；glm-5.2 的空回复问题需在 5.3 上重新验证。"
```

同时把 `_comment_models` 末尾补一句「现配置继续生效，试验配置见 _comment_ab_test」。

### 2. `docs/model-selection-2026-10.md`（新建，约一页）

把选型结论写成一页纸记录，包含：
- 现配置 vs 试验配置的按功能对照表；
- 每个选择的理由（对应上面注释里的要点）；
- A/B 方法：用 `backend/tests/acceptance/real_eval` 同一批真实样本分别跑两套配置，对比批改判题一致率、教案可用度、OCR 准确率、成本；
- 复查节奏：模型版本迭代快，每月对照公开教育/高考榜单复查一次。

## 验收标准

1. `config.example.json` 仍是合法 JSON（`python -c "import json;json.load(open('backend/config.example.json',encoding='utf-8'))"` 通过）。
2. 生效字段（models / fallbacks）与改动前完全一致，只新增注释字段。
3. 文档为中文，路径 `docs/model-selection-2026-10.md`。
