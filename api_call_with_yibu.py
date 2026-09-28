# -*- coding: utf-8 -*-
# 功能说明：
# 使用 OpenAI 兼容接口批量调用模型，并为每次运行创建独立输出文件夹。
# 每次运行的文件夹名、日志文件、每条日志都会记录模型名、运行时间戳、run_id、API Key 后四位。
# 支持：
# 1. 默认 API Key：优先读取环境变量 YIBU_API_KEY，没有则使用 DEFAULT_API_KEY。
# 2. 代理开关：默认不走代理；传 --use-proxy 时走代理。
# 3. 走代理时默认不校验证书；不走代理时默认校验证书。
# 4. 每次输出独立文件夹，避免不同批次日志混在一起。
# 5. 可作为库被其他脚本调用：execute_api_run() / call_messages_once()。
#
# 依赖：
# pip install openai httpx

# python api_call_with_run_folder_v0603.py \
#   --api-key "你的真实key" \
#   --model "gemini-3.5-flash" \
#   --question "你好，简单回复一句话"

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


# =========================
# 0) 默认配置区
# =========================

DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://yibuapi.com/v1")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")

# 环境变量优先；如果没有环境变量，就用下面这个默认 key。
# 注意：正式共享脚本前建议把 DEFAULT_API_KEY 改回空字符串，避免泄露。
DEFAULT_API_KEY_ENV = ""
DEFAULT_API_KEY = ""

# 所有 run 文件夹都会放在这个根目录下。
DEFAULT_OUTPUT_ROOT = os.getenv("API_OUTPUT_ROOT", "api_runs")

# 默认不走代理。需要走代理时，命令行加 --use-proxy。
DEFAULT_USE_PROXY = True

# 代理默认值。也可以通过环境变量或命令行覆盖。
DEFAULT_PROXY_USERNAME = os.getenv("PROXY_USERNAME", None)
DEFAULT_PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", None)
DEFAULT_PROXY_HOST = os.getenv("PROXY_HOST", None)
DEFAULT_PROXY_PORT = os.getenv("PROXY_PORT", None)

DEFAULT_QUESTION = """
介绍长征23号
""".strip()


# =========================
# 1) 通用工具
# =========================

def ensure_dir(path: str) -> None:
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def now_utc_iso() -> str:
    """返回 UTC ISO 时间字符串。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def now_for_filename() -> str:
    """返回适合放进文件名的本地时间戳。"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def key_suffix(api_key: str) -> str:
    """只返回 API Key 后四位，避免日志泄露完整 key。"""
    api_key = (api_key or "").strip()
    if not api_key:
        return "none"
    return api_key[-4:]


def safe_filename_part(text: str, max_len: int = 80) -> str:
    """把模型名等字符串转成适合文件名的片段。"""
    text = str(text or "unknown").strip()
    text = re.sub(r"[^0-9A-Za-z._-]+", "_", text)
    text = text.strip("._-") or "unknown"
    return text[:max_len]


def json_dumps(obj: Any) -> str:
    """统一 JSON 序列化。"""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def append_jsonl(path: str, record: Dict[str, Any]) -> None:
    """追加写入一条 JSONL。"""
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json_dumps(record) + "\n")


def mask_secret(text: str, secret: str) -> str:
    """打印配置时遮盖密码。"""
    if not text or not secret:
        return text
    return text.replace(secret, "***")


# =========================
# 2) 代理与 OpenAI Client
# =========================

def build_proxy_url(args: argparse.Namespace) -> Optional[str]:
    """
    根据命令行参数生成代理地址。

    优先级：
    1. --proxy-url
    2. --proxy-username / --proxy-password / --proxy-host / --proxy-port
    """
    if args.proxy_url:
        return args.proxy_url

    username = args.proxy_username
    password = args.proxy_password
    host = args.proxy_host
    port = str(args.proxy_port or "")

    if not host or not port:
        return None

    if username and password:
        return f"http://{username}:{password}@{host}:{port}"

    return f"http://{host}:{port}"


