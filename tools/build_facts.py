"""Render the public archive from its reviewed JSON records."""
from html import escape
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit


CATEGORIES = {
    "teaching": ("教学", "课程、教学成果与学生学科竞赛"),
    "research": ("科研", "论文、科研项目与学术影响"),
    "service": ("社会服务", "期刊建设、学术组织与对外讲座"),
}
FIELDS = {"id", "category", "subcategory", "title", "date", "date_label", "role", "detail", "sources"}
SITE = Path(__file__).resolve().parents[1] / "site"


def safe_link(url, site):
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 for c in url) or "\\" in url:
        return False
    try:
        parts = urlsplit(url)
        if parts.scheme in {"https", "http"}:
            return bool(parts.hostname) and parts.username is None and parts.password is None
    except ValueError:
        return False
    path = PurePosixPath(parts.path)
    return (not parts.scheme and not parts.netloc and not path.is_absolute()
            and ".." not in path.parts and "\\" not in url and (site / path).is_file())


def load_records(site):
    records = json.loads((site / "assets/records.json").read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("records.json must contain public records")
    seen = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("Only reviewed public record fields are allowed")
        rid = row["id"]
        if (not isinstance(rid, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,100}", rid)
                or rid in seen or row["category"] not in CATEGORIES):
            raise ValueError(f"Invalid or duplicate public record ID or category: {rid}")
        seen.add(rid)
        if not all(isinstance(row[key], str) and row[key].strip()
                   for key in ("title", "subcategory", "detail")) or not isinstance(row["role"], str):
            raise ValueError(f"Missing public record text: {rid}")
        if row["date"] is not None and not isinstance(row["date"], str):
            raise ValueError(f"Invalid date: {rid}")
        if row["date_label"] is not None and not isinstance(row["date_label"], str):
            raise ValueError(f"Invalid date label: {rid}")
        if not isinstance(row["sources"], list):
            raise ValueError(f"Invalid sources: {rid}")
        for src in row["sources"]:
            if (not isinstance(src, dict) or not {"label", "url"} <= set(src) <= {"label", "url", "note", "show_note"}
                    or not isinstance(src["label"], str) or not src["label"].strip()
                    or ("show_note" in src and ("note" not in src or not isinstance(src["show_note"], bool)))
                    or ("note" in src and (not isinstance(src["note"], str) or not src["note"].strip()))
                    or not safe_link(src["url"], site)):
                raise ValueError(f"Invalid evidence link: {rid}")
    return records


def record_html(row):
    tag = escape(row["subcategory"])
    date_label = escape(row["date_label"] or row["date"] or "日期未载")
    sources = []
    for src in row["sources"]:
        label = escape(src["label"])
        url = src["url"]
        external = urlsplit(url).scheme in {"http", "https"}
        if external or PurePosixPath(url).suffix.lower() in {".webp", ".jpg", ".jpeg"}:
            action = ' target="_blank" rel="noopener"'
        elif PurePosixPath(url).suffix.lower() in {".pdf", ".zip", ".png"}:
            action = " download"
        else:
            action = ""
        note = escape(src.get("note", ""), quote=True)
        tooltip = f' title="{note}"' if note else ""
        if external:
            address = escape(url, quote=True)
            sources.append(f'<a class="external-source" href="{address}"{action}{tooltip}>'
                           f'<span class="source-name">{label}</span><bdi class="source-url" dir="ltr">{address}</bdi></a>')
        else:
            sources.append(f'<a href="{escape(url, quote=True)}"{action}{tooltip}>{label}</a>')
        if src.get("show_note"):
            sources.append(f'<small class="citation-note">{note}</small>')
    links = " ".join(sources)
    role = f'\n        <p class="fact-role"><span>角色</span>　{escape(row["role"])}</p>' if row["role"] else ""
    year = escape(row["date"][:4]) if row["date"] else "current"
    rid = row["id"]
    source_block = f'<div class="fact-sources"><span>来源</span>　{links}</div>' if links else ""
    actions = (f'\n        <div class="fact-actions">{source_block}'
               f'<a class="source" href="news.html#{rid}">查看新闻动态</a></div>')
    return f"""
    <li class="fact" id="record-{rid}" data-category="{row['category']}" data-year="{year}">
      <div class="fact-meta"><span class="fact-date">{date_label}</span><span class="fact-tag">{tag}</span></div>
      <div class="fact-main">
        <h3 class="fact-title">{escape(row['title'])}</h3>{role}
        <p class="fact-detail">{escape(row['detail'])}</p>{actions}
      </div>
    </li>"""


def build_facts(site=SITE):
    records = load_records(site)
    years = sorted({row["date"][:4] for row in records if row["date"]}, reverse=True)
    options = ['<option value="all">全部年份</option>']
    options.extend(f'<option value="{escape(year)}">{escape(year)} 年</option>' for year in years)
    if any(not row["date"] for row in records):
        options.append('<option value="current">未列年份</option>')
    groups = []
    filters = ['<button class="topic-filter" type="button" data-filter="all" aria-pressed="true">全部</button>']
    for code, (label, _) in CATEGORIES.items():
        members = sorted((r for r in records if r["category"] == code),
                         key=lambda r: r["date"] or "", reverse=True)
        if not members:
            continue
        filters.append(f'<button class="topic-filter" type="button" data-filter="{code}" aria-pressed="false">{label}</button>')
        items = "".join(record_html(item) for item in members)
        groups.append(f'<section class="fact-group" id="{code}" aria-labelledby="group-{code}">'
                      f'<h2 id="group-{code}">{label}</h2><ul class="fact-list">{items}</ul></section>')
    # Reuse the site's navigation and footer so shared links stay in sync.
    template = (site / "news.html").read_text(encoding="utf-8")
    head, rest = template.split('<main id="main">', 1)
    _, footer = rest.split("</main>", 1)
    head = head.replace("<title>新闻动态｜", "<title>成果与活动｜")
    head = head.replace('href="news.html" aria-current="page"', 'href="news.html"')
    head = head.replace('class="nav-link" href="facts.html"', 'class="nav-link" href="facts.html" aria-current="page"')
    body = f"""<main id="main"><div class="wrap inner archive">
      <h1>成果与活动</h1>
      <p class="lead">查阅教学、科研与社会服务记录，可按年份、类别或关键词筛选。</p>
      <div class="archive-tools" data-archive-controls hidden>
        <div class="filter-row"><div class="filter-options" role="group" aria-label="按类别筛选">{''.join(filters)}</div>
          <label class="record-search"><span>检索记录</span><input type="search" id="archive-search" placeholder="名称、年份或关键词" autocomplete="off"></label>
          <label class="archive-year">年份　<select data-year-filter aria-label="按年份筛选">{''.join(options)}</select></label>
        </div>
        <p class="results-status" role="status" aria-live="polite"></p>
      </div>
      <noscript><div class="archive-jumps"><a href="#teaching">教学</a> · <a href="#research">科研</a> · <a href="#service">社会服务</a></div></noscript>
      <p class="no-results" hidden>没有符合条件的记录。<button type="button" class="reset-filters">显示全部记录</button></p>
      {''.join(groups)}
    </div></main>"""
    output = head + body + footer.replace('data-news-page', '')
    (site / "facts.html").write_text(output, encoding="utf-8")


if __name__ == "__main__":
    build_facts()
