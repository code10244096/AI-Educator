"""每日题库爬虫：北京时间 00:00–08:00 窗口增量扩充 question_bank。

零 LLM 调用。复用 ProvinceGaokaoCrawler 与 import_open_math 去重导入模式。

用法：
  python backend/crawler/daily_crawl.py
  python backend/crawler/daily_crawl.py --source gaokao --force --dry-run
  python backend/crawler/daily_crawl.py --source open --force
  python backend/crawler/daily_crawl.py --source all --force

退出码：全部成功 0，部分失败 2，完全失败 1。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select


def _sanitize_proxy_env() -> None:
    """httpx 无法解析 NO_PROXY 中的 [::1]，清洗以免 AsyncClient 初始化即崩。"""
    for key in ("NO_PROXY", "no_proxy"):
        raw = os.environ.get(key)
        if not raw:
            continue
        parts = []
        for item in raw.split(","):
            item = item.strip()
            if not item or item in ("[::1]", "::1"):
                continue
            parts.append(item)
        os.environ[key] = ",".join(parts)

# backend/ 加入 path，以便 import crawl_province_gaokao / import_open_math / database
_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from crawl_province_gaokao import ProvinceGaokaoCrawler  # noqa: E402
from database import AsyncSessionLocal, init_db  # noqa: E402
from import_open_math import (  # noqa: E402
    BANK_DIR,
    CMATH_REPO,
    TAXONOMY_REPO,
    cmath_records,
    raw_dir,
    taxonomy_records,
)
from models import QuestionBank  # noqa: E402

BJ = ZoneInfo("Asia/Shanghai")
WINDOW_START = dt_time(0, 0)
WINDOW_STOP_NEW = dt_time(7, 50)  # 之后不再抓新页面，收尾入库
WINDOW_END = dt_time(8, 0)

MIN_INTERVAL_SEC = 3.0
MAX_RETRIES = 2
MAX_PAGES_PER_SOURCE = 500
MAX_QUESTIONS_PER_NIGHT = 2000
BATCH_SIZE = 100

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

LOG_DIR = _ROOT / "logs" / "crawler"
STATE_PATH = LOG_DIR / "open_sources_state.json"
RAW_OPEN = BANK_DIR / "_原始下载"

# 开放源：仓库 + 本地文件名 + 远端候选路径
OPEN_REPOS: List[Dict[str, Any]] = [
    {
        "key": "cn-math-taxonomy",
        "repo": "xiaoyang111222/cn-math-taxonomy",
        "files": [
            {
                "local": "cn-math-questions.json",
                "remote_paths": [
                    "cn-math-questions.json",
                    "data/cn-math-questions.json",
                    "questions/cn-math-questions.json",
                ],
            },
            {
                "local": "cn-math-topics.json",
                "remote_paths": [
                    "cn-math-topics.json",
                    "data/cn-math-topics.json",
                    "topics/cn-math-topics.json",
                ],
            },
        ],
    },
    {
        "key": "cmath",
        "repo": "XiaoMi/cmath",
        "files": [
            {
                "local": "cmath_dev.jsonl",
                "remote_paths": [
                    "cmath_dev.jsonl",
                    "data/cmath_dev.jsonl",
                    "dev.jsonl",
                ],
            },
        ],
    },
]

GAOKAO_PROVINCES = ["北京卷", "上海卷", "天津卷"]
GAOKAO_YEARS = range(2020, 2027)  # 含 2026


@dataclass
class SourceStats:
    new: int = 0
    dup: int = 0
    error: int = 0
    pages: int = 0
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "new": self.new,
            "dup": self.dup,
            "error": self.error,
            "pages": self.pages,
        }


def now_bj() -> datetime:
    return datetime.now(BJ)


def in_crawl_window(force: bool = False) -> Tuple[bool, str]:
    """是否允许启动。force 跳过窗口检查。"""
    if force:
        return True, "force 跳过时间窗口"
    t = now_bj().time()
    if WINDOW_START <= t < WINDOW_END:
        return True, f"当前北京时间 {now_bj().strftime('%H:%M:%S')} 在窗口内"
    return False, (
        f"当前北京时间 {now_bj().strftime('%Y-%m-%d %H:%M:%S')} "
        f"不在 {WINDOW_START.strftime('%H:%M')}-{WINDOW_END.strftime('%H:%M')} 窗口，退出"
    )


# --force 时跳过 07:50 停抓（验收/补跑）；正常调度仍在窗口内尊重截止点
_FORCE_RUN = False


def should_stop_new_pages() -> bool:
    """07:50 后不再抓新页面（force 模式除外）。"""
    if _FORCE_RUN:
        return False
    return now_bj().time() >= WINDOW_STOP_NEW


def normalize_question_text(text: str) -> str:
    """去空白与常见标点后用于内容 hash。"""
    if not text:
        return ""
    s = "".join(str(text).split())
    s = re.sub(r"[，。！？；：、,.!?;:\"'（）()【】\[\]《》<>·…—\-_/\\|+*=~`@#$%^&{}]", "", s)
    return s


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_question_text(text).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def setup_logging(day: str) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{day}.log"
    logger = logging.getLogger("daily_crawl")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


class RobotsCache:
    """按 origin 缓存 robots.txt，disallow 路径跳过。"""

    def __init__(self, client: httpx.AsyncClient, logger: logging.Logger):
        self.client = client
        self.logger = logger
        self._parsers: Dict[str, Optional[RobotFileParser]] = {}

    async def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._parsers:
            rp = RobotFileParser()
            robots_url = urljoin(origin + "/", "robots.txt")
            try:
                resp = await self._get_with_retry(robots_url)
                if resp is None or resp.status_code >= 400:
                    # 无法获取时保守放行，但记日志（常见站点无 robots 或 403）
                    self.logger.info("robots.txt 不可用，放行: %s", robots_url)
                    self._parsers[origin] = None
                else:
                    rp.parse(resp.text.splitlines())
                    self._parsers[origin] = rp
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("读取 robots.txt 失败 %s: %s", robots_url, exc)
                self._parsers[origin] = None

        parser = self._parsers[origin]
        if parser is None:
            return True
        ok = parser.can_fetch(USER_AGENT, url)
        if not ok:
            self.logger.info("robots disallow，跳过: %s", url)
        return ok

    async def _get_with_retry(self, url: str) -> Optional[httpx.Response]:
        delay = MIN_INTERVAL_SEC
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                await asyncio.sleep(MIN_INTERVAL_SEC if attempt == 0 else delay)
                return await self.client.get(url)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                delay = MIN_INTERVAL_SEC * (2 ** attempt)
                self.logger.warning("请求失败(%s/%s) %s: %s", attempt + 1, MAX_RETRIES + 1, url, exc)
        if last_exc:
            self.logger.error("重试耗尽 %s: %s", url, last_exc)
        return None


class RateLimitedFetcher:
    """≥3s 间隔、≤2 次指数退避重试、robots 检查。"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        robots: RobotsCache,
        logger: logging.Logger,
        page_budget: List[int],
    ):
        self.client = client
        self.robots = robots
        self.logger = logger
        self.page_budget = page_budget  # [used] mutable counter
        self._last_request_at = 0.0

    async def get_text(self, url: str) -> Optional[str]:
        if should_stop_new_pages():
            self.logger.info("已到 07:50，停止抓取新页面")
            return None
        if self.page_budget[0] >= MAX_PAGES_PER_SOURCE:
            self.logger.info("单源页面上限 %s 已达，停止", MAX_PAGES_PER_SOURCE)
            return None
        if not await self.robots.allowed(url):
            return None

        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_INTERVAL_SEC:
            await asyncio.sleep(MIN_INTERVAL_SEC - elapsed)

        delay = MIN_INTERVAL_SEC
        for attempt in range(MAX_RETRIES + 1):
            try:
                self._last_request_at = time.monotonic()
                resp = await self.client.get(url)
                self.page_budget[0] += 1
                resp.raise_for_status()
                return resp.text
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "抓取失败(%s/%s) %s: %s", attempt + 1, MAX_RETRIES + 1, url, exc
                )
                if attempt >= MAX_RETRIES:
                    return None
                await asyncio.sleep(delay)
                delay *= 2
                self._last_request_at = time.monotonic()
        return None


