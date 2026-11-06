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

# 容器内 _ROOT=parents[2] 会落到 /；日志应写到 /app/logs/crawler（挂载卷）
_log_dir_env = (os.environ.get("CRAWLER_LOG_DIR") or "").strip()
LOG_DIR = Path(_log_dir_env) if _log_dir_env else (_BACKEND / "logs" / "crawler")
STATE_PATH = LOG_DIR / "open_sources_state.json"
RAW_OPEN = BANK_DIR / "_原始下载"

# 开放源：仓库 + 本地文件名 + 远端候选路径（API 会再动态校正）
OPEN_REPOS: List[Dict[str, Any]] = [
    {
        "key": "cn-math-taxonomy",
        "repo": "xiaoyang111222/cn-math-taxonomy",
        "files": [
            {
                "local": "cn-math-questions.json",
                # 仓库已改名为 data/questions.json
                "match_names": ["cn-math-questions.json", "questions.json"],
                "remote_paths": [
                    "data/questions.json",
                    "cn-math-questions.json",
                    "data/cn-math-questions.json",
                    "questions/cn-math-questions.json",
                ],
            },
            {
                "local": "cn-math-topics.json",
                # 仓库已改名为 data/topics.json
                "match_names": ["cn-math-topics.json", "topics.json"],
                "remote_paths": [
                    "data/topics.json",
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
                "match_names": ["cmath_dev.jsonl"],
                "remote_paths": [
                    "datasets/cmath_dev.jsonl",
                    "cmath_dev.jsonl",
                    "data/cmath_dev.jsonl",
                    "dev.jsonl",
                ],
            },
        ],
    },
]

# GitHub Contents 递归时跳过的目录 / 非题库数据文件名
_GITHUB_SKIP_DIRS = {
    ".git", ".github", "node_modules", "assets", "docs", "screenshots",
    "scripts", "tests", "explore", "children", "diagnose", "mappings",
    "_qbatches", "_second_pass",
}
_GITHUB_SKIP_NAME_SUBSTR = (
    "changelog", "license", "readme", "package", "manifest",
    "dependencies", "curriculum", "alias", "verification", "report",
    "distractor", "second_pass",
)

GAOKAO_PROVINCES = ["北京卷", "上海卷", "天津卷"]
GAOKAO_YEARS = range(2020, 2027)  # 含 2026
GAOKAO_ZHENTI_LIST = "https://www.gk100.com/zhenti/list_4002.htm"
GAOKAO_ZHENTI_MAX_PAGES = 8


@dataclass
class SourceStats:
    new: int = 0
    dup: int = 0
    dirty: int = 0
    error: int = 0
    pages: int = 0
    degraded: bool = False
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "new": self.new,
            "dup": self.dup,
            "dirty": self.dirty,
            "error": self.error,
            "pages": self.pages,
            "degraded": self.degraded,
        }


# 公告/网页残留拦截：入库源头过滤脏题干
_HTM_RESIDUE_RE = re.compile(r"\d+\.\s*htm", re.IGNORECASE)
# 合法选择题选项标记，或数学公式特征 → 关键词规则不判脏
_OPTION_OR_MATH_RE = re.compile(
    r"(?:^|\n)\s*A(?:[\.、]| )|"  # A. / A、 / \nA␠
    r"\$\$|"
    r"\\\(|"
    r"\\\["
)
_ADVICE_KEYWORDS = (
    # 线上真实公告六条（id 271636–271641）的完整措辞
    "平稳心态",
    "积极面对",
    "科学规划后续复习",
    "合理利用考后",
    "升学路径",
    "家庭沟通",
    "共商未来",
    "关注官方信息",
    "官方通知",
)
_NAV_SOURCE_KEYWORDS = (
    "下一页",
    "上一页",
    "点击进入",
    "本文整理",
    "本文来源",
    "新东方在线",
    "无忧考网",
    "gkxx",
    "www.",
    "http",
)


