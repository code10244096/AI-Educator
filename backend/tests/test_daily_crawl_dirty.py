"""daily_crawl 入库脏数据过滤：公告/网页残留拦截。"""
from crawler.daily_crawl import SourceStats, filter_new_rows, looks_like_dirty_row


# 线上真实脏样例（已手工删除的同类文本）
DIRTY_HTM = (
    "7006319. htm下文是2024年北京高考各科试卷及答案解析："
    "请考生结合自身情况合理安排复习。"
)
DIRTY_ADVICE = (
    "1. 平稳心态，积极面对：高考结束并不意味着一切结束，"
    "要以平常心对待成绩公布。"
)
DIRTY_ADVICE_2 = "3. 合理利用考后时间：可适当放松，同时关注志愿填报信息。"
DIRTY_ADVICE_3 = "5. 家庭沟通，共商未来：与父母充分交流，共同规划下一步。"
DIRTY_NAV = "下一页 本文来源：新东方在线 / 无忧考网 gkxx 点击进入 www.example.com"


def _row(text: str, **extra) -> dict:
    data = {
        "question_text": text,
        "answer": "",
        "solution": "",
        "question_type": "选择题",
        "subject": "数学",
        "education_level": "高中",
        "source_url": extra.pop("source_url", f"https://example.test/{hash(text) & 0xFFFF}"),
    }
    data.update(extra)
    return data


def test_dirty_htm_residue_blocked():
    assert looks_like_dirty_row(_row(DIRTY_HTM)) is True


def test_dirty_advice_blocked():
    assert looks_like_dirty_row(_row(DIRTY_ADVICE)) is True
    assert looks_like_dirty_row(_row(DIRTY_ADVICE_2)) is True
    assert looks_like_dirty_row(_row(DIRTY_ADVICE_3)) is True


def test_dirty_nav_source_blocked():
    assert looks_like_dirty_row(_row(DIRTY_NAV)) is True
    assert looks_like_dirty_row(_row("本文整理自网络，上一页继续阅读")) is True


def test_clean_choice_with_http_not_blocked():
    text = (
        "某研究引用了 http://example.com 参考网站 上的数据，下列说法正确的是\n"
        "A. 样本具有代表性\n"
        "B. 样本不具有代表性\n"
        "C. 无法判断\n"
        "D. 以上都不对"
    )
    assert looks_like_dirty_row(_row(text)) is False


def test_clean_application_with_kaohou_not_blocked():
    text = (
        "考后某同学复习函数，已知 $$f(x)=x^2$$，则 f(2) 等于多少？"
    )
    assert looks_like_dirty_row(_row(text)) is False


def test_clean_choice_with_advice_keyword_not_blocked():
    """含建议语气关键词但带选项 → 不误拦。"""
    text = (
        "关于考试后如何平稳心态，下列做法正确的是\n"
        "A. 适度放松\n"
        "B. 彻夜刷题\n"
        "C. 忽略成绩\n"
        "D. 放弃志愿"
    )
    assert looks_like_dirty_row(_row(text)) is False


def test_filter_new_rows_drops_dirty_and_counts():
    clean = _row(
        "已知函数 f(x)=x+1，则 f(1)=（　）\nA. 1\nB. 2\nC. 3\nD. 4",
        source_url="https://example.test/clean-1",
    )
    dirty_rows = [
        _row(DIRTY_HTM, source_url="https://example.test/dirty-htm"),
        _row(DIRTY_ADVICE, source_url="https://example.test/dirty-advice"),
        _row(DIRTY_NAV, source_url="https://example.test/dirty-nav"),
    ]
    stats = SourceStats()
    fresh = filter_new_rows(
        dirty_rows + [clean],
        existing_urls=set(),
        existing_hashes=set(),
        night_new_total=0,
        stats=stats,
    )
    assert len(fresh) == 1
    assert fresh[0]["source_url"] == "https://example.test/clean-1"
    assert stats.dirty == 3
    assert stats.dup == 0

DIRTY_ADVICE_4 = "2. 科学规划后续复习：若仍在高考期间，数学考试后应迅速调整状态。"
DIRTY_ADVICE_5 = "6. 关注官方信息，确保无误：紧盯教育招生考试院发布的官方通知。"


def test_dirty_advice_remaining_variants_blocked():
    assert looks_like_dirty_row(_row(DIRTY_ADVICE_4)) is True
    assert looks_like_dirty_row(_row(DIRTY_ADVICE_5)) is True