async def load_existing_dedup_keys(
    dry_run: bool,
) -> Tuple[Set[str], Set[str]]:
    """返回 (source_urls, content_hashes)。dry-run 仍可读库做去重统计，读失败则空集。"""
    urls: Set[str] = set()
    hashes: Set[str] = set()
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(QuestionBank.source_url, QuestionBank.question_text))).all()
            for source_url, question_text in rows:
                if source_url:
                    urls.add(source_url)
                if question_text:
                    hashes.add(content_hash(question_text))
    except Exception as exc:  # noqa: BLE001
        # dry-run 或库不可用时不阻断抓取
        logging.getLogger("daily_crawl").warning("加载去重键失败（继续，视为空库）: %s", exc)
    return urls, hashes


def row_to_bank_kwargs(row: dict) -> dict:
    return {
        "question_text": row["question_text"],
        "answer": row.get("answer") or "",
        "solution": row.get("solution") or "",
        "question_type": row.get("question_type") or "解答题",
        "subject": row.get("subject") or "数学",
        "education_level": row.get("education_level") or "高中",
        "grade": row.get("grade"),
        "exam_type": row.get("exam_type") or "",
        "year": row.get("year"),
        "region": row.get("region") or "",
        "knowledge_points": json.dumps(row.get("knowledge_points") or [], ensure_ascii=False),
        "difficulty": row.get("difficulty", 3),
        "score": row.get("score"),
        "source_url": row.get("source_url") or "",
        "teaching_tips": row.get("teaching_tips") or "",
        "common_mistakes": row.get("common_mistakes") or "",
        "is_verified": False,
    }