def looks_like_dirty_row(row: dict) -> bool:
    """判断爬虫行是否为公告/网页残留脏数据（入库前拦截）。

    规则：
    1. 题干前 20 字出现 ``数字. htm`` 列表页标题残留 → 脏；
    2. 命中考后建议或导航/来源关键词，且不含选项标记 / 公式特征 → 脏。
    """
    text = str(row.get("question_text") or "")
    if not text.strip():
        return False
    if _HTM_RESIDUE_RE.search(text[:20]):
        return True
    if _OPTION_OR_MATH_RE.search(text):
        return False
    lowered = text.lower()
    for kw in _ADVICE_KEYWORDS:
        if kw in text:
            return True
    for kw in _NAV_SOURCE_KEYWORDS:
        if kw.lower() in lowered:
            return True
    return False


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
    """两级去重 + 脏数据拦截 + 夜间总量上限。"""
    out: List[dict] = []
    dirty_n = 0
    dirty_sample = ""
    logger = logging.getLogger("daily_crawl")
    for row in records:
        if night_new_total + len(out) >= MAX_QUESTIONS_PER_NIGHT:
            stats.notes.append(f"达到夜间总量上限 {MAX_QUESTIONS_PER_NIGHT}")
            break
        url = (row.get("source_url") or "").strip()
        text = row.get("question_text") or ""
        if not text.strip():
            stats.dup += 1
            continue
        if looks_like_dirty_row(row):
            dirty_n += 1
            stats.dirty += 1
            if not dirty_sample:
                dirty_sample = str(text)[:60]
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
    if dirty_n:
        logger.warning("拦截脏数据 %s 条，样例: %s", dirty_n, dirty_sample)
    return out


# ---------------------------------------------------------------------------
# gaokao 源
# ---------------------------------------------------------------------------

def _mark_gaokao_degraded(stats: SourceStats, logger: logging.Logger, reason: str) -> None:
    """标记 gaokao 为 degraded：记日志与 notes，不抬高 error，以免拖垮其它源。"""
    stats.degraded = True
    note = f"degraded: {reason}"
    if note not in stats.notes:
        stats.notes.append(note)
    logger.warning("gaokao 源 degraded: %s", reason)


def _html_looks_image_only(html: str) -> bool:
    """gk100 真题正文常见为整页扫描图，无可用文本题干。"""
    if not html:
        return False
    img_n = len(re.findall(r"p\d?\.gk100\.com/article/|src=[\"'][^\"']+\.(?:jpg|jpeg|png|webp)", html, re.I))
    # 有题号文本则不算纯图
    has_numbered = bool(re.search(r"(?:^|>)\s*\d+\s*[\.、．]", html)) or "选择题" in html
    return img_n >= 3 and not has_numbered


def _match_zhenti_title(title: str, province: str, year: int) -> bool:
    prov = province.replace("卷", "")
    t = title or ""
    return str(year) in t and prov in t and "数学" in t


