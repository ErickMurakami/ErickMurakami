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


def theme_card(content, *, light=False):
    """Use neutral framing while preserving the languages' identifying colors."""
    text, secondary, border = (
        ('#292e35', '#59636f', '#cbd0d6') if light
        else ('#e5e7eb', '#b8bec6', '#41454b')
    )
    colors = {'#e5e7eb': text, '#c4c7cc': secondary, '#41454b': border}
    content = re.sub(
        r'#[0-9a-fA-F]{6}\b',
        lambda match: colors.get(match[0].lower(), match[0]), content,
    )
    def transparent_background(match):
        return re.sub(r"fill=([\"'])[^\"']*\1", 'fill="none"', match[0])
    content = re.sub(
        r'<rect\b[^>]*data-testid="card-bg"[^>]*/>',
        transparent_background, content,
    )
    content = re.sub(
        r"<rect\b[^>]*width='494'[^>]*/>",
        transparent_background, content,
    )
    return content


if __name__ == '__main__':
    # Keep the original renderer: the alternative public host returned HTTP 403
    # during the audit. A failed refresh never replaces the committed snapshot.
    url = (
        'https://github-readme-streak-stats.herokuapp.com/?user=ErickMurakami'
        '&theme=dark&background=1B1C1E&border=41454B&stroke=41454B'
        '&ring=C4C7CC&fire=C4C7CC&currStreakNum=C4C7CC&sideNums=C4C7CC'
        '&currStreakLabel=C4C7CC&sideLabels=C4C7CC&dates=E5E7EB'
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
    outputs = {
        Path('assets/streak.svg'): theme_card(content),
        Path('assets/streak-light.svg'): theme_card(content, light=True),
        languages: theme_card(language_content),
        Path('assets/top-languages-light.svg'): theme_card(language_content, light=True),
    }
    for path, svg in outputs.items():
        validate(path, svg)
    for path, svg in outputs.items():
        path.write_text(svg)
