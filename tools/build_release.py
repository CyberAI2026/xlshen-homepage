#!/usr/bin/env python3
"""Build the public homepage release. Requires Python 3.8 or newer."""
import hashlib
from html import unescape
import io
import json
from pathlib import Path
import re
import stat
import zipfile

from build_facts import build_facts, load_records


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'about.html', 'course-lab.html', 'honors.html', 'index.html',
    'information-reception-lab.html',
    'news.html', 'facts.html', 'research.html', 'service.html', 'teaching.html',
}
LAB = re.compile(r'(?:Information_Reception_Lab_V\d+(?:_\d+)*\.html|Reception_Lab_V\d+(?:_\d+)*_Student\.zip)\Z')
PART_BYTES = 8 * 1024**2
ASSET_TYPES = {'.css', '.js', '.json', '.txt', '.xml', '.pdf', '.zip', '.png', '.jpg',
               '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.csv'}
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z')
PAPER_TYPES = {'学术论文', '期刊录用', '期刊导言', '会议论文', '会议报告', '会议海报'}


def archive_entries(path):
    source = path.read_text(encoding='utf-8')
    matches = re.findall(r'<li\s+id="([a-z0-9-]+)"[^>]*>(.*?)</li>', source, re.S)
    entries = dict(matches)
    if len(entries) != len(matches):
        raise ValueError(f'Duplicate archive entries in {path.name}')
    return entries


def validate_archive(site):
    records = load_records(site)
    news = archive_entries(site / 'news.html')
    missing_news = {row['id'] for row in records} - news.keys()
    if missing_news:
        raise ValueError('Records missing from News: ' + ', '.join(sorted(missing_news)))

    papers = archive_entries(site / 'research.html')
    for row in records:
        if row['category'] != 'research' or row['subcategory'] not in PAPER_TYPES:
            continue
        rid = row['id']
        paper_id = f'paper-{rid}'
        if paper_id not in papers or f'href="research.html#{paper_id}"' not in news[rid]:
            raise ValueError(f'Link the research paper and its news entry: {rid}')
        headline = re.search(r'class="entry-title"[^>]*>([^<]+)</a>', news[rid])
        if not headline or row['title'] not in unescape(headline.group(1)):
            raise ValueError(f'Include the full paper title in its news headline: {rid}')
        if row['subcategory'] == '期刊录用':
            citations = re.findall(r'《([^》]+)》', row['title'])
            paper = unescape(papers[paper_id])
            if len(citations) < 2 or '录用' not in row['title'] or '已录用' not in paper:
                raise ValueError(f'Use the paper title, journal, and acceptance status in both entries: {rid}')
            if not all(citation in paper for citation in citations[:2]):
                raise ValueError(f'The research entry must identify the accepted paper and journal: {rid}')


def public_files(site):
    if site.is_symlink() or not site.is_dir():
        raise ValueError('site/ must be a directory, not a symlink')
    files = {}
    for path in sorted(site.rglob('*')):
        relative = path.relative_to(site)
        if path.is_symlink():
            raise ValueError('Refusing symlink: %s' % relative)
        if path.is_dir() or any(not NAME.fullmatch(part) for part in relative.parts):
            continue
        name = relative.as_posix()
        asset = relative.parts[0] == 'assets' and path.suffix.lower() in ASSET_TYPES
        if name not in PAGES and not LAB.fullmatch(name) and not asset:
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError('Expected a regular file: %s' % name)
        files[name] = path
    missing = (PAGES | {'assets/site.css'}) - set(files)
    if missing:
        raise ValueError('Missing required files: ' + ', '.join(sorted(missing)))
    return files


def build():
    validate_archive(ROOT / 'site')
    build_facts(ROOT / 'site')
    files = public_files(ROOT / 'site')
    version_page_assets(files)
    sizes = [path.stat().st_size for path in files.values()]
    if len(files) > 512 or max(sizes) > 12 * 1024**2 or sum(sizes) > 128 * 1024**2:
        raise ValueError("Public files exceed the server file count, individual size or expanded size limit")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, files[name].read_bytes(), zipfile.ZIP_DEFLATED, compresslevel=9)
    package = buf.getvalue()
    if len(package) > 64 * 1024**2:
        raise ValueError("Release ZIP exceeds the 64 MiB server limit")
    digest = hashlib.sha256(package).hexdigest()
    part_dir = ROOT / 'release-parts'
    part_dir.mkdir(exist_ok=True)
    digests = []
    expected = set()
    for offset in range(0, len(package), PART_BYTES):
        part = package[offset:offset + PART_BYTES]
        name = 'site.zip.part%02d' % (len(digests) + 1)
        expected.add(name)
        (part_dir / name).write_bytes(part)
        digests.append(hashlib.sha256(part).hexdigest())
    for old in part_dir.glob('site.zip.part[0-9][0-9]'):
        if old.name not in expected:
            old.unlink()
    manifest = json.dumps({'file': 'site.zip.parts', 'size': len(package),
                           'sha256': digest, 'parts': digests}, indent=2) + '\n'
    (ROOT / 'site.zip').write_bytes(package)
    (ROOT / 'release.json').write_bytes(manifest.encode('ascii'))
    print('%d files, ZIP SHA-256 %s' % (len(files), digest))


def version_page_assets(files):
    """Refresh browser cache keys for shared code and public certificates."""
    versioned = ['assets/site.css', 'assets/archive.js']
    versioned.extend(name for name in files
                     if Path(name).parent.as_posix() == 'assets'
                     and Path(name).suffix.lower() in {'.pdf', '.png', '.webp'})
    versions = {name: hashlib.sha256(files[name].read_bytes()).hexdigest()[:12]
                for name in versioned}
    asset_urls = re.compile(
        r'(?P<attr>\b(?:href|src)=)(?P<quote>["\'])(?P<path>' +
        '|'.join(re.escape(name) for name in sorted(versions)) + ')'
        r'(?:\?v=[a-zA-Z0-9_-]+)?(?P=quote)'
    )

    def with_version(match):
        path = match['path']
        quote = match['quote']
        return f"{match['attr']}{quote}{path}?v={versions[path]}{quote}"

    for name in sorted(PAGES):
        page = files[name]
        source = page.read_text(encoding='utf-8')
        updated = asset_urls.sub(with_version, source)
        if updated != source:
            page.write_text(updated, encoding='utf-8')


if __name__ == '__main__':
    build()