def should_verify_ssl(args: argparse.Namespace) -> bool:
    """
    证书校验逻辑：

    - 不走代理：默认校验证书。
    - 走代理：默认不校验证书。
    - 如果用户显式传 --verify-ssl，则强制校验证书。
    - 如果用户显式传 --no-verify-ssl，则强制不校验证书。
    """
    if args.verify_ssl:
        return True

    if args.no_verify_ssl:
        return False

    if args.use_proxy:
        return False

    return True


def build_http_client(args: argparse.Namespace) -> Optional[Any]:
    """
    构造 httpx.Client。

    - 默认不启用代理。
    - 需要代理时传 --use-proxy。
    - 走代理时默认 verify=False。
    - 新版本 httpx 使用 proxy=，老版本使用 proxies=，这里做兼容。
    """
    if not args.use_proxy:
        return None

    import httpx

    proxy_url = build_proxy_url(args)
    if not proxy_url:
        raise ValueError("启用了 --use-proxy，但没有可用的代理地址。请检查 --proxy-url 或代理 host/port。")

    verify = should_verify_ssl(args)

    try:
        return httpx.Client(proxy=proxy_url, verify=verify, timeout=args.timeout)
    except TypeError:
        return httpx.Client(
            proxies={
                "http://": proxy_url,
                "https://": proxy_url,
            },
            verify=verify,
            timeout=args.timeout,
        )


def build_openai_client(args: argparse.Namespace, api_key: str) -> Tuple[Any, Optional[Any]]:
    """构造 OpenAI 兼容客户端，同时返回 http_client 方便最后关闭。"""
    import openai

    http_client = build_http_client(args)
    client_kwargs = {
        "api_key": api_key,
        "base_url": args.base_url,
        "max_retries": args.max_retries,
    }

    if http_client is not None:
        client_kwargs["http_client"] = http_client

    return openai.OpenAI(**client_kwargs), http_client


# =========================
# 3) 输入任务加载
# =========================