async def insert_batch(
    rows: List[dict],
    dry_run: bool,
    logger: logging.Logger,
) -> Tuple[int, int, int]:
    """入库；返回 (new, dup, error)。每批 100，单题失败不影响整批。"""
    if not rows:
        return 0, 0, 0
    if dry_run:
        logger.info("[dry-run] 跳过写库，本批候选 %s 条", len(rows))
        return len(rows), 0, 0

    new = dup = error = 0
    async with AsyncSessionLocal() as db:
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = rows[i : i + BATCH_SIZE]
            for row in chunk:
                try:
                    db.add(QuestionBank(**row_to_bank_kwargs(row)))
                    new += 1
                except Exception as exc:  # noqa: BLE001
                    error += 1
                    logger.warning("单题入库失败: %s", exc)
            try:
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                logger.error("批次提交失败，逐条重试: %s", exc)
                # 逐条提交，避免整批丢失
                for row in chunk:
                    try:
                        async with AsyncSessionLocal() as one:
                            one.add(QuestionBank(**row_to_bank_kwargs(row)))
                            await one.commit()
                    except Exception as one_exc:  # noqa: BLE001
                        error += 1
                        new = max(0, new - 1)
                        logger.warning("逐条入库失败: %s", one_exc)
    return new, dup, error


def filter_new_rows(
    records: List[dict],
    existing_urls: Set[str],
    existing_hashes: Set[str],
    night_new_total: int,
    stats: SourceStats,
) -> List[dict]:
    """两级去重 + 夜间总量上限。"""
    out: List[dict] = []
    for row in records:
        if night_new_total + len(out) >= MAX_QUESTIONS_PER_NIGHT:
            stats.notes.append(f"达到夜间总量上限 {MAX_QUESTIONS_PER_NIGHT}")
            break
        url = (row.get("source_url") or "").strip()
        text = row.get("question_text") or ""
        if not text.strip():
            stats.dup += 1
            continue
        h = content_hash(text)
        if url and url in existing_urls:
            stats.dup += 1
            continue
        if h in existing_hashes:
            stats.dup += 1
            continue
        if url:
            existing_urls.add(url)
        existing_hashes.add(h)
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# gaokao 源
# ---------------------------------------------------------------------------

