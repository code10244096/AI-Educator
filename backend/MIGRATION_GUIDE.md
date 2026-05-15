# 配置文件迁移说明

## 📋 变更概述

从 **v1.1.0** 开始，项目配置文件从 `.env` 环境变量文件迁移到 **`config.json`** JSON 配置文件。

## 🔄 主要变化

### ❌ 旧方式（.env 文件）
```bash
# .env 文件
AI_API_KEY=your_api_key
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4
DATABASE_URL=sqlite+aiosqlite:///./db.db
```

### ✅ 新方式（config.json 文件）
```json
{
  "ai": {
    "api_key": "your_api_key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  },
  "database": {
    "url": "sqlite+aiosqlite:///./db.db"
  }
}
```

## 📝 迁移步骤

### 1. 备份现有配置（如果有）
```bash
# 如果之前有 .env 文件，先备份
cp .env .env.backup
```

### 2. 编辑 config.json
打开 `backend/config.json` 文件，修改以下关键配置：

```json
{
  "ai": {
    "api_key": "你的 API 密钥",        // ⚠️ 必须修改
    "base_url": "你的 API 地址",       // 根据需要修改
    "model": "gpt-4",                 // 根据需要修改
    "ocr_model": "gpt-4-vision-preview" // 根据需要修改
  }
}
```

### 3. 验证配置
```bash
cd backend
python -c "from config import settings; print(settings.APP_NAME)"
```

## 🎯 配置项对照表

| .env 变量 | config.json 路径 | 说明 |
|-----------|------------------|------|
| `AI_API_KEY` | `ai.api_key` | AI API 密钥 ⚠️ |
| `AI_API_BASE_URL` | `ai.base_url` | AI API 地址 |
| `OCR_MODEL` | `ai.ocr_model` | OCR 模型名称 |
| `GRADER_MODEL` | `ai.grader_model` | 作业批改模型 ⭐ |
| `LESSONPLAN_MODEL` | `ai.lessonplan_model` | 教案生成模型 ⭐ |
| `APP_NAME` | `app.name` | 应用名称 |
| `APP_VERSION` | `app.version` | 版本号 |
| `DEBUG` | `app.debug` | 调试模式 |
| `DATABASE_URL` | `database.url` | 数据库连接 |
| `UPLOAD_DIR` | `upload.dir` | 上传目录 |
| `SECRET_KEY` | `jwt.secret_key` | JWT 密钥 ⚠️ |

## ⚠️ 注意事项

1. **API 密钥安全**
   - `config.json` 已添加到 `.gitignore`
   - 不要将包含真实密钥的文件提交到 Git
   - 生产环境建议使用环境变量或密钥管理服务

2. **JSON 格式**
   - 确保使用双引号 `"` 而不是单引号 `'`
   - 最后一个属性后不要加逗号
   - 使用 JSON 编辑器验证格式

3. **向后兼容性**
   - 旧的 `.env` 文件不会被自动删除
   - 但系统不再读取 `.env` 文件
   - 可以安全删除旧的 `.env` 文件

## 🚀 优势

使用 JSON 配置文件的优势：

✅ **结构清晰** - 分层组织，易于理解  
✅ **类型安全** - JSON 原生支持多种数据类型  
✅ **注释支持** - 可以在代码中添加配置说明  
✅ **易于验证** - JSON 格式验证工具丰富  
✅ **统一管理** - 所有配置在一个文件中  

## 🔧 故障排除

### 问题 1：配置加载失败
```
FileNotFoundError: 配置文件不存在：config.json
```
**解决**：确保 `config.json` 在 `backend/` 目录下

### 问题 2：JSON 格式错误
```
ValueError: JSON 格式错误：...
```
**解决**：使用 JSON 验证工具检查格式，或从 `config.example.json` 复制

### 问题 3：API 调用失败
```
HTTPError: 401 Unauthorized
```
**解决**：检查 `ai.api_key` 是否正确配置

## 📚 相关文档

- [CONFIG_GUIDE.md](./CONFIG_GUIDE.md) - 详细配置指南
- [config.example.json](./config.example.json) - 配置示例文件

## 📞 需要帮助？

如果迁移过程中遇到问题，请查看：
- 项目 README.md
- 测试说明.md
- 或提交 Issue
