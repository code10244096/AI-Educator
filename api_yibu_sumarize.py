# -*- coding: utf-8 -*-
# 功能说明：
# 统计 api_runs/ 下后端 LLM 网关写入的调用日志，输出命令行表格、CSV、JSON 和 HTML dashboard。
#
# 聚合逻辑统一放在 backend/usage_stats.py，本脚本只负责参数解析与输出渲染：
#   - 自动跳过 run_summary 行，不读取 responses.jsonl（避免重复统计）；
#   - 支持 --since / --until / --feature / --source 过滤；
#   - HTML：总览 KPI、Token 构成、按功能、按来源、按模型、按 Key、按日期、Key+Model 明细。
#
# 用法：
#   python api_yibu_sumarize.py --root api_runs
#   python api_yibu_sumarize.py --since 2026-09-01 --feature grade,ocr --source backend

import argparse
import csv
import html
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import usage_stats  # noqa: E402
from usage_stats import safe_float, safe_int  # noqa: E402


FEATURE_LABELS = {
    "ocr": "OCR 识别",
    "grade": "作业批改",
    "lessonplan": "教案生成",
    "variant": "变式题",
    "seed_grade": "种子批改",
    "other": "其他",
    "unknown": "未标注",
}

SOURCE_LABELS = {
    "backend": "后端服务",
    "cli": "命令行脚本",
}


# =========================
# 1) 基础工具
# =========================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def now_for_filename() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def fmt_int(value: Any) -> str:
    return f"{safe_int(value):,}"


def fmt_float(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value):,.{digits}f}"


def pct(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value):.{digits}f}%"


def esc(value: Any) -> str:
    return html.escape(str(value))


# =========================
# 2) 命令行 / CSV / JSON
# =========================

METRIC_COLUMNS = [
    "calls",
    "unique_call_ids",
    "duplicate_call_id_count",
    "success",
    "failed",
    "success_rate",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "avg_total_tokens_per_call",
    "avg_prompt_tokens_per_call",
    "avg_completion_tokens_per_call",
    "elapsed_seconds",
    "avg_elapsed_seconds",
    "median_elapsed_seconds",
    "run_count",
    "task_count",
    "log_file_count",
    "first_ts",
    "last_ts",
]

CSV_COLUMNS = ["group", "name", "key_suffix", "model"] + METRIC_COLUMNS + ["log_files"]

# (summary 中的 section, 分组字段, 显示名)
GROUP_SPECS = [
    ("by_feature", "feature", "按功能 (feature)"),
    ("by_source", "source", "按来源 (source)"),
    ("by_model", "model", "按模型 (model)"),
    ("by_key", "key_suffix", "按 Key"),
    ("by_day", "day", "按日期 (本地时区)"),
]