async def crawl_gaokao(
    dry_run: bool,
    logger: logging.Logger,
    existing_urls: Set[str],
    existing_hashes: Set[str],
    night_new_total: int,
) -> SourceStats:
    stats = SourceStats()
    page_budget = [0]
    pending: List[dict] = []

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            robots = RobotsCache(client, logger)
            fetcher = RateLimitedFetcher(client, robots, logger, page_budget)
            crawler = ProvinceGaokaoCrawler()
            crawler.client = client
            # 覆盖 fetch，走礼仪与预算
            crawler.fetch_page = fetcher.get_text  # type: ignore[method-assign]

            for province in GAOKAO_PROVINCES:
                if should_stop_new_pages() or page_budget[0] >= MAX_PAGES_PER_SOURCE:
                    break
                if night_new_total + stats.new >= MAX_QUESTIONS_PER_NIGHT:
                    stats.notes.append("夜间总量上限，停止 gaokao")
                    break
                for year in GAOKAO_YEARS:
                    if should_stop_new_pages() or page_budget[0] >= MAX_PAGES_PER_SOURCE:
                        break
                    try:
                        questions = await _crawl_province_year_safe(
                            crawler, province, year, logger
                        )
                        # 补唯一 source_url（原爬虫写死站点根 URL）
                        for idx, q in enumerate(questions):
                            base = (q.get("source_url") or ProvinceGaokaoCrawler.BASE_URL).rstrip("/")
                            q["source_url"] = f"{base}/gaokao/{province}/{year}/q{idx + 1}"
                        fresh = filter_new_rows(
                            questions,
                            existing_urls,
                            existing_hashes,
                            night_new_total + stats.new,
                            stats,
                        )
                        pending.extend(fresh)
                    except Exception as exc:  # noqa: BLE001
                        stats.error += 1
                        logger.warning("gaokao %s %s 解析/抓取失败，跳过: %s", province, year, exc)

            stats.pages = page_budget[0]
            added, _dup, err = await insert_batch(pending, dry_run, logger)
            stats.new += added
            stats.error += err
            if not pending and stats.pages == 0 and stats.error == 0:
                stats.notes.append("未抓到页面（网络或站点结构）")
    except Exception as exc:  # noqa: BLE001
        stats.error += 1
        logger.exception("gaokao 源异常: %s", exc)
        stats.notes.append(str(exc))

    logger.info(
        "gaokao 完成 new=%s dup=%s error=%s pages=%s",
        stats.new, stats.dup, stats.error, stats.pages,
    )
    return stats


async def _crawl_province_year_safe(
    crawler: ProvinceGaokaoCrawler,
    province: str,
    year: int,
    logger: logging.Logger,
) -> List[dict]:
    """包装 crawl_province_year；站点结构变化时返回空列表而非崩掉。"""
    try:
        return await crawler.crawl_province_year(province, year) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("crawl_province_year 失败 %s %s: %s", province, year, exc)
        return []


# ---------------------------------------------------------------------------
# open 源
# ---------------------------------------------------------------------------

async def fetch_github_commit_sha(client: httpx.AsyncClient, repo: str, logger: logging.Logger) -> Optional[str]:
    url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
    delay = MIN_INTERVAL_SEC
    for attempt in range(MAX_RETRIES + 1):
        try:
            await asyncio.sleep(MIN_INTERVAL_SEC if attempt == 0 else delay)
            resp = await client.get(url, headers={"Accept": "application/vnd.github+json"})
            if resp.status_code == 403:
                logger.warning("GitHub API 限流/禁止: %s", repo)
                return None
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0].get("sha")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("获取 commit 失败(%s) %s: %s", attempt + 1, repo, exc)
            delay *= 2
    return None


