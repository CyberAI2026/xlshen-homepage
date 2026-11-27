"""Set the tab behavior for links in the released HTML."""

from html import escape
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit


PREVIEWABLE = {'.pdf', '.png', '.jpg', '.jpeg', '.webp', '.gif'}
EXPERIMENT_PAGE = 'information-reception-lab.html'



class LinkTargets(HTMLParser):
    def __init__(self, source, page):
        super().__init__(convert_charrefs=False)
        self.page = page
        self.line_starts = [0] + [m.end() for m in re.finditer('\n', source)]
        self.edits = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        attrs = dict(attrs)
        href = attrs.get('href')
        if not href or 'skip' in (attrs.get('class') or '').split():
            return
        if self.page == EXPERIMENT_PAGE and href.startswith('#'):
            return
        url = urlsplit(href)
        if url.scheme not in ('', 'http', 'https'):
            return

        download = 'download' in attrs
        if download and PurePosixPath(url.path).suffix.lower() not in PREVIEWABLE:
            return
        rel = (attrs.get('rel') or '').split()
        if attrs.get('target') == '_blank' and 'noopener' in rel and not download:
            return
        attrs.pop('download', None)
        attrs['target'] = '_blank'
        if 'noopener' not in rel:
            attrs['rel'] = ' '.join([*rel, 'noopener'])

        original = self.get_starttag_text()
        attributes = [name if value is None else f'{name}="{escape(value, quote=True)}"'
                      for name, value in attrs.items()]
        updated = '<a ' + ' '.join(attributes) + '>'
        line, column = self.getpos()
        offset = self.line_starts[line - 1] + column
        self.edits.append((offset, len(original), updated))


def set_link_targets(files):
    for name, path in files.items():
        if path.suffix != '.html':
            continue
        source = path.read_text(encoding='utf-8')
        parser = LinkTargets(source, name)
        parser.feed(source)
        parser.close()
        if parser.edits:
            parts = []
            start = 0
            for offset, length, updated in parser.edits:
                parts.extend((source[start:offset], updated))
                start = offset + length
            parts.append(source[start:])
            path.write_text(''.join(parts), encoding='utf-8')
