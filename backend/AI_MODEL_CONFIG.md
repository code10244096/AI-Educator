# AI 模型配置说明

## 📋 模型概述

本系统使用三个不同的 AI 模型来处理不同的任务：

| 模型类型 | 配置项 | 默认值 | 用途 |
|---------|--------|--------|------|
| **OCR 模型** | `ocr_model` | `gpt-4-vision-preview` | 识别图片中的文字内容 |
| **批改模型** | `grader_model` | `gpt-4` | 批改作业、生成变式题 |
| **教案模型** | `lessonplan_model` | `gpt-4` | 生成教学方案 |

---

## 🔧 配置文件位置

所有模型配置都在 [`config.json`](./config.json) 文件中：

```json
{
  "ai": {
    "api_key": "你的 API 密钥",
    "base_url": "https://api.openai.com/v1",
    "ocr_model": "gpt-4-vision-preview",
    "grader_model": "gpt-4",
    "lessonplan_model": "gpt-4"
  }
}
```

---

## 📝 模型详细说明

### 1️⃣ OCR 模型 (`ocr_model`)

**用途：** 识别图片中的文字内容

**使用场景：**
- 作业图片文字识别
- 错题图片文字识别
- 提取题目和学生作答

**推荐模型：**
- OpenAI: `gpt-4-vision-preview`
- Azure OpenAI: `gpt-4v`
- 阿里云通义千问：`qwen-vl-max`
- 其他多模态模型

**配置示例：**
```json
"ocr_model": "gpt-4-vision-preview"
```

---

### 2️⃣ 批改模型 (`grader_model`)

**用途：** 批改作业和生成变式题

**使用场景：**
- 作业智能批改
- 判断答案正误
- 生成错题解析
- 生成变式练习题

**推荐模型：**
- OpenAI: `gpt-4`, `gpt-4-turbo`
- Azure OpenAI: `gpt-4`
- 阿里云通义千问：`qwen-max`, `qwen-plus`
- 其他强推理模型

**配置示例：**
```json
"grader_model": "gpt-4"
```

---

### 3️⃣ 教案模型 (`lessonplan_model`)

**用途：** 生成完整的教学方案

**使用场景：**
- 生成教案（包含教学目标、重难点、教学过程等）
- 教学设计建议
- 板书设计

**推荐模型：**
- OpenAI: `gpt-4`, `gpt-4-turbo`
- Azure OpenAI: `gpt-4`
- 阿里云通义千问：`qwen-max`, `qwen-plus`
- 其他强文本生成模型

**配置示例：**
```json
"lessonplan_model": "gpt-4"
```

---

## 🎯 模型调用流程

### 作业批改流程
```
上传图片 → OCR 模型识别 → 批改模型批改 → 返回结果
           ↓                  ↓
      提取文字内容        判断正误 + 解析
```

### 错题本流程
```
上传图片 → OCR 模型识别 → 批改模型生成变式题 → 保存
           ↓                  ↓
      提取题目内容        生成相似题目
```

### 教案生成流程
```
输入课题 → 教案模型生成 → 返回 Markdown 教案
           ↓
      完整教学方案
```

---

## 🔐 API 密钥配置

### 阿里云通义千问（DashScope）

```json
{
  "ai": {
    "api_key": "sk-xxxxxxxxxxxxxxxx",
    "base_url": "https://dashscope.aliyuncs.com/compatible-model/v1",
    "ocr_model": "qwen-vl-max",
    "grader_model": "qwen-max",
    "lessonplan_model": "qwen-max"
  }
}
```

### OpenAI

```json
{
  "ai": {
    "api_key": "sk-xxxxxxxxxxxxxxxx",
    "base_url": "https://api.openai.com/v1",
    "ocr_model": "gpt-4-vision-preview",
    "grader_model": "gpt-4-turbo",
    "lessonplan_model": "gpt-4-turbo"
  }
}
```

### Azure OpenAI

```json
{
  "ai": {
    "api_key": "xxxxxxxxxxxxxxxx",
    "base_url": "https://your-resource.openai.azure.com/openai/deployments",
    "ocr_model": "gpt-4v",
    "grader_model": "gpt-4",
    "lessonplan_model": "gpt-4"
  }
}
```

---

## 💡 配置建议

### 经济实惠方案
```json
{
  "ocr_model": "qwen-vl-max",
  "grader_model": "qwen-plus",
  "lessonplan_model": "qwen-plus"
}
```

### 高性能方案
```json
{
  "ocr_model": "gpt-4-vision-preview",
  "grader_model": "gpt-4-turbo",
  "lessonplan_model": "gpt-4-turbo"
}
```

### 混合方案（推荐）
```json
{
  "ocr_model": "qwen-vl-max",
  "grader_model": "gpt-4-turbo",
  "lessonplan_model": "gpt-4-turbo"
}
```

---

## ⚠️ 注意事项

1. **模型兼容性**
   - 确保选择的模型支持相应的功能（如多模态、JSON 输出等）
   - 不同模型的 API 调用格式可能不同

2. **成本控制**
   - OCR 识别调用频繁，建议使用性价比高的模型
   - 批改和教案生成对质量要求高，建议使用更强的模型

3. **性能优化**
   - 可以根据实际需求调整模型的 temperature 参数
   - 对于固定格式输出（如 JSON），使用较低的 temperature（0.3-0.5）

4. **错误处理**
   - 如果模型调用失败，检查 API 密钥和 base_url 是否正确
   - 查看应用日志获取详细错误信息

---

## 🧪 测试配置

配置完成后，可以运行以下命令测试：

```bash
cd backend
python -c "from config import settings; print(settings.OCR_MODEL, settings.GRADER_MODEL, settings.LESSONPLAN_MODEL)"
```

预期输出：
```
gpt-4-vision-preview gpt-4 gpt-4
```

---

## 📚 相关文档

- [CONFIG_GUIDE.md](./CONFIG_GUIDE.md) - 完整配置指南
- [config.json](./config.json) - 当前配置文件
- [config.example.json](./config.example.json) - 配置示例

---

## 🔗 模型 API 文档

- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [阿里云通义千问 API](https://help.aliyun.com/zh/dashscope/)
- [Azure OpenAI API](https://learn.microsoft.com/azure/ai-services/openai/)