def normalize_messages_from_obj(
    obj: Any,
    prompt_field: str,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    把一行输入规范化为 messages。

    支持：
    - JSON 对象里有 messages 字段；
    - JSON 对象里有 prompt/question/text/content/input 字段；
    - 纯字符串。
    """
    meta: Dict[str, Any] = {}

    if isinstance(obj, dict):
        task_id = str(obj.get("id") or obj.get("task_id") or obj.get("uid") or uuid.uuid4())
        meta = {k: v for k, v in obj.items() if k not in {"messages"}}

        if isinstance(obj.get("messages"), list):
            return task_id, obj["messages"], meta

        prompt = obj.get(prompt_field)
        if prompt is None:
            for field in ("question", "text", "content", "input"):
                if obj.get(field) is not None:
                    prompt = obj[field]
                    break

        if prompt is None:
            prompt = json_dumps(obj)

        return task_id, [{"role": "user", "content": str(prompt)}], meta

    task_id = str(uuid.uuid4())
    return task_id, [{"role": "user", "content": str(obj)}], meta


def iter_jsonl(path: str) -> Iterable[Any]:
    """逐行读取 JSONL；如果某行不是合法 JSON，就把整行当 prompt。"""
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = {"id": f"line_{line_no}", "prompt": line}

            yield obj


def load_tasks(args: argparse.Namespace) -> List[Tuple[str, List[Dict[str, Any]], Dict[str, Any]]]:
    """加载待调用任务。"""
    tasks: List[Tuple[str, List[Dict[str, Any]], Dict[str, Any]]] = []

    if args.input_jsonl:
        for obj in iter_jsonl(args.input_jsonl):
            tasks.append(normalize_messages_from_obj(obj, args.prompt_field))
        return tasks

    if args.input_txt:
        with open(args.input_txt, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                tasks.append(
                    (
                        f"line_{line_no}",
                        [{"role": "user", "content": line}],
                        {"source_line_no": line_no},
                    )
                )

        return tasks

    question = args.question or DEFAULT_QUESTION
    tasks.append(("single_test", [{"role": "user", "content": question}], {}))
    return tasks


# =========================
# 4) usage 提取与单次调用
# =========================

def extract_usage_from_response(response: Any) -> Dict[str, int]:
    """
    从 OpenAI SDK 返回对象中提取 token 统计。

    兼容：
    - prompt_tokens / completion_tokens / total_tokens
    - input_tokens / output_tokens
    - completion_tokens_details.reasoning_tokens
    """
    usage = getattr(response, "usage", None)

    usage_rec = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "reasoning_tokens": 0,
    }

    if usage is None:
        return usage_rec

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    if prompt_tokens is None:
        prompt_tokens = getattr(usage, "input_tokens", 0)

    completion_tokens = getattr(usage, "completion_tokens", None)
    if completion_tokens is None:
        completion_tokens = getattr(usage, "output_tokens", 0)

    total_tokens = getattr(usage, "total_tokens", None)
    if total_tokens is None:
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

    usage_rec["prompt_tokens"] = int(prompt_tokens or 0)
    usage_rec["completion_tokens"] = int(completion_tokens or 0)
    usage_rec["total_tokens"] = int(total_tokens or 0)

    completion_details = getattr(usage, "completion_tokens_details", None)
    if completion_details is not None:
        usage_rec["reasoning_tokens"] = int(
            getattr(completion_details, "reasoning_tokens", 0) or 0
        )

    return usage_rec


def response_to_dict(response: Any) -> Dict[str, Any]:
    """尽量把 SDK 响应转成 dict；失败则只保留字符串。"""
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    return {"raw": str(response)}


def call_once(
    *,
    client: Any,
    task_id: str,
    messages: List[Dict[str, Any]],
    task_meta: Dict[str, Any],
    args: argparse.Namespace,
    run_meta: Dict[str, Any],
    log_jsonl: str,
    response_jsonl: str,
) -> Tuple[bool, Dict[str, int], float, str]:
    """调用一次模型，并写入日志。"""
    call_id = str(uuid.uuid4())
    start_ts = time.time()

    usage_zero = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "reasoning_tokens": 0,
    }

    request_params: Dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
    }

    if args.max_tokens is not None:
        request_params["max_tokens"] = args.max_tokens

    if args.top_p is not None:
        request_params["top_p"] = args.top_p

    log_record: Dict[str, Any] = {
        "schema_version": "api_call_log_v3",
        "run_id": run_meta["run_id"],
        "run_dir": run_meta["run_dir"],
        "run_ts_local": run_meta["run_ts_local"],
        "run_ts_utc": run_meta["run_ts_utc"],
        "call_id": call_id,
        "task_id": task_id,
        "ts_utc": now_utc_iso(),
        "api_key_suffix": run_meta["api_key_suffix"],
        "model": args.model,
        "base_url": args.base_url,
        "success": False,
        "elapsed_seconds": None,
        "usage": usage_zero.copy(),
        "request": request_params,
        "task_meta": task_meta,
        "response": {"content": ""},
        "error": None,
    }

    try:
        response = client.chat.completions.create(**request_params)
        elapsed = time.time() - start_ts

        content = response.choices[0].message.content or ""
        usage_rec = extract_usage_from_response(response)

        log_record["success"] = True
        log_record["elapsed_seconds"] = round(elapsed, 4)
        log_record["usage"] = usage_rec
        log_record["response"] = {
            "content": content,
            "finish_reason": getattr(response.choices[0], "finish_reason", None),
            "raw_response_id": getattr(response, "id", None),
        }

        if args.save_raw_response:
            log_record["raw_response"] = response_to_dict(response)

        append_jsonl(log_jsonl, log_record)

        append_jsonl(
            response_jsonl,
            {
                "run_id": run_meta["run_id"],
                "task_id": task_id,
                "call_id": call_id,
                "api_key_suffix": run_meta["api_key_suffix"],
                "model": args.model,
                "success": True,
                "elapsed_seconds": round(elapsed, 4),
                "usage": usage_rec,
                "content": content,
                "error": None,
            },
        )

        return True, usage_rec, elapsed, content

    except Exception as e:
        elapsed = time.time() - start_ts

        log_record["success"] = False
        log_record["elapsed_seconds"] = round(elapsed, 4)
        log_record["error"] = {
            "type": type(e).__name__,
            "message": str(e),
        }

        append_jsonl(log_jsonl, log_record)

        append_jsonl(
            response_jsonl,
            {
                "run_id": run_meta["run_id"],
                "task_id": task_id,
                "call_id": call_id,
                "api_key_suffix": run_meta["api_key_suffix"],
                "model": args.model,
                "success": False,
                "elapsed_seconds": round(elapsed, 4),
                "usage": usage_zero.copy(),
                "content": "",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            },
        )

        return False, usage_zero.copy(), elapsed, f"请求失败: {type(e).__name__}: {e}"


# =========================
# 5) run 目录创建
# =========================

def make_run_dir(args: argparse.Namespace, api_key: str) -> Tuple[str, Dict[str, Any]]:
    """为每次运行创建独立目录，并返回 run_meta。"""
    ensure_dir(args.output_root)

    run_id = str(uuid.uuid4())
    run_id_short = run_id[:8]
    run_ts_local = now_for_filename()
    run_ts_utc = now_utc_iso()

    model_safe = safe_filename_part(args.model)
    suffix = key_suffix(api_key)

    run_dir_name = f"{run_ts_local}_{model_safe}_key{suffix}_{run_id_short}"
    run_dir = os.path.join(args.output_root, run_dir_name)
    ensure_dir(run_dir)

    proxy_url = build_proxy_url(args) if args.use_proxy else ""
    proxy_url_masked = mask_secret(proxy_url or "", args.proxy_password)

    run_meta: Dict[str, Any] = {
        "schema_version": "api_run_meta_v3",
        "run_id": run_id,
        "run_id_short": run_id_short,
        "run_ts_local": run_ts_local,
        "run_ts_utc": run_ts_utc,
        "run_dir": os.path.abspath(run_dir),
        "api_key_suffix": suffix,
        "model": args.model,
        "base_url": args.base_url,
        "input_jsonl": args.input_jsonl,
        "input_txt": args.input_txt,
        "question_mode": bool(not args.input_jsonl and not args.input_txt),
        "use_proxy": bool(args.use_proxy),
        "proxy": {
            "enabled": bool(args.use_proxy),
            "host": args.proxy_host if args.use_proxy else "",
            "port": args.proxy_port if args.use_proxy else "",
            "url_masked": proxy_url_masked,
            "verify_ssl": should_verify_ssl(args),
        },
        "generation": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": args.max_tokens,
        },
    }

    return run_dir, run_meta


# =========================
# 6) 命令行入口
# =========================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenAI 兼容 API 批量调用脚本：每次运行独立文件夹，支持代理开关和 token 日志。"
    )

    # API 配置
    parser.add_argument(
        "--api-key",
        default=os.getenv(DEFAULT_API_KEY_ENV, DEFAULT_API_KEY),
        help=f"API Key。优先使用环境变量 {DEFAULT_API_KEY_ENV}；没有则使用脚本里的 DEFAULT_API_KEY。",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI 兼容接口地址。")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名称。")

    # 输入配置
    parser.add_argument("--input-jsonl", default="", help="批量输入 JSONL。支持 messages/prompt/question/text/content/input 字段。")
    parser.add_argument("--input-txt", default="", help="批量输入 TXT，一行一个 prompt。")
    parser.add_argument("--prompt-field", default="prompt", help="JSONL 中优先读取的 prompt 字段名。")
    parser.add_argument("--question", default="", help="单条测试问题；未传输入文件时生效。")

    # 输出配置
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT, help="所有 run 输出目录的根目录。")
    parser.add_argument("--save-raw-response", action="store_true", help="是否在日志中保存 SDK 原始响应。")

    # 生成参数
    parser.add_argument("--temperature", type=float, default=0.7, help="采样温度。")
    parser.add_argument("--top-p", type=float, default=None, help="top_p；不传则由服务端默认。")
    parser.add_argument("--max-tokens", type=int, default=None, help="最大输出 token；不传则由服务端默认。")
    parser.add_argument("--timeout", type=float, default=600.0, help="HTTP 超时时间，秒。")
    parser.add_argument("--max-retries", type=int, default=0, help="OpenAI SDK 内部重试次数。")
    parser.add_argument("--sleep", type=float, default=0.0, help="每次调用后 sleep 秒数，用于限速。")

    # 代理开关
    proxy_group = parser.add_mutually_exclusive_group()
    proxy_group.add_argument(
        "--use-proxy",
        dest="use_proxy",
        action="store_true",
        help="启用代理。启用后默认不校验证书。",
    )
    proxy_group.add_argument(
        "--no-proxy",
        dest="use_proxy",
        action="store_false",
        help="禁用代理。",
    )
    parser.set_defaults(use_proxy=DEFAULT_USE_PROXY)

    # 代理参数
    parser.add_argument("--proxy-url", default="", help="完整代理 URL，优先级最高。例如 http://user:pass@host:8080。")
    parser.add_argument("--proxy-username", default=DEFAULT_PROXY_USERNAME, help="代理用户名。")
    parser.add_argument("--proxy-password", default=DEFAULT_PROXY_PASSWORD, help="代理密码。")
    parser.add_argument("--proxy-host", default=DEFAULT_PROXY_HOST, help="代理 host。")
    parser.add_argument("--proxy-port", default=DEFAULT_PROXY_PORT, help="代理端口。")

    # SSL 证书开关
    ssl_group = parser.add_mutually_exclusive_group()
    ssl_group.add_argument(
        "--verify-ssl",
        dest="verify_ssl",
        action="store_true",
        help="强制开启 HTTPS 证书校验。",
    )
    ssl_group.add_argument(
        "--no-verify-ssl",
        dest="no_verify_ssl",
        action="store_true",
        help="强制关闭 HTTPS 证书校验。",
    )
    parser.set_defaults(verify_ssl=False, no_verify_ssl=False)

    return parser.parse_args()


# =========================
# 7) 库接口（供 extract_image_features 等脚本调用）
# =========================

Task = Tuple[str, List[Dict[str, Any]], Dict[str, Any]]


def build_namespace(**overrides: Any) -> argparse.Namespace:
    """根据关键字参数构造调用配置；未传字段使用脚本默认值。"""
    defaults: Dict[str, Any] = {
        "api_key": os.getenv(DEFAULT_API_KEY_ENV, DEFAULT_API_KEY),
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "input_jsonl": "",
        "input_txt": "",
        "prompt_field": "prompt",
        "question": "",
        "output_root": DEFAULT_OUTPUT_ROOT,
        "save_raw_response": False,
        "temperature": 0.7,
        "top_p": None,
        "max_tokens": None,
        "timeout": 600.0,
        "max_retries": 0,
        "sleep": 0.0,
        "use_proxy": DEFAULT_USE_PROXY,
        "proxy_url": "",
        "proxy_username": DEFAULT_PROXY_USERNAME,
        "proxy_password": DEFAULT_PROXY_PASSWORD,
        "proxy_host": DEFAULT_PROXY_HOST,
        "proxy_port": DEFAULT_PROXY_PORT,
        "verify_ssl": False,
        "no_verify_ssl": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def namespace_from_mapping(config: Mapping[str, Any], **overrides: Any) -> argparse.Namespace:
    """从 config.json 等字典构造调用配置。"""
    mapped = {
        "api_key": config.get("api_key"),
        "base_url": config.get("base_url"),
        "model": config.get("model"),
        "temperature": config.get("temperature"),
        "max_tokens": config.get("max_tokens"),
        "top_p": config.get("top_p"),
        "output_root": config.get("output_root") or config.get("api_output_root"),
        "use_proxy": config.get("use_proxy"),
        "proxy_url": config.get("proxy_url"),
        "proxy_username": config.get("proxy_username"),
        "proxy_password": config.get("proxy_password"),
        "proxy_host": config.get("proxy_host"),
        "proxy_port": config.get("proxy_port"),
        "timeout": config.get("timeout"),
        "max_retries": config.get("max_retries"),
        "sleep": config.get("sleep"),
        "save_raw_response": config.get("save_raw_response"),
    }

    cleaned = {k: v for k, v in mapped.items() if v is not None and v != ""}
    cleaned.update(overrides)
    return build_namespace(**cleaned)


def call_messages_once(
    args: argparse.Namespace,
    messages: List[Dict[str, Any]],
    *,
    task_id: str = "single_call",
    task_meta: Optional[Dict[str, Any]] = None,
    run_meta: Optional[Dict[str, Any]] = None,
    log_jsonl: str = "",
    response_jsonl: str = "",
) -> Tuple[bool, Dict[str, int], float, str]:
    """执行单次模型调用；可选写入 run 日志。"""
    if not args.api_key:
        raise ValueError("未提供 API Key")

    client, http_client = build_openai_client(args, args.api_key)
    try:
        if run_meta and log_jsonl and response_jsonl:
            return call_once(
                client=client,
                task_id=task_id,
                messages=messages,
                task_meta=task_meta or {},
                args=args,
                run_meta=run_meta,
                log_jsonl=log_jsonl,
                response_jsonl=response_jsonl,
            )

        start_ts = time.time()
        try:
            request_params: Dict[str, Any] = {
                "model": args.model,
                "messages": messages,
                "temperature": args.temperature,
            }
            if args.max_tokens is not None:
                request_params["max_tokens"] = args.max_tokens
            if args.top_p is not None:
                request_params["top_p"] = args.top_p

            response = client.chat.completions.create(**request_params)
            elapsed = time.time() - start_ts
            content = response.choices[0].message.content or ""
            usage = extract_usage_from_response(response)
            return True, usage, elapsed, content
        except Exception as exc:
            exc_info = f"{type(exc).__name__}: {exc}"
            elapsed = time.time() - start_ts
        return False, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
            }, elapsed, f"请求失败: {exc_info}"
    finally:
        if http_client is not None:
            http_client.close()


def execute_api_run(
    args: argparse.Namespace,
    tasks: List[Task],
    *,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    执行一批 API 调用，写入独立 run 文件夹，并返回汇总结果。

    Returns
    -------
    dict 包含 run_dir, run_meta, summary, results
    """
    if not tasks:
        raise ValueError("tasks 不能为空")

    run_dir, run_meta = make_run_dir(args, args.api_key)

    log_jsonl = os.path.join(run_dir, "api_calls.jsonl")
    response_jsonl = os.path.join(run_dir, "responses.jsonl")
    run_meta_json = os.path.join(run_dir, "run_meta.json")
    summary_json = os.path.join(run_dir, "summary.json")

    run_meta["log_jsonl"] = os.path.abspath(log_jsonl)
    run_meta["response_jsonl"] = os.path.abspath(response_jsonl)
    run_meta["summary_json"] = os.path.abspath(summary_json)

    with open(run_meta_json, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, ensure_ascii=False, indent=2)

    if verbose:
        proxy_url = build_proxy_url(args) if args.use_proxy else ""
        proxy_url_masked = mask_secret(proxy_url or "", args.proxy_password)
        print("=" * 90)
        print("API 批量调用开始")
        print("=" * 90)
        print(f"run_id: {run_meta['run_id']}")
        print(f"run_dir: {run_dir}")
        print(f"model: {args.model}")
        print(f"base_url: {args.base_url}")
        print(f"key_suffix: {run_meta['api_key_suffix']}")
        print(f"tasks: {len(tasks)}")
        print(f"use_proxy: {args.use_proxy}")
        print(f"proxy_url: {proxy_url_masked}")
        print(f"verify_ssl: {should_verify_ssl(args)}")
        print(f"log_jsonl: {log_jsonl}")
        print(f"response_jsonl: {response_jsonl}")

    client, http_client = build_openai_client(args, args.api_key)

    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    total_reasoning = 0
    success = 0
    failed = 0
    total_elapsed = 0.0
    results: List[Dict[str, Any]] = []

    try:
        for idx, (task_id, messages, task_meta) in enumerate(tasks, start=1):
            ok, usage, elapsed, content_or_error = call_once(
                client=client,
                task_id=task_id,
                messages=messages,
                task_meta=task_meta,
                args=args,
                run_meta=run_meta,
                log_jsonl=log_jsonl,
                response_jsonl=response_jsonl,
            )

            if ok:
                success += 1
            else:
                failed += 1

            total_elapsed += elapsed
            total_prompt += int(usage.get("prompt_tokens") or 0)
            total_completion += int(usage.get("completion_tokens") or 0)
            total_tokens += int(usage.get("total_tokens") or 0)
            total_reasoning += int(usage.get("reasoning_tokens") or 0)

            results.append(
                {
                    "task_id": task_id,
                    "success": ok,
                    "content": content_or_error if ok else "",
                    "error": None if ok else content_or_error,
                    "usage": usage,
                    "elapsed_seconds": round(elapsed, 4),
                    "task_meta": task_meta,
                }
            )

            if verbose:
                print(
                    f"[{idx}/{len(tasks)}] task_id={task_id} success={ok} "
                    f"elapsed={elapsed:.2f}s total_tokens={usage.get('total_tokens', 0)}"
                )
                if not ok:
                    print(f"    error: {content_or_error}")

            if args.sleep > 0 and idx < len(tasks):
                time.sleep(args.sleep)
    finally:
        if http_client is not None:
            http_client.close()

    summary = {
        "schema_version": "api_run_summary_v3",
        "run_id": run_meta["run_id"],
        "run_dir": os.path.abspath(run_dir),
        "run_ts_local": run_meta["run_ts_local"],
        "run_ts_utc": run_meta["run_ts_utc"],
        "api_key_suffix": run_meta["api_key_suffix"],
        "model": args.model,
        "base_url": args.base_url,
        "use_proxy": bool(args.use_proxy),
        "verify_ssl": should_verify_ssl(args),
        "total_calls": len(tasks),
        "success_calls": success,
        "failed_calls": failed,
        "success_rate": round(success / len(tasks) * 100, 4) if tasks else 0,
        "elapsed_seconds": round(total_elapsed, 4),
        "usage": {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "reasoning_tokens": total_reasoning,
        },
        "log_jsonl": os.path.abspath(log_jsonl),
        "response_jsonl": os.path.abspath(response_jsonl),
        "run_meta_json": os.path.abspath(run_meta_json),
    }

    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    append_jsonl(log_jsonl, {"type": "run_summary", **summary})

    if verbose:
        print("\n" + "=" * 90)
        print("本次 run 汇总")
        print("=" * 90)
        print(f"total_calls: {summary['total_calls']}")
        print(f"success_calls: {summary['success_calls']}")
        print(f"failed_calls: {summary['failed_calls']}")
        print(f"success_rate: {summary['success_rate']:.2f}%")
        print(f"elapsed_seconds: {summary['elapsed_seconds']:.2f}")
        print(f"prompt_tokens: {total_prompt}")
        print(f"completion_tokens: {total_completion}")
        print(f"total_tokens: {total_tokens}")
        print(f"reasoning_tokens: {total_reasoning}")
        print(f"run_dir: {run_dir}")
        print(f"log_jsonl: {log_jsonl}")
        print(f"response_jsonl: {response_jsonl}")
        print(f"summary_json: {summary_json}")

    return {
        "run_dir": run_dir,
        "run_meta": run_meta,
        "summary": summary,
        "results": results,
        "exit_code": 0 if failed == 0 else 2,
    }


def main() -> int:
    args = parse_args()
    args.api_key = "sk-cjiSTL6ZKGaM4RvocI2YOxMh7wpm8k1QiyeCJQDxjwdsJbs4"
    if not args.api_key or args.api_key == "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
        print(
            f"[ERROR] 未提供有效 API Key。可以设置环境变量：export {DEFAULT_API_KEY_ENV}='你的key'，"
            "或者修改脚本顶部 DEFAULT_API_KEY。",
            file=sys.stderr,
        )
        return 1

    tasks = load_tasks(args)
    if not tasks:
        print("[WARN] 没有读取到任何任务。")
        return 0

    result = execute_api_run(args, tasks, verbose=True)
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
