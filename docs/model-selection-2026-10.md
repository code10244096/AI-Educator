# 模型选型结论（2026-10）

现配置继续线上生效；试验配置仅作 A/B 对照记录，转正前不改 `models` / `fallbacks`。注释见 `backend/config.example.json` 的 `_comment_ab_test`。

## 现配置 vs 试验配置

| 功能 | 现配置（主 / 备用） | 试验配置（主 / 备用） |
|------|---------------------|----------------------|
| OCR 识别 | gpt-5.5 / deepseek-v4.1-flash | gpt-5.5 保留 / 可试 glm-5.3-flash |
| 批改 grade | gemini-3.1-pro-preview / deepseek-v4.1-flash | qwen3.8-max / gemini-3.1-pro-preview |
| 变式出题 variant | gemini-3.1-pro-preview / deepseek-v4-pro | deepseek-v4-flash / deepseek-v4-pro |
| 教案 lessonplan | gemini-3.1-pro-preview / deepseek-v4.1-flash | kimi-k3 / qwen3.8-max |

## 试验选择理由

- **批改**：qwen3.8-max 幻觉控制与指令遵循在国产模型中表现最好；批改最怕误判，优先稳妥。
- **变式出题**：deepseek-v4-flash 数学推理强且成本最低；注意 DeepSeek 峰谷计价（北京时间 9–12 / 14–18 点翻倍），批量任务排低谷。
- **教案**：kimi-k3 约 1M 上下文可装下整份课标教材，中文行文质量好。
- **OCR**：gpt-5.5 继续保留；备用可试 glm-5.3-flash（原生多模态、便宜）。glm-5.2 曾出现空回复，需在 5.3 上重新验证后再考虑接入。

## A/B 方法

用 `backend/tests/acceptance/real_eval` 同一批真实样本，分别跑现配置与试验配置，对比：

1. 批改判题一致率
2. 教案可用度
3. OCR 准确率
4. 成本

对比通过后再决定是否把试验配置写入生效字段。

## 复查节奏

模型版本迭代快，每月对照公开教育 / 高考榜单复查一次选型是否仍成立。