async def download_open_file(
    client: httpx.AsyncClient,
    robots: RobotsCache,
    repo: str,
    remote_paths: List[str],
    dest: Path,
    logger: logging.Logger,
    page_budget: List[int],
) -> bool:
    mirrors = []
    for path in remote_paths:
        raw = f"https://raw.githubusercontent.com/{repo}/main/{path}"
        mirrors.append(raw)
        mirrors.append("https://gh-proxy.com/" + raw)
        # master 分支兜底
        raw_m = f"https://raw.githubusercontent.com/{repo}/master/{path}"
        mirrors.append(raw_m)
        mirrors.append("https://gh-proxy.com/" + raw_m)

    fetcher = RateLimitedFetcher(client, robots, logger, page_budget)
    for url in mirrors:
        if should_stop_new_pages() or page_budget[0] >= MAX_PAGES_PER_SOURCE:
            return False
        # raw/proxy 也可能有 robots；失败则跳过该 URL
        text = None
        # 二进制友好：直接 bytes
        if not await robots.allowed(url):
            continue
        elapsed = time.monotonic() - fetcher._last_request_at
        if elapsed < MIN_INTERVAL_SEC:
            await asyncio.sleep(MIN_INTERVAL_SEC - elapsed)
        delay = MIN_INTERVAL_SEC
        ok = False
        for attempt in range(MAX_RETRIES + 1):
            try:
                fetcher._last_request_at = time.monotonic()
                resp = await client.get(url)
                page_budget[0] += 1
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(resp.content)
                logger.info("已下载 %s <- %s (%s bytes)", dest.name, url, len(resp.content))
                ok = True
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("下载失败(%s) %s: %s", attempt + 1, url, exc)
                if attempt >= MAX_RETRIES:
                    break
                await asyncio.sleep(delay)
                delay *= 2
        if ok:
            return True
    return False


