"""The page: the character archived and embedded into the template."""

import json
import os

from .achievements import keep_earned
from .archive import archive_snapshot, refresh_texts
from .character import compute_character
from .constants import DATA_PLACEHOLDER
from .lang import page_lang
from .storage import history_path, ledger_path, load_catalog, load_json, save_json
from .views import public_view


def template_path():
    """Bundled HTML template."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'template.html')


def render(home, now=None, lang=None):
    """Compute the character, archive its public snapshot and write the page; return (character, html path, history).

    The page language is the given one or the one the human mostly writes in; the archive is reworded into it.
    """
    ledger = load_json(ledger_path(home), None)
    if ledger is None:
        raise SystemExit('ledger not found: run "rpg.py update" first')
    lang = lang or page_lang(home, ledger)
    character = compute_character(ledger, load_catalog(home), now, lang)
    history = [refresh_texts(snapshot, lang) for snapshot in load_json(history_path(home), [])]
    registry_path = os.path.join(home, 'achievements.json')
    save_json(registry_path, keep_earned(character, load_json(registry_path, {}), history))
    save_json(os.path.join(home, 'character.json'), character)
    # The page and its archive get the game view plus the insights layer; everything else stays in character.json.
    history = archive_snapshot(history, public_view(character))
    save_json(history_path(home), history)
    return character, write_page(home, history), history


def write_page(home, history):
    """Embed the archive into the template and write character.html; return its path."""
    with open(template_path(), encoding='utf-8') as handle:
        template = handle.read()
    if DATA_PLACEHOLDER not in template:
        raise SystemExit(f'template has no {DATA_PLACEHOLDER} placeholder')
    # No '<' at all inside the script: '</script>' would close it early and '<!--' with '<script' would keep
    # the real closing tag from closing it.
    payload = json.dumps(history, ensure_ascii=False).replace('<', '\\u003c')
    html_path = os.path.join(home, 'character.html')
    with open(html_path, 'w', encoding='utf-8') as handle:
        handle.write(template.replace(DATA_PLACEHOLDER, payload))
    return html_path
