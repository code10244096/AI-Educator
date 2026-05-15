import json
import os
from pathlib import Path


def load_config():
    """加载 config.json 配置文件"""
    config_path = Path(__file__).parent / "config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在：{config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 格式错误：{e}")


# 加载配置
config = load_config()


class Settings:
    """应用配置设置类"""
    
    def __init__(self):
        # 应用配置
        self.APP_NAME = config.get("app", {}).get("name", "AI 教学助手")
        self.APP_VERSION = config.get("app", {}).get("version", "1.0.0")
        self.DEBUG = config.get("app", {}).get("debug", True)
        
        # API 配置
        self.API_PREFIX = config.get("api", {}).get("prefix", "/api")
        self.CORS_ORIGINS = config.get("api", {}).get("cors_origins", [
            "http://localhost:3000",
            "http://localhost:5173"
        ])
        
        # 数据库配置
        self.DATABASE_URL = config.get("database", {}).get("url", 
            "sqlite+aiosqlite:///./teaching_assistant.db")
        
        # AI 模型配置
        self.AI_API_KEY = config.get("ai", {}).get("api_key", "")
        self.AI_API_BASE_URL = config.get("ai", {}).get("base_url", 
            "https://api.openai.com/v1")
        self.OCR_MODEL = config.get("ai", {}).get("ocr_model", 
            "gpt-4-vision-preview")
        self.GRADER_MODEL = config.get("ai", {}).get("grader_model", "gpt-4")
        self.LESSONPLAN_MODEL = config.get("ai", {}).get("lessonplan_model", 
            "gpt-4")
        
        # 文件上传配置
        self.UPLOAD_DIR = config.get("upload", {}).get("dir", "./uploads")
        self.MAX_FILE_SIZE = config.get("upload", {}).get("max_file_size", 
            10 * 1024 * 1024)
        self.ALLOWED_EXTENSIONS = config.get("upload", {}).get(
            "allowed_extensions", ["jpg", "jpeg", "png", "gif"])
        
        # JWT 配置
        self.SECRET_KEY = config.get("jwt", {}).get("secret_key", 
            "your-secret-key-change-in-production")
        self.ALGORITHM = config.get("jwt", {}).get("algorithm", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = config.get("jwt", {}).get(
            "access_token_expire_minutes", 30)


# 创建全局配置实例
settings = Settings()
