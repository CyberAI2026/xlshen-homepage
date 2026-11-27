"""Keep publication and project groups ordered by their recorded dates."""
from collections import defaultdict
from html import escape
import re

from build_facts import in_news_archive, load_records


SECTION_END = '</section>'
PAPER_LIST = re.compile(r'<li id="paper-([a-z0-9-]+)"[^>]*>.*?</li>', re.S)


def replace_section(source, section_id, render):
    start = source.index(f'<section class="block" id="{section_id}">')
    end = source.index(SECTION_END, start)
    return source[:start] + render(source[start:end]) + source[end:]


def group_records(entries, *, heading_id, list_class):
    years = defaultdict(list)
    for date, entry in sorted(entries, key=lambda pair: pair[0], reverse=True):
        years[date[:4]].append(entry)
    for year, items in years.items():
        attrs = f' id="{heading_id}{year}"' if heading_id else ''
        yield f'<h3 class="record-year"{attrs}>{year} 年</h3>'
        yield f'<ul class="{list_class}">\n' + '\n'.join(items) + '\n</ul>\n'


def build_research(site):
    by_id = {row['id']: row for row in load_records(site)}
    path = site / 'research.html'
    source = path.read_text(encoding='utf-8')

    def publications(section):
        groups = []
        for paper in PAPER_LIST.finditer(section):
            rid = paper[1]
            row = by_id.get(rid)
            if not row or not row['date']:
                raise ValueError(f'Missing publication date: {rid}')
            entry = paper[0]
            if not in_news_archive(row):
                entry = re.sub(r'\s*<a\b[^>]*href="news\.html#[^"]+"[^>]*>[^<]*</a>', '', entry)
            groups.append((row['date'], entry))
        if not groups or len(groups) != section.count('<li id="paper-'):
            raise ValueError('Could not read the research publication list')
        years = sorted({date[:4] for date, _ in groups}, reverse=True)
        nav = ''.join(f'<a href="#pub-{year}">{year}</a>' for year in years)
        head = section.split('<nav class="year-links"', 1)[0]
        return (head + f'<nav class="year-links" aria-label="按年份跳转">{nav}</nav>\n'
                + '\n'.join(group_records(groups, heading_id='pub-', list_class='publication-list')))

    def projects(section):
        groups = []
        for row in by_id.values():
            if row['category'] != 'research' or row['subcategory'] != '研究项目':
                continue
            rid = row['id']
            title = escape(row['title'])
            detail = escape(row['detail'])
            entry = (f'<li id="project-{rid}"><a class="award-title" href="facts.html#record-{rid}">{title}</a>'
                     f'<p>{detail}</p></li>')
            groups.append((row['date'], entry))
        return (section.split('</h2>', 1)[0] + '</h2>\n'
                + '\n'.join(group_records(groups, heading_id='project-year-', list_class='records sourced')))

    source = replace_section(source, 'papers', publications)
    source = replace_section(source, 'academic-records', projects)
    path.write_text(source, encoding='utf-8')