async def crawl_open(
    dry_run: bool,
    logger: logging.Logger,
    existing_urls: Set[str],
    existing_hashes: Set[str],
    night_new_total: int,
) -> SourceStats:
    stats = SourceStats()
    page_budget = [0]
    state = load_state()
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}

    try:
        async with httpx.AsyncClient(timeout=60.0, headers=headers, follow_redirects=True) as client:
            robots = RobotsCache(client, logger)
            any_updated = False

            for spec in OPEN_REPOS:
                if should_stop_new_pages():
                    stats.notes.append("07:50 停止 open 更新检查")
                    break
                key = spec["key"]
                repo = spec["repo"]
                sha = await fetch_github_commit_sha(client, repo, logger)
                prev = (state.get(key) or {}).get("commit")
                local_hashes = {
                    f["local"]: file_sha256(RAW_OPEN / f["local"])
                    for f in spec["files"]
                }
                changed = False
                if sha and sha != prev:
                    changed = True
                    logger.info("%s 远端 commit 变化: %s -> %s", key, prev, sha)
                elif not sha:
                    # API 不可用时，用本地缺失判定是否尝试下载
                    missing = [f["local"] for f in spec["files"] if not (RAW_OPEN / f["local"]).exists()]
                    if missing:
                        changed = True
                        logger.info("%s 无法取 commit，本地缺失 %s，尝试下载", key, missing)
                    else:
                        logger.info("%s 无 commit 信息且本地文件齐全，跳过下载", key)
                else:
                    logger.info("%s commit 未变 (%s)，跳过下载", key, sha)

                if changed:
                    for f in spec["files"]:
                        dest = RAW_OPEN / f["local"]
                        ok = await download_open_file(
                            client, robots, repo, f["remote_paths"], dest, logger, page_budget
                        )
                        if not ok:
                            stats.error += 1
                            stats.notes.append(f"下载失败 {key}/{f['local']}")
                        else:
                            any_updated = True
                    if sha:
                        state[key] = {
                            "commit": sha,
                            "checked_at": now_bj().isoformat(),
                            "file_hashes": {
                                f["local"]: file_sha256(RAW_OPEN / f["local"])
                                for f in spec["files"]
                            },
                        }
                else:
                    # 记录检查时间
                    state.setdefault(key, {})
                    state[key]["checked_at"] = now_bj().isoformat()
                    state[key]["file_hashes"] = local_hashes
                    if sha:
                        state[key]["commit"] = sha

            if not dry_run:
                save_state(state)
            else:
                logger.info("[dry-run] 不写 open_sources_state.json")

            # 有更新或本地已有原始文件时走去重导入逻辑
            source = raw_dir()
            if source is None:
                # 回退到 RAW_OPEN
                if (RAW_OPEN / "cn-math-questions.json").exists() and (
                    RAW_OPEN / "cn-math-topics.json"
                ).exists():
                    source = RAW_OPEN
            if source is None:
                stats.notes.append("本地无 open 原始文件，跳过导入")
                stats.pages = page_budget[0]
                return stats

            if not any_updated and not dry_run:
                # 即使未更新，仍可用本地文件做增量（库可能是空的）；只导入尚未入库的
                logger.info("open 远端无更新，仍按本地文件做 source_url 去重扫描")

            records: List[dict] = []
            try:
                q_path = source / "cn-math-questions.json"
                t_path = source / "cn-math-topics.json"
                if q_path.exists() and t_path.exists():
                    questions = json.loads(q_path.read_text(encoding="utf-8"))
                    topics = {
                        item["id"]: item
                        for item in json.loads(t_path.read_text(encoding="utf-8"))
                    }
                    records.extend(taxonomy_records(questions, topics))
                cmath_path = source / "cmath_dev.jsonl"
                records.extend(cmath_records(cmath_path))
            except Exception as exc:  # noqa: BLE001
                stats.error += 1
                logger.exception("解析 open 数据失败: %s", exc)
                stats.notes.append(f"解析失败: {exc}")
                stats.pages = page_budget[0]
                return stats

            # 去掉 _file 等写盘辅助字段
            cleaned = []
            for row in records:
                row = dict(row)
                row.pop("_file", None)
                if not row.get("source_url"):
                    # 兜底：taxonomy/cmath 已带 source_url
                    tip = row.get("teaching_tips") or ""
                    if "cmath" in tip.lower():
                        row["source_url"] = f"{CMATH_REPO}#missing"
                    else:
                        row["source_url"] = f"{TAXONOMY_REPO}#missing"
                cleaned.append(row)

            fresh = filter_new_rows(
                cleaned, existing_urls, existing_hashes, night_new_total + stats.new, stats
            )
            # dry-run 时 open 全量扫描可能极大；限制候选打印规模但统计仍准确
            if dry_run and len(fresh) > 200:
                logger.info(
                    "[dry-run] open 去重后候选 %s 条（仅入库模拟前 200 计入 new）",
                    len(fresh),
                )
                # 仍报告全部会新增的数量
                stats.new += len(fresh)
                stats.pages = page_budget[0]
                logger.info(
                    "open 完成 new=%s dup=%s error=%s pages=%s",
                    stats.new, stats.dup, stats.error, stats.pages,
                )
                return stats

            added, _dup, err = await insert_batch(fresh, dry_run, logger)
            stats.new += added
            stats.error += err
            stats.pages = page_budget[0]
    except Exception as exc:  # noqa: BLE001
        stats.error += 1
        logger.exception("open 源异常: %s", exc)
        stats.notes.append(str(exc))

    logger.info(
        "open 完成 new=%s dup=%s error=%s pages=%s",
        stats.new, stats.dup, stats.error, stats.pages,
    )
    return stats


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def write_summary(day: str, summary: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{day}-summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def decide_status(sources: Dict[str, SourceStats], ran: List[str]) -> str:
    if not ran:
        return "failed"
    errors = [sources[s].error for s in ran]
    news = [sources[s].new for s in ran]
    if all(e == 0 for e in errors):
        return "success"
    if all(e > 0 and n == 0 for e, n in zip(errors, news)):
        return "failed"
    return "partial"


def exit_code_for(status: str) -> int:
    if status == "success":
        return 0
    if status == "partial":
        return 2
    return 1


async def async_main(args: argparse.Namespace) -> int:
    global _FORCE_RUN
    _FORCE_RUN = bool(args.force)

    day = now_bj().strftime("%Y-%m-%d")
    logger = setup_logging(day)
    started = now_bj()

    ok, reason = in_crawl_window(force=args.force)
    if not ok:
        print(reason)
        logger.info(reason)
        summary = {
            "date": day,
            "started_at": started.isoformat(),
            "ended_at": now_bj().isoformat(),
            "sources": {},
            "total_new": 0,
            "status": "failed",
            "notes": reason,
        }
        write_summary(day, summary)
        return 1

    logger.info("启动 daily_crawl source=%s force=%s dry_run=%s | %s", args.source, args.force, args.dry_run, reason)

    if not args.dry_run:
        try:
            await init_db()
        except Exception as exc:  # noqa: BLE001
            logger.error("init_db 失败: %s", exc)
            write_summary(day, {
                "date": day,
                "started_at": started.isoformat(),
                "ended_at": now_bj().isoformat(),
                "sources": {},
                "total_new": 0,
                "status": "failed",
                "notes": f"init_db 失败: {exc}",
            })
            return 1

    existing_urls, existing_hashes = await load_existing_dedup_keys(args.dry_run)
    logger.info("已加载去重键 urls=%s hashes=%s", len(existing_urls), len(existing_hashes))

    sources_to_run: List[str] = []
    if args.source in ("gaokao", "all"):
        sources_to_run.append("gaokao")
    if args.source in ("open", "all"):
        sources_to_run.append("open")

    stats_map: Dict[str, SourceStats] = {}
    night_new = 0
    notes: List[str] = []

    if "gaokao" in sources_to_run:
        gstats = await crawl_gaokao(
            args.dry_run, logger, existing_urls, existing_hashes, night_new
        )
        stats_map["gaokao"] = gstats
        night_new += gstats.new
        notes.extend(gstats.notes)

    if "open" in sources_to_run:
        if night_new >= MAX_QUESTIONS_PER_NIGHT:
            notes.append("夜间总量已满，跳过 open")
            stats_map["open"] = SourceStats(notes=["夜间总量已满"])
        else:
            ostats = await crawl_open(
                args.dry_run, logger, existing_urls, existing_hashes, night_new
            )
            stats_map["open"] = ostats
            night_new += ostats.new
            notes.extend(ostats.notes)

    ended = now_bj()
    status = decide_status(stats_map, list(stats_map.keys()))
    # 若某源完全无页面且有网络类 notes，仍可能是 partial
    summary = {
        "date": day,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "sources": {k: v.as_dict() for k, v in stats_map.items()},
        "total_new": night_new,
        "status": status,
        "notes": "; ".join(notes) if notes else "",
        "dry_run": bool(args.dry_run),
        "force": bool(args.force),
    }
    path = write_summary(day, summary)
    logger.info("汇总写入 %s", path)
    logger.info("summary: %s", json.dumps(summary, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code_for(status)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="每日题库爬虫（00:00-08:00 北京时间）")
    p.add_argument(
        "--source",
        choices=["gaokao", "open", "all"],
        default="all",
        help="题目源（默认 all）",
    )
    p.add_argument("--force", action="store_true", help="忽略时间窗口强制运行")
    p.add_argument("--dry-run", action="store_true", help="只抓/扫描不写库，打印统计")
    return p


def main() -> None:
    _sanitize_proxy_env()
    args = build_parser().parse_args()
    code = asyncio.run(async_main(args))
    sys.exit(code)


if __name__ == "__main__":
    main()
