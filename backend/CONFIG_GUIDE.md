# 配置说明

## 配置文件位置

所有配置信息现在都存储在 `config.json` 文件中，不再需要 `.env` 文件。

## 如何配置

1. **复制示例配置文件**（如果还没有）：
   ```bash
   # config.json 已经存在，直接编辑即可
   ```

2. **编辑 `config.json` 文件**，填入你的配置信息：

### AI 模型配置（重要！）

在 `config.json` 中修改 `"ai"` 部分，配置三个不同的 AI 模型：

```json
"ai": {
  "api_key": "你的 API 密钥",
  "base_url": "https://api.openai.com/v1",
  "ocr_model": "gpt-4-vision-preview",
  "grader_model": "gpt-4",
  "lessonplan_model": "gpt-4"
}
```

**模型说明：**
- `ocr_model` - OCR 文字识别模型（用于识别图片中的题目和答案）
- `grader_model` - 作业批改模型（用于批改作业和生成变式题）
- `lessonplan_model` - 教案生成模型（用于生成教学方案）

### 其他配置

- **应用配置**：应用名称、版本、调试模式
- **API 配置**：路由前缀、CORS 跨域设置
- **数据库配置**：数据库连接 URL
- **文件上传**：上传目录、文件大小限制、允许的文件类型
- **JWT 配置**：密钥、算法、令牌过期时间

## 配置结构

```json
{
  "app": {                    # 应用配置
    "name": "应用名称",
    "version": "版本号",
    "debug": true/false
  },
  "api": {                    # API 配置
    "prefix": "/api",
    "cors_origins": ["允许的跨域地址"]
  },
  "database": {               # 数据库配置
    "url": "数据库连接字符串"
  },
  "ai": {                     # AI 模型配置（重点！）
    "api_key": "API 密钥",
    "base_url": "API 地址",
    "model": "主模型",
    "ocr_model": "OCR 模型"
  },
  "upload": {                 # 文件上传配置
    "dir": "./uploads",
    "max_file_size": 10485760,
    "allowed_extensions": ["jpg", "jpeg", "png", "gif"]
  },
  "jwt": {                    # JWT 配置
    "secret_key": "密钥",
    "algorithm": "HS256",
    "access_token_expire_minutes": 30
  }
}
```

## 注意事项

1. **API 密钥安全**：
   - 不要将包含真实 API 密钥的 `config.json` 提交到 Git
   - 生产环境使用环境变量或密钥管理服务

2. **JSON 格式**：
   - 确保 JSON 格式正确（逗号、引号、括号匹配）
   - 使用 JSON 编辑器或 IDE 的 JSON 插件检查格式

3. **路径配置**：
   - 上传目录 `upload.dir` 会自动创建，无需手动创建

## 验证配置

启动应用后，访问：
- http://localhost:8000/health - 健康检查
- http://localhost:8000/ - 应用信息

如果配置有误，应用启动时会抛出异常并提示错误信息。