async def _collect_zhenti_links(
    fetcher: "RateLimitedFetcher",
    logger: logging.Logger,
) -> List[Tuple[str, str]]:
    """从 /zhenti/list_4002.htm 分页收集 (标题, 绝对 URL)。"""
    out: List[Tuple[str, str]] = []
    seen: Set[str] = set()
    from bs4 import BeautifulSoup  # 与 ProvinceGaokaoCrawler 同依赖

    for page in range(1, GAOKAO_ZHENTI_MAX_PAGES + 1):
        if should_stop_new_pages():
            break
        url = GAOKAO_ZHENTI_LIST if page == 1 else f"{GAOKAO_ZHENTI_LIST}?p={page}"
        html = await fetcher.get_text(url)
        if not html:
            logger.warning("zhenti 列表页不可用: %s", url)
            break
        soup = BeautifulSoup(html, "html.parser")
        page_hits = 0
        for link in soup.find_all("a", href=True):
            href = (link.get("href") or "").strip()
            text = " ".join((link.get_text() or "").split())
            if "read_" not in href or not text:
                continue
            if href.startswith("/"):
                href = ProvinceGaokaoCrawler.BASE_URL + href
            if href in seen:
                continue
            seen.add(href)
            out.append((text, href))
            page_hits += 1
        logger.info("zhenti 列表 p=%s 收录链接 %s（累计 %s）", page, page_hits, len(out))
        if page_hits == 0:
            break
    return out


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

            # 旧 /search/?q= 已不再返回匹配真题；改走高考数学真题列表
            zhenti_links = await _collect_zhenti_links(fetcher, logger)
            if not zhenti_links:
                # 诊断：旧搜索是否仍可用
                probe = (
                    f"{ProvinceGaokaoCrawler.BASE_URL}/search/"
                    f"?q={GAOKAO_PROVINCES[0]}+{list(GAOKAO_YEARS)[-2]}+数学+高考真题"
                )
                probe_html = await fetcher.get_text(probe)
                _mark_gaokao_degraded(
                    stats,
                    logger,
                    "gk100 真题列表不可用；/search/?q= 亦无法定位题目页（站点结构变化）"
                    + ("" if probe_html else "；搜索页抓取失败"),
                )
                stats.pages = page_budget[0]
                return stats

            image_only_pages = 0
            matched_years = 0
            parsed_questions = 0

            for province in GAOKAO_PROVINCES:
                if should_stop_new_pages() or page_budget[0] >= MAX_PAGES_PER_SOURCE:
                    break
                if night_new_total + stats.new >= MAX_QUESTIONS_PER_NIGHT:
                    stats.notes.append("夜间总量上限，停止 gaokao")
                    break
                for year in GAOKAO_YEARS:
                    if should_stop_new_pages() or page_budget[0] >= MAX_PAGES_PER_SOURCE:
                        break
                    targets = [
                        url for title, url in zhenti_links
                        if _match_zhenti_title(title, province, year)
                    ]
                    if not targets:
                        logger.info("zhenti 列表未匹配 %s %s", province, year)
                        continue
                    matched_years += 1
                    try:
                        questions: List[dict] = []
                        for url in targets[:2]:
                            html = await fetcher.get_text(url)
                            if not html:
                                continue
                            qs = crawler.parse_questions_from_html(html, year, province) or []
                            if qs:
                                questions.extend(qs)
                            elif _html_looks_image_only(html):
                                image_only_pages += 1
                                logger.info(
                                    "gaokao 页面为图片扫描、无文本题干: %s %s %s",
                                    province, year, url,
                                )
                        parsed_questions += len(questions)
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

            if parsed_questions == 0 and image_only_pages > 0:
                _mark_gaokao_degraded(
                    stats,
                    logger,
                    "gk100 真题正文为图片扫描件，文本解析器无法抽取题目；"
                    "旧搜索页 /search/?q= 已不再返回匹配结果（已改用 /zhenti/list_4002.htm）",
                )
            elif parsed_questions == 0 and matched_years == 0:
                _mark_gaokao_degraded(
                    stats,
                    logger,
                    "zhenti 列表无北京/上海/天津卷匹配项，且无法从页面抽取文本题",
                )
            elif not pending and stats.pages == 0 and stats.error == 0 and not stats.degraded:
                stats.notes.append("未抓到页面（网络或站点结构）")
    except Exception as exc:  # noqa: BLE001
        stats.error += 1
        logger.exception("gaokao 源异常: %s", exc)
        stats.notes.append(str(exc))

    logger.info(
        "gaokao 完成 new=%s dup=%s error=%s pages=%s degraded=%s",
        stats.new, stats.dup, stats.error, stats.pages, stats.degraded,
    )
    return stats


# ---------------------------------------------------------------------------
# open 源
# ---------------------------------------------------------------------------

def _github_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _github_api_get(
    client: httpx.AsyncClient,
    url: str,
    logger: logging.Logger,
) -> Optional[Any]:
    delay = MIN_INTERVAL_SEC
    for attempt in range(MAX_RETRIES + 1):
        try:
            await asyncio.sleep(MIN_INTERVAL_SEC if attempt == 0 else delay)
            resp = await client.get(url, headers=_github_headers())
            if resp.status_code == 403:
                logger.warning("GitHub API 限流/禁止: %s", url)
                return None
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("GitHub API 失败(%s) %s: %s", attempt + 1, url, exc)
            delay *= 2
    return None


async def fetch_github_default_branch(
    client: httpx.AsyncClient, repo: str, logger: logging.Logger
) -> str:
    data = await _github_api_get(client, f"https://api.github.com/repos/{repo}", logger)
    if isinstance(data, dict) and data.get("default_branch"):
        return str(data["default_branch"])
    return "main"


async def fetch_github_commit_sha(client: httpx.AsyncClient, repo: str, logger: logging.Logger) -> Optional[str]:
    url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
    data = await _github_api_get(client, url, logger)
    if isinstance(data, list) and data:
        return data[0].get("sha")
    return None


def _is_skippable_data_name(name: str) -> bool:
    lower = name.lower()
    if lower.startswith("_"):
        return True
    return any(s in lower for s in _GITHUB_SKIP_NAME_SUBSTR)


