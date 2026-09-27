import json
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def load_config():
    """
    加载 config.json（可选）。生产环境建议全部走环境变量（见 .env.example），
    config.json 不存在时按空配置处理。
    """
    config_path = Path(os.getenv("CONFIG_FILE") or (BACKEND_DIR / "config.json"))
    if not config_path.exists():
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 格式错误：{config_path}：{e}")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _normalize_sqlite_url(url: str) -> str:
    """相对路径的 SQLite 库一律相对 backend/ 目录解析（避免在别的目录运行 manage.py 时建出另一个库）"""
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix):
        path = url[len(prefix):]
        if path and path != ":memory:" and not os.path.isabs(path) and not path.startswith("/"):
            return prefix + (BACKEND_DIR / path).resolve().as_posix()
    return url


# 加载配置
config = load_config()

DEFAULT_JWT_SECRET = "your-secret-key-change-in-production"


class Settings:
    """应用配置设置类（环境变量优先，其次 config.json，最后默认值）"""

    def __init__(self):
        # 运行环境：development / production
        self.APP_ENV = (os.getenv("APP_ENV") or config.get("app", {}).get("env") or "development").strip().lower()
        self.IS_PRODUCTION = self.APP_ENV == "production"

        # 应用配置
        self.APP_NAME = config.get("app", {}).get("name", "AI 教学助手")
        self.APP_VERSION = config.get("app", {}).get("version", "1.0.0")
        self.DEBUG = _env_bool("DEBUG", config.get("app", {}).get("debug", False)) and not self.IS_PRODUCTION
        # 是否打印 SQL（默认关闭；生产强制关闭）
        self.SQL_ECHO = _env_bool("SQL_ECHO", False) and not self.IS_PRODUCTION

        # API 配置
        self.API_PREFIX = config.get("api", {}).get("prefix", "/api")
        # 跨域白名单：生产只认环境变量 CORS_ORIGINS（逗号分隔，填部署域名）；未设置时不放行任何跨域请求
        # （前端与后端经 nginx 同域访问，本来就不需要跨域）
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env is not None and cors_env.strip():
            self.CORS_ORIGINS = [o.strip() for o in cors_env.split(",") if o.strip()]
        elif self.IS_PRODUCTION:
            self.CORS_ORIGINS = []
        else:
            self.CORS_ORIGINS = config.get("api", {}).get("cors_origins", [
                "http://localhost:3000",
                "http://localhost:5173"
            ])
        # 生产关闭 /docs、/redoc、/openapi.json
        self.ENABLE_API_DOCS = not self.IS_PRODUCTION

        # 数据库配置（记录来源，启动时打印实际使用的库，防止误连）
        if os.getenv("DATABASE_URL"):
            self.DATABASE_URL_SOURCE = "环境变量 DATABASE_URL"
        elif config.get("database", {}).get("url"):
            self.DATABASE_URL_SOURCE = "config.json"
        else:
            self.DATABASE_URL_SOURCE = "默认值（未设置 DATABASE_URL）"
        self.DATABASE_URL = _normalize_sqlite_url(
            os.getenv("DATABASE_URL") or config.get("database", {}).get(
                "url", "sqlite+aiosqlite:///./teaching_assistant.db")
        )

        # AI 模型配置
        self.AI_API_KEY = config.get("ai", {}).get("api_key", "")
        self.AI_API_BASE_URL = config.get("ai", {}).get("base_url",
            "https://api.openai.com/v1")
        self.OCR_MODEL = config.get("ai", {}).get("ocr_model",
            "gpt-4-vision-preview")
        self.GRADER_MODEL = config.get("ai", {}).get("grader_model", "gpt-4")
        self.LESSONPLAN_MODEL = config.get("ai", {}).get("lessonplan_model",
            "gpt-4")

        # 大模型网关配置（优先 "llm" 段，缺省回退到上面的 "ai" 段；LLM_API_KEY 等环境变量优先）
        from llm import load_llm_config
        self.LLM = load_llm_config(config.get("llm") or {}, config.get("ai") or {})

        # 文件上传配置
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR") or config.get("upload", {}).get("dir", "./uploads")
        self.MAX_FILE_SIZE = config.get("upload", {}).get("max_file_size",
            10 * 1024 * 1024)
        self.ALLOWED_EXTENSIONS = config.get("upload", {}).get(
            "allowed_extensions", ["jpg", "jpeg", "png", "gif"])
        # 单份作业（一次上传请求）最多文件数
        self.MAX_FILES_PER_SUBMISSION = _env_int("MAX_FILES_PER_SUBMISSION", 10)

        # 会话（JWT，存 httpOnly Cookie）
        self.JWT_SECRET = os.getenv("JWT_SECRET") or config.get("jwt", {}).get("secret_key", DEFAULT_JWT_SECRET)
        self.SECRET_KEY = self.JWT_SECRET  # 兼容旧名
        self.ALGORITHM = config.get("jwt", {}).get("algorithm", "HS256")
        # 会话有效期（分钟），默认 7 天；签发令牌时读取，可在运行时修改
        self.SESSION_EXPIRE_MINUTES = _env_int(
            "SESSION_EXPIRE_MINUTES", config.get("jwt", {}).get("session_expire_minutes", 7 * 24 * 60))
        self.ACCESS_TOKEN_EXPIRE_MINUTES = self.SESSION_EXPIRE_MINUTES  # 兼容旧名
        # bcrypt 计算强度（默认 12；自动化测试可调低以加快速度）
        self.BCRYPT_ROUNDS = _env_int("BCRYPT_ROUNDS", 12)
        # 会话 Cookie 是否只走 HTTPS（生产默认开启）
        self.COOKIE_SECURE = _env_bool("COOKIE_SECURE", self.IS_PRODUCTION)

        # 演示数据：仅开发环境显式开启时播种（生产强制关闭）
        self.SEED_DEMO_DATA = _env_bool("SEED_DEMO_DATA", False) and not self.IS_PRODUCTION

        # 批改队列：全局同时运行的批改任务数、每位教师每天最多提交的批改份数
        self.GRADING_CONCURRENCY = max(1, _env_int("GRADING_CONCURRENCY", 4))
        self.DAILY_GRADING_QUOTA = _env_int("DAILY_GRADING_QUOTA", 300)
        # 模拟模式下每次模拟调用的等待秒数（便于测试排队与进度）
        self.MOCK_LLM_DELAY_SECONDS = _env_float("MOCK_LLM_DELAY_SECONDS", 0.0)


# 创建全局配置实例
settings = Settings()


# 被视为“未修改”的示例密钥（生产环境拒绝启动）
_EXAMPLE_SECRETS = {
    DEFAULT_JWT_SECRET, "change-me", "changeme", "please-change-this-secret", "secret", "your-secret-key",
    "your_jwt_secret_here", "replace-with-a-long-random-string",
}


def production_problems(s: "Settings") -> list:
    """生产环境启动前的安全检查，返回问题列表（为空表示通过）"""
    if not s.IS_PRODUCTION:
        return []
    problems = []
    secret = (s.JWT_SECRET or "").strip()
    if not os.getenv("JWT_SECRET") or secret.lower() in _EXAMPLE_SECRETS or secret.lower().startswith(("your", "change", "<")):
        problems.append("生产环境必须设置 JWT_SECRET（环境变量，至少 32 位随机字符串，不能用示例值）")
    elif len(secret) < 32:
        problems.append("生产环境必须设置 JWT_SECRET：当前长度不足 32 位，请换成更长的随机字符串")
    if not s.LLM.enabled:
        problems.append("生产环境必须配置有效的 LLM_API_KEY（生产禁止模拟模式，否则老师会看到假的批改结果）")
    return problems
