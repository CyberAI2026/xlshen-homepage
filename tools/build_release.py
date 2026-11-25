#!/usr/bin/env python3
"""Build the public homepage release. Requires Python 3.8 or newer."""
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile

from build_facts import build_facts


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'about.html', 'course-lab.html', 'honors.html', 'index.html',
    'news.html', 'facts.html', 'research.html', 'service.html', 'teaching.html',
}
LAB = re.compile(r'(?:Information_Reception_Lab_V\d+(?:_\d+)*\.html|Reception_Lab_V\d+(?:_\d+)*_Student\.zip)\Z')
ASSET_TYPES = {'.css', '.js', '.json', '.txt', '.xml', '.pdf', '.zip', '.png', '.jpg',
               '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.csv'}
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z')


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
    build_facts(ROOT / 'site')
    files = public_files(ROOT / 'site')
    version_page_assets(files)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, files[name].read_bytes(), zipfile.ZIP_DEFLATED, compresslevel=9)
    package = buf.getvalue()
    digest = hashlib.sha256(package).hexdigest()
    manifest = json.dumps({'file': 'site.zip', 'sha256': digest}, indent=2) + '\n'
    (ROOT / 'site.zip').write_bytes(package)
    (ROOT / 'release.json').write_bytes(manifest.encode('ascii'))
    print('%d files, ZIP SHA-256 %s' % (len(files), digest))


def version_page_assets(files):
    """Refresh browser cache keys only for the homepage's shared CSS and JS."""
    versions = {
        name: hashlib.sha256(files[name].read_bytes()).hexdigest()[:12]
        for name in ('assets/site.css', 'assets/archive.js')
    }
    asset_urls = re.compile(
        r'(?P<attr>\b(?:href|src)=)(?P<quote>["\'])(?P<path>assets/(?:site\.css|archive\.js))'
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