async def discover_repo_data_files(
    client: httpx.AsyncClient,
    repo: str,
    branch: str,
    logger: logging.Logger,
    max_entries: int = 200,
) -> List[Dict[str, Any]]:
    """用 Contents API 递归列出仓库内 json/jsonl 数据文件（含 download_url）。"""
    found: List[Dict[str, Any]] = []
    queue: List[str] = [""]
    seen_dirs: Set[str] = set()

    while queue and len(found) < max_entries:
        rel = queue.pop(0)
        if rel in seen_dirs:
            continue
        seen_dirs.add(rel)
        api = f"https://api.github.com/repos/{repo}/contents"
        if rel:
            api = f"{api}/{rel}"
        api = f"{api}?ref={branch}"
        data = await _github_api_get(client, api, logger)
        if data is None:
            continue
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or ""
            path = item.get("path") or name
            typ = item.get("type")
            if typ == "dir":
                base = name.lower()
                if base in _GITHUB_SKIP_DIRS or name.startswith("."):
                    continue
                queue.append(path)
                continue
            if typ != "file":
                continue
            lower = name.lower()
            if not (lower.endswith(".json") or lower.endswith(".jsonl")):
                continue
            if _is_skippable_data_name(name):
                continue
            download_url = item.get("download_url")
            if not download_url:
                download_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
            found.append({
                "name": name,
                "path": path,
                "download_url": download_url,
                "size": item.get("size") or 0,
            })
    logger.info("%s@%s 发现数据文件 %s 个: %s", repo, branch, len(found), [f["path"] for f in found])
    return found


def resolve_file_download_urls(
    file_spec: Dict[str, Any],
    discovered: List[Dict[str, Any]],
    repo: str,
    branch: str,
) -> List[str]:
    """按 match_names / remote_paths 优先，拼出下载 URL 列表（含 gh-proxy）。"""
    match_names = [n.lower() for n in (file_spec.get("match_names") or [file_spec["local"]])]
    remote_paths: List[str] = list(file_spec.get("remote_paths") or [])
    urls: List[str] = []

    # 1) API 发现：按 match_names 顺序精确匹配 basename
    for want in match_names:
        candidates = [d for d in discovered if (d.get("name") or "").lower() == want]
        # 优先 data/、datasets/ 下的路径
        candidates.sort(
            key=lambda d: (
                0 if str(d.get("path", "")).startswith(("data/", "datasets/")) else 1,
                -int(d.get("size") or 0),
            )
        )
        for d in candidates:
            u = d.get("download_url")
            if u and u not in urls:
                urls.append(u)

    # 2) 静态候选路径 + 当前默认分支（再兜底 main/master）
    branches = []
    for b in (branch, "main", "master"):
        if b and b not in branches:
            branches.append(b)
    for path in remote_paths:
        for b in branches:
            raw = f"https://raw.githubusercontent.com/{repo}/{b}/{path}"
            if raw not in urls:
                urls.append(raw)

    # 3) 镜像
    mirrored: List[str] = []
    for u in urls:
        mirrored.append(u)
        if u.startswith("https://raw.githubusercontent.com/"):
            proxied = "https://gh-proxy.com/" + u
            if proxied not in mirrored:
                mirrored.append(proxied)
    return mirrored


async def download_open_file(
    client: httpx.AsyncClient,
    robots: RobotsCache,
    repo: str,
    remote_paths: List[str],
    dest: Path,
    logger: logging.Logger,
    page_budget: List[int],
    resolved_urls: Optional[List[str]] = None,
) -> bool:
    mirrors: List[str] = list(resolved_urls or [])
    if not mirrors:
        for path in remote_paths:
            for branch in ("main", "master"):
                raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                mirrors.append(raw)
                mirrors.append("https://gh-proxy.com/" + raw)

    fetcher = RateLimitedFetcher(client, robots, logger, page_budget)
    for url in mirrors:
        if should_stop_new_pages() or page_budget[0] >= MAX_PAGES_PER_SOURCE:
            return False
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
                    branch = await fetch_github_default_branch(client, repo, logger)
                    discovered = await discover_repo_data_files(client, repo, branch, logger)
                    if not discovered:
                        logger.warning(
                            "%s Contents API 未列出数据文件，回退静态 remote_paths（branch=%s）",
                            key, branch,
                        )
                    for f in spec["files"]:
                        dest = RAW_OPEN / f["local"]
                        urls = resolve_file_download_urls(f, discovered, repo, branch)
                        logger.info(
                            "%s/%s 候选下载 %s 个（优先 API）: %s",
                            key, f["local"], len(urls), urls[:4],
                        )
                        ok = await download_open_file(
                            client,
                            robots,
                            repo,
                            f["remote_paths"],
                            dest,
                            logger,
                            page_budget,
                            resolved_urls=urls,
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
                            "branch": branch,
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
