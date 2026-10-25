"""English text for the small built-in UI; the controller stays a single source.

Only bundled UI assets pass through this dictionary. User JSON, names and model
results are never translated. Longest-first, single-pass matching keeps messages
containing units intact and never translates a replacement a second time.
"""
import json
from pathlib import Path
import re


def ui_asset(name, language='ru'):
    root = Path(__file__).parent
    source = (root / name).read_text(encoding='utf-8')
    if language != 'en':
        return source
    translations = json.loads((root / 'ui_en.json').read_text(encoding='utf-8'))
    pattern = '|'.join(re.escape(key) for key in sorted(translations, key=len, reverse=True))
    source = re.sub(pattern, lambda match: translations[match.group()], source)
    if name == 'ui.html':
        source = source.replace('lang="ru"', 'lang="en"').replace('src="/ui.js"', 'src="/ui.js?lang=en"')
    return source
