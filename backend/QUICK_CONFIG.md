# 快速配置参考

## 🚀 三步配置

### 1️⃣ 打开配置文件
编辑 `backend/config.json`

### 2️⃣ 填写 API 密钥和模型
```json
"ai": {
  "api_key": "你的 API 密钥",
  "base_url": "API 地址",
  "ocr_model": "OCR 模型名称",
  "grader_model": "批改模型名称",
  "lessonplan_model": "教案模型名称"
}
```

### 3️⃣ 验证配置
```bash
cd backend
python -c "from config import settings; print(settings.OCR_MODEL, settings.GRADER_MODEL, settings.LESSONPLAN_MODEL)"
```

---

## 📦 常用模型配置

### 阿里云通义千问
```json
{
  "api_key": "sk-xxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-model/v1",
  "ocr_model": "qwen-vl-max",
  "grader_model": "qwen-max",
  "lessonplan_model": "qwen-max"
}
```

### OpenAI
```json
{
  "api_key": "sk-xxx",
  "base_url": "https://api.openai.com/v1",
  "ocr_model": "gpt-4-vision-preview",
  "grader_model": "gpt-4-turbo",
  "lessonplan_model": "gpt-4-turbo"
}
```

---

## 🎯 模型用途速查

| 配置项 | 用途 | 调用时机 |
|--------|------|----------|
| `ocr_model` | 图片文字识别 | 上传图片时 |
| `grader_model` | 作业批改 | 批改作业时 |
| `lessonplan_model` | 教案生成 | 生成教案时 |

---

## 🔍 故障排除

**配置加载失败？**
- 确保 `config.json` 在 `backend/` 目录
- 检查 JSON 格式是否正确

**API 调用失败？**
- 检查 `api_key` 是否正确
- 检查 `base_url` 是否正确
- 查看 API 余额/配额

**模型名称错误？**
- 确认模型名称拼写正确
- 确认该模型在你的账户中可用

---

## 📖 详细文档

- [AI_MODEL_CONFIG.md](./AI_MODEL_CONFIG.md) - 详细模型说明
- [CONFIG_GUIDE.md](./CONFIG_GUIDE.md) - 完整配置指南
