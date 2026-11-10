"""Refresh the original streak SVG and validate cards before publishing."""

import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def validate(path, content):
    root = ET.fromstring(content)
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError(f'{path}: expected an SVG')
    if any(term in content.lower() for term in (
        'something went wrong', 'maximum retries', 'rate limit exceeded',
        '<script', '<foreignobject',
    )):
        raise ValueError(f'{path}: error card or unsupported content')


def normalize_languages(content):
    """Match the streak's 495 x 195 canvas without stretching card content."""
    validate('languages', content)
    root = ET.fromstring(content)
    if root.get('viewBox') not in ('0 0 495 190', '0 0 495 195'):
        raise ValueError('Expected the compact languages card with card_width=495')
    # Keep the upstream markup intact: XML reserialization can change CSS
    # namespace selectors and is unnecessary for these targeted adjustments.
    content = re.sub(r'\bheight="190"', 'height="195"', content, count=1)
    content = content.replace('viewBox="0 0 495 190"', 'viewBox="0 0 495 195"', 1)
    content = content.replace('height="99%"', 'height="194"', 1)
    # Without animation support, staggered labels must remain visible.
    content = re.sub(
        r'(\.stagger\s*\{\s*)opacity:\s*0;', r'\1opacity: 1;', content,
    )
    if '@media (prefers-reduced-motion: reduce)' in content:
        return content
    return content.replace(
        '</style>',
        '@media (prefers-reduced-motion: reduce) '
        '{ * { animation: none !important; } }</style>',
        1,
    )


if __name__ == '__main__':
    # Keep the original renderer: the alternative public host returned HTTP 403
    # during the audit. A failed refresh never replaces the committed snapshot.
    url = (
        'https://github-readme-streak-stats.herokuapp.com/?user=ErickMurakami'
        '&theme=dark&background=14151A&border=454C63&stroke=454C63'
        '&ring=7897FF&fire=7897FF&currStreakNum=7897FF&sideNums=7897FF'
        '&currStreakLabel=7897FF&sideLabels=7897FF&dates=FFF6E5'
        '&disable_animations=false'
    )
    with urllib.request.urlopen(url, timeout=45) as response:
        content = response.read().decode('utf-8')
    validate('streak', content)
    # Text remains visible if CSS animation is disabled or unsupported.
    content = re.sub(r'opacity:\s*0;(?=\s*animation:)', 'opacity: 1;', content)
    content = content.replace(
        '</style>',
        '@media (prefers-reduced-motion: reduce) '
        '{ * { animation: none !important; } }</style>',
        1,
    )
    languages = Path('assets/top-languages.svg')
    language_content = normalize_languages(languages.read_text())
    for path in Path('assets').glob('*.svg'):
        validate(path, language_content if path == languages else path.read_text())
    validate('streak', content)
    languages.write_text(language_content)
    Path('assets/streak.svg').write_text(content)