def flatten_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把 summarize() 的结构展平为 CSV 行。"""
    rows: List[Dict[str, Any]] = []
    overview = dict(summary.get("overview") or {})
    overview.update({"group": "overview", "name": "ALL", "key_suffix": "ALL_KEYS", "model": "ALL_MODELS"})
    rows.append(overview)

    for section, field, _ in GROUP_SPECS:
        for item in summary.get(section, []):
            row = dict(item)
            row["group"] = section
            row["name"] = item.get(field, "")
            row.setdefault("key_suffix", "ALL_KEYS" if field != "key_suffix" else item.get(field))
            row.setdefault("model", "ALL_MODELS" if field != "model" else item.get(field))
            rows.append(row)

    for item in summary.get("key_model", []):
        row = dict(item)
        row["group"] = "key_model"
        row["name"] = f"{item.get('key_suffix')}/{item.get('model')}"
        rows.append(row)
    return rows


def print_table(title: str, items: List[Dict[str, Any]], name_col: str) -> None:
    print(f"\n[{title}]")
    if not items:
        print("  暂无数据。")
        return

    columns = [
        name_col,
        "calls",
        "success",
        "failed",
        "success_rate",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "avg_total_tokens_per_call",
        "avg_elapsed_seconds",
        "run_count",
    ]
    widths = {col: max(len(col), max(len(str(item.get(col, ""))) for item in items)) for col in columns}
    print(" | ".join(col.ljust(widths[col]) for col in columns))
    print("-+-".join("-" * widths[col] for col in columns))
    for item in items:
        print(" | ".join(str(item.get(col, "")).ljust(widths[col]) for col in columns))


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


def write_json(path: str, summary: Dict[str, Any], meta: Dict[str, Any]) -> None:
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "summary": summary}, f, ensure_ascii=False, indent=2)


# =========================
# 3) HTML
# =========================

STYLE = """    :root {
      --bg: #f6f7fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --soft: #f3f4f6;
      --blue: #2563eb;
      --green: #16a34a;
      --amber: #d97706;
      --red: #dc2626;
      --purple: #7c3aed;
      --cyan: #0891b2;
      --shadow: 0 10px 30px rgba(17, 24, 39, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", "Microsoft YaHei", sans-serif;
    }

    .page {
      max-width: 1440px;
      margin: 0 auto;
      padding: 28px;
    }

    .hero {
      background: linear-gradient(135deg, #111827 0%, #1e3a8a 50%, #312e81 100%);
      color: #fff;
      border-radius: 22px;
      padding: 28px;
      box-shadow: var(--shadow);
      margin-bottom: 22px;
    }

    .hero-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0 0 8px 0;
      font-size: 30px;
      letter-spacing: -0.02em;
    }

    .subtitle {
      color: rgba(255,255,255,0.72);
      line-height: 1.6;
      font-size: 14px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.12);
      color: rgba(255,255,255,0.92);
      font-size: 13px;
      white-space: nowrap;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 14px;
    }

    .kpi {
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 18px;
      padding: 18px;
      backdrop-filter: blur(8px);
    }

    .kpi-label {
      color: rgba(255,255,255,0.70);
      font-size: 13px;
      margin-bottom: 8px;
    }

    .kpi-value {
      font-size: 30px;
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.02em;
    }

    .kpi-note {
      color: rgba(255,255,255,0.68);
      font-size: 12px;
      margin-top: 7px;
    }

    .section {
      margin-top: 22px;
    }

    .section-title {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin: 0 0 12px 0;
    }

    .section-title h2 {
      margin: 0;
      font-size: 20px;
      letter-spacing: -0.01em;
    }

    .section-hint {
      color: var(--muted);
      font-size: 13px;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(260px, 1fr));
      gap: 16px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: var(--shadow);
    }

    .model-card {
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-height: 250px;
    }

    .model-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }

    .model-name {
      font-size: 18px;
      font-weight: 800;
      word-break: break-word;
    }

    .share-pill {
      border-radius: 999px;
      background: #eff6ff;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 700;
      padding: 6px 10px;
      white-space: nowrap;
    }

    .big-token {
      font-size: 34px;
      font-weight: 850;
      letter-spacing: -0.03em;
      margin-top: 2px;
    }

    .token-caption {
      color: var(--muted);
      font-size: 13px;
      margin-top: 2px;
    }

    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 4px;
    }

    .mini-metric {
      background: var(--soft);
      border-radius: 14px;
      padding: 10px 12px;
    }

    .mini-label {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }

    .mini-value {
      font-weight: 800;
      font-size: 16px;
    }

    .token-stack {
      display: flex;
      overflow: hidden;
      height: 12px;
      border-radius: 999px;
      background: #e5e7eb;
      margin: 6px 0 8px;
    }

    .seg.prompt { background: var(--blue); }
    .seg.completion { background: var(--green); }
    .seg.reasoning { background: var(--purple); }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 999px;
      margin-right: 5px;
    }

    .dot.prompt { background: var(--blue); }
    .dot.completion { background: var(--green); }
    .dot.reasoning { background: var(--purple); }

    .key-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 14px;
    }

    .key-card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 15px;
      box-shadow: var(--shadow);
    }

    .key-name {
      font-weight: 800;
      font-size: 15px;
      margin-bottom: 8px;
    }

    .key-token {
      font-size: 24px;
      font-weight: 850;
      letter-spacing: -0.02em;
    }

    .progress-wrap {
      height: 10px;
      background: #e5e7eb;
      border-radius: 999px;
      overflow: hidden;
      margin: 10px 0 8px;
    }

    .progress {
      height: 100%;
      background: linear-gradient(90deg, var(--cyan), var(--blue));
      border-radius: 999px;
    }

    .table-card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 0;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .table-scroll {
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      min-width: 1100px;
    }

    th, td {
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: right;
      white-space: nowrap;
    }

    th {
      background: #f9fafb;
      color: #374151;
      position: sticky;
      top: 0;
      z-index: 1;
      font-size: 12px;
      text-transform: none;
    }

    td:first-child, th:first-child,
    td:nth-child(2), th:nth-child(2) {
      text-align: left;
    }

    tr:hover td {
      background: #f9fafb;
    }

    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
    }

    .ok { color: var(--green); font-weight: 700; }
    .bad { color: var(--red); font-weight: 700; }

    .footer {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.7;
      margin: 22px 0 4px;
    }

    @media (max-width: 1100px) {
      .kpi-grid { grid-template-columns: repeat(2, minmax(160px, 1fr)); }
      .cards { grid-template-columns: repeat(2, minmax(260px, 1fr)); }
      .key-grid { grid-template-columns: repeat(2, minmax(180px, 1fr)); }
    }

    @media (max-width: 720px) {
      .page { padding: 16px; }
      .hero-top { flex-direction: column; }
      .kpi-grid, .cards, .key-grid { grid-template-columns: 1fr; }
      .kpi-value { font-size: 26px; }
      .big-token { font-size: 28px; }
    }
    .feature-label { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .bar-cell { min-width: 180px; }
    .bar-cell .progress-wrap { margin: 4px 0; }
    .compact table { min-width: 900px; }
"""


def token_share_width(value: Any, total: Any) -> str:
    total_int = safe_int(total)
    value_int = safe_int(value)
    if total_int <= 0:
        return "0%"
    return f"{max(0.5, min(100.0, value_int / total_int * 100)):.2f}%"


def small_metric(label: str, value: str) -> str:
    return f"""
    <div class="mini-metric">
      <div class="mini-label">{esc(label)}</div>
      <div class="mini-value">{esc(value)}</div>
    </div>
    """


def render_token_bar(item: Dict[str, Any]) -> str:
    total = safe_int(item.get("total_tokens"))
    prompt = safe_int(item.get("prompt_tokens"))
    completion = safe_int(item.get("completion_tokens"))
    reasoning = safe_int(item.get("reasoning_tokens"))
    # reasoning 通常是 completion 的子项，这里仅作直观占比展示，不做严格会计口径。
    return f"""
    <div class="token-stack" title="prompt={prompt}, completion={completion}, reasoning={reasoning}">
      <div class="seg prompt" style="width:{token_share_width(prompt, total)}"></div>
      <div class="seg completion" style="width:{token_share_width(completion, total)}"></div>
      <div class="seg reasoning" style="width:{token_share_width(reasoning, total)}"></div>
    </div>
    <div class="legend">
      <span><i class="dot prompt"></i>Prompt {fmt_int(prompt)}</span>
      <span><i class="dot completion"></i>Completion {fmt_int(completion)}</span>
      <span><i class="dot reasoning"></i>Reasoning {fmt_int(reasoning)}</span>
    </div>
    """


def section(title: str, hint: str, body: str) -> str:
    return f"""
    <section class="section">
      <div class="section-title">
        <h2>{esc(title)}</h2>
        <div class="section-hint">{esc(hint)}</div>
      </div>
      {body}
    </section>
    """


def render_group_table(items: List[Dict[str, Any]], name_col: str, name_title: str,
                       total_tokens: int, labels: Dict[str, str] = None) -> str:
    """通用分组表：名称 + token 占比条 + 主要指标。"""
    labels = labels or {}
    rows = []
    for item in items:
        name = str(item.get(name_col, ""))
        share = safe_int(item.get("total_tokens")) / total_tokens * 100 if total_tokens else 0.0
        label_html = f'<div class="feature-label">{esc(labels[name])}</div>' if name in labels else ""
        failed = safe_int(item.get("failed"))
        rows.append(f"""
        <tr>
          <td class="mono">{esc(name)}{label_html}</td>
          <td class="bar-cell">
            <div class="progress-wrap"><div class="progress" style="width:{max(0.5, min(100.0, share)):.2f}%"></div></div>
            <div class="feature-label">{fmt_int(item.get("total_tokens"))} tokens · {share:.2f}%</div>
          </td>
          <td>{fmt_int(item.get("calls"))}</td>
          <td class="ok">{fmt_int(item.get("success"))}</td>
          <td class="{'bad' if failed else ''}">{fmt_int(failed)}</td>
          <td>{pct(item.get("success_rate"))}</td>
          <td>{fmt_int(item.get("prompt_tokens"))}</td>
          <td>{fmt_int(item.get("completion_tokens"))}</td>
          <td>{fmt_int(item.get("reasoning_tokens"))}</td>
          <td>{fmt_float(item.get("avg_total_tokens_per_call"))}</td>
          <td>{fmt_float(item.get("avg_elapsed_seconds"))}s</td>
          <td>{fmt_float(item.get("median_elapsed_seconds"))}s</td>
          <td>{fmt_int(item.get("task_count"))}</td>
        </tr>
        """)

    headers = [name_title, "Token 占比", "calls", "success", "failed", "success_rate",
               "prompt", "completion", "reasoning", "avg tokens/call", "avg elapsed",
               "median elapsed", "tasks"]
    body = "".join(rows) if rows else f'<tr><td colspan="{len(headers)}">暂无数据。</td></tr>'
    return f"""
    <div class="table-card compact">
      <div class="table-scroll">
        <table>
          <thead><tr>{''.join(f'<th>{esc(h)}</th>' for h in headers)}</tr></thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    </div>
    """


def write_html(path: str, summary: Dict[str, Any], meta: Dict[str, Any]) -> None:
    ensure_dir(os.path.dirname(os.path.abspath(path)))

    total_item = summary.get("overview") or {}
    total_tokens = safe_int(total_item.get("total_tokens"))

    filters = meta.get("filters") or {}
    filter_text = "，".join(f"{k}={v}" for k, v in filters.items() if v) or "无"

    hero = f"""
    <section class="hero">
      <div class="hero-top">
        <div>
          <h1>模型调用统计 Dashboard</h1>
          <div class="subtitle">
            统计时间：<span class="mono">{esc(meta.get("generated_at", ""))}</span><br>
            扫描根目录：<span class="mono">{esc(meta.get("root", ""))}</span><br>
            过滤条件：<span class="mono">{esc(filter_text)}</span>
          </div>
        </div>
        <div class="badge">日志文件 {fmt_int(total_item.get("log_file_count"))} 个 · Run {fmt_int(total_item.get("run_count"))} 个</div>
      </div>

      <div class="kpi-grid">
        <div class="kpi">
          <div class="kpi-label">总 Token</div>
          <div class="kpi-value">{fmt_int(total_tokens)}</div>
          <div class="kpi-note">Prompt + Completion，reasoning 另列</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">总调用次数</div>
          <div class="kpi-value">{fmt_int(total_item.get("calls"))}</div>
          <div class="kpi-note">成功 {fmt_int(total_item.get("success"))}，失败 {fmt_int(total_item.get("failed"))}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">成功率</div>
          <div class="kpi-value">{pct(total_item.get("success_rate"))}</div>
          <div class="kpi-note">按真实 API call 记录计算</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">平均耗时</div>
          <div class="kpi-value">{fmt_float(total_item.get("avg_elapsed_seconds"))}s</div>
          <div class="kpi-note">中位数 {fmt_float(total_item.get("median_elapsed_seconds"))}s</div>
        </div>
      </div>
    </section>
    """

    token_overview = section("总 Token 构成", "用于快速看这批调用主要消耗在哪里", f"""
      <div class="card">
        {render_token_bar(total_item)}
        <div class="mini-grid">
          {small_metric("Prompt Tokens", fmt_int(total_item.get("prompt_tokens")))}
          {small_metric("Completion Tokens", fmt_int(total_item.get("completion_tokens")))}
          {small_metric("Reasoning Tokens", fmt_int(total_item.get("reasoning_tokens")))}
          {small_metric("平均 Tokens/Call", fmt_float(total_item.get("avg_total_tokens_per_call")))}
        </div>
      </div>
    """)

    features_section = section(
        "按功能 (feature)", "后端各功能（OCR / 批改 / 教案 …）的消耗；旧 CLI 日志记为 unknown",
        render_group_table(summary.get("by_feature", []), "feature", "feature", total_tokens, FEATURE_LABELS),
    )
    sources_section = section(
        "按来源 (source)", "backend = 后端服务，cli = 命令行脚本（旧日志缺省为 cli）",
        render_group_table(summary.get("by_source", []), "source", "source", total_tokens, SOURCE_LABELS),
    )

    model_cards = []
    for item in summary.get("by_model", []):
        share = safe_int(item.get("total_tokens")) / total_tokens * 100 if total_tokens else 0.0
        model_cards.append(f"""
        <div class="card model-card">
          <div class="model-head">
            <div class="model-name mono">{esc(item.get("model", ""))}</div>
            <div class="share-pill">{share:.2f}%</div>
          </div>
          <div>
            <div class="big-token">{fmt_int(item.get("total_tokens"))}</div>
            <div class="token-caption">Total tokens</div>
          </div>
          {render_token_bar(item)}
          <div class="mini-grid">
            {small_metric("Calls", fmt_int(item.get("calls")))}
            {small_metric("Success Rate", pct(item.get("success_rate")))}
            {small_metric("Avg Tokens/Call", fmt_float(item.get("avg_total_tokens_per_call")))}
            {small_metric("Avg Elapsed", fmt_float(item.get("avg_elapsed_seconds")) + "s")}
            {small_metric("Runs", fmt_int(item.get("run_count")))}
            {small_metric("Log Files", fmt_int(item.get("log_file_count")))}
          </div>
        </div>
        """)
    models_section = section("按模型分块", "按 total_tokens 从高到低排序",
                             f'<div class="cards">{"".join(model_cards) or "<div class=card>暂无模型统计。</div>"}</div>')

    key_cards = []
    for item in summary.get("by_key", []):
        share = safe_int(item.get("total_tokens")) / total_tokens * 100 if total_tokens else 0.0
        key_cards.append(f"""
        <div class="key-card">
          <div class="key-name mono">key{esc(item.get("key_suffix", ""))}</div>
          <div class="key-token">{fmt_int(item.get("total_tokens"))}</div>
          <div class="token-caption">tokens · {share:.2f}% of total</div>
          <div class="progress-wrap"><div class="progress" style="width:{max(0.5, min(100.0, share)):.2f}%"></div></div>
          <div class="legend">
            <span>Calls {fmt_int(item.get("calls"))}</span>
            <span>Success {pct(item.get("success_rate"))}</span>
            <span>Runs {fmt_int(item.get("run_count"))}</span>
          </div>
        </div>
        """)
    keys_section = section("按 Key 汇总", "只显示 key 后四位，避免泄露完整 key",
                           f'<div class="key-grid">{"".join(key_cards) or "<div class=key-card>暂无 key 统计。</div>"}</div>')

    days_section = section(
        "按日期", "按本地日期汇总",
        render_group_table(summary.get("by_day", []), "day", "day", total_tokens),
    )

    table_columns = [
        "key_suffix", "model", "calls", "success", "failed", "success_rate", "total_tokens",
        "prompt_tokens", "completion_tokens", "reasoning_tokens", "avg_total_tokens_per_call",
        "avg_elapsed_seconds", "run_count", "log_file_count",
    ]
    int_cols = {"calls", "success", "failed", "total_tokens", "prompt_tokens", "completion_tokens",
                "reasoning_tokens", "run_count", "log_file_count"}
    table_rows = []
    for item in summary.get("key_model", []):
        cells = []
        for col in table_columns:
            val = item.get(col, "")
            if col == "success_rate":
                val = pct(val)
            elif col in int_cols:
                val = fmt_int(val)
            elif col in {"avg_total_tokens_per_call", "avg_elapsed_seconds"}:
                val = fmt_float(val)
            cls = "mono" if col in {"key_suffix", "model"} else ""
            if col == "success":
                cls = "ok"
            if col == "failed" and safe_int(item.get(col)) > 0:
                cls = "bad"
            cells.append(f"<td class='{cls}'>{esc(val)}</td>")
        table_rows.append("<tr>" + "".join(cells) + "</tr>")

    details_section = section("Key + Model 明细", "用于追查具体哪个 key 跑了哪个模型", f"""
      <div class="table-card">
        <div class="table-scroll">
          <table>
            <thead><tr>{''.join(f'<th>{esc(c)}</th>' for c in table_columns)}</tr></thead>
            <tbody>{''.join(table_rows) or f'<tr><td colspan="{len(table_columns)}">暂无明细。</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    """)

    footer = f"""
    <div class="footer">
      说明：HTML 仅用于展示，CSV 适合 Excel / pandas 二次处理，JSON 适合自动化读取。
      本报告只统计真实 API 调用记录，已跳过 run_summary 行，不读取 responses.jsonl。
      真实调用记录数：<span class="mono">{fmt_int(meta.get("real_call_records"))}</span>，
      跳过 summary 行：<span class="mono">{fmt_int(meta.get("skipped_summary_rows"))}</span>，
      跳过无效行：<span class="mono">{fmt_int(meta.get("skipped_invalid_rows"))}</span>。
    </div>
    """

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>模型调用统计 Dashboard</title>
<style>{STYLE}</style>
</head>
<body>
<div class="page">
  {hero}
  {token_overview}
  {features_section}
  {sources_section}
  {models_section}
  {keys_section}
  {days_section}
  {details_section}
  {footer}
</div>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)


# =========================
# 4) 入口
# =========================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="统计 api_runs 日志中的 token、调用次数、成功率等信息。")
    parser.add_argument("--root", default="", help="日志根目录 / 单个 run 目录 / 单个 api_calls.jsonl；默认 API_OUTPUT_ROOT 或 <repo>/api_runs。")
    parser.add_argument("--out-dir", default="", help="统计结果输出目录；默认 <root>/_summary。")
    parser.add_argument("--since", default=None, help="只统计此时间之后的调用（ISO，如 2026-09-01 或 2026-09-01T08:00:00+08:00；无时区按 UTC）。")
    parser.add_argument("--until", default=None, help="只统计此时间之前的调用（ISO）。")
    parser.add_argument("--feature", default=None, help="功能过滤，逗号分隔：ocr,grade,lessonplan,variant,seed_grade,other,unknown")
    parser.add_argument("--source", default=None, help="来源过滤，逗号分隔：backend,cli")
    parser.add_argument("--print-files", action="store_true", help="打印扫描到的日志文件。")
    parser.add_argument("--no-console-tables", action="store_true", help="不在命令行打印分组表格。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    root_abs = os.path.abspath(args.root) if args.root else usage_stats.default_log_root()
    out_dir = args.out_dir or os.path.join(root_abs if os.path.isdir(root_abs) else os.path.dirname(root_abs), "_summary")

    scan = usage_stats.scan_logs(root_abs)
    log_files = scan["log_files"]
    rows = usage_stats.filter_records(
        scan["records"], since=args.since, until=args.until, source=args.source, feature=args.feature,
    )

    print("=" * 100)
    print("模型调用日志统计")
    print("=" * 100)
    print(f"root: {root_abs}")
    print(f"log_file_count: {len(log_files)}")
    if args.print_files:
        print("\n扫描到的日志文件：")
        for path in log_files:
            print(f"  {path}")

    filters = {"since": args.since, "until": args.until, "feature": args.feature, "source": args.source}
    print(f"all_call_records: {len(scan['records'])}")
    print(f"filtered_call_records: {len(rows)}  (filters: {json.dumps({k: v for k, v in filters.items() if v}, ensure_ascii=False)})")
    print(f"skipped_summary_rows: {scan['skipped_summary_rows']}")
    print(f"skipped_invalid_rows: {scan['skipped_invalid_rows']}")

    if not rows:
        print("\n没有找到符合条件的 API 调用记录。")
        return 1

    summary = usage_stats.summarize(rows, include_log_files=True)
    ov = summary["overview"]
    print(f"\n总调用 {ov['calls']:,} · 成功率 {ov['success_rate']:.2f}% · 总 tokens {ov['total_tokens']:,} · 平均耗时 {ov['avg_elapsed_seconds']:.2f}s")

    if not args.no_console_tables:
        for sec, field, title in GROUP_SPECS:
            print_table(title, summary.get(sec, []), field)

    ensure_dir(out_dir)
    ts = now_for_filename()
    csv_path = os.path.join(out_dir, f"api_logs_summary_{ts}.csv")
    html_path = os.path.join(out_dir, f"api_logs_summary_{ts}.html")
    json_path = os.path.join(out_dir, f"api_logs_summary_{ts}.json")

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": root_abs,
        "filters": filters,
        "log_file_count": len(log_files),
        "real_call_records": len(rows),
        "all_call_records": len(scan["records"]),
        "skipped_summary_rows": scan["skipped_summary_rows"],
        "skipped_invalid_rows": scan["skipped_invalid_rows"],
        "out_dir": os.path.abspath(out_dir),
    }

    write_csv(csv_path, flatten_summary(summary))
    write_html(html_path, summary, meta)
    write_json(json_path, summary, meta)

    print("\n" + "=" * 100)
    print("统计文件已生成")
    print("=" * 100)
    print(f"csv : {csv_path}")
    print(f"html: {html_path}")
    print(f"json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
