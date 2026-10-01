"""Page language: the vote of each human message and the language of the page."""

from collections import Counter

from .constants import (
    CODE_BLOCK_RE, COMMAND_ARGS_RE, CYRILLIC_RE, INLINE_CODE_RE, LANGS, LANG_FALLBACK, LANG_MIN_LETTERS,
    LANG_RU_LETTERS, LANG_RU_SHARE, LANG_SWITCH_SHARE, MARKER_RE, PASTED_RE, PATH_RE, RUSSIAN_LETTERS, TAG_BLOCK_RE,
    TAG_RE, URL_RE,
)
from .storage import history_path, load_json


def message_lang(text):
    """Vote of one human message: 'ru', 'other', or None when too little of the human's own words is left."""
    text = COMMAND_ARGS_RE.sub(r' \1 ', text or '')
    for pattern in (PASTED_RE, TAG_BLOCK_RE, TAG_RE, CODE_BLOCK_RE, INLINE_CODE_RE, URL_RE, PATH_RE, MARKER_RE):
        text = pattern.sub(' ', text)
    letters = [char for char in text.lower() if char.isalpha()]
    if len(letters) < LANG_MIN_LETTERS:
        return None
    # Cyrillic outside the Russian alphabet (і, ї, є, ґ, ў, ј, љ...) is another language written in Cyrillic.
    if any(CYRILLIC_RE.match(char) and char not in RUSSIAN_LETTERS for char in letters):
        return 'other'
    russian = sum(1 for char in letters if char in RUSSIAN_LETTERS)
    return 'ru' if russian >= LANG_RU_LETTERS or russian >= LANG_RU_SHARE * len(letters) else 'other'


def lang_votes(ledger):
    """Russian and other votes of the human messages over the whole ledger."""
    votes = Counter()
    for session in (ledger.get('sessions') or {}).values():
        votes.update(session.get('langs') or {})
    return votes['ru'], votes['other']


def detect_lang(ru, other, previous=None):
    """Page language from the votes: Russian by majority; a page that has a language switches only on a clear lead."""
    if not ru + other:
        return previous if previous in LANGS else LANG_FALLBACK
    if previous in LANGS:
        rival = other if previous == 'ru' else ru
        if rival < LANG_SWITCH_SHARE * (ru + other):
            return previous
        return 'en' if previous == 'ru' else 'ru'
    return 'ru' if ru >= other else 'en'


def page_lang(home, ledger, override=None):
    """Language of the page: the override, or the votes measured against the language of the latest snapshot."""
    if override in LANGS:
        return override
    history = load_json(history_path(home), [])
    previous = history[-1].get('lang', 'ru') if history else None
    return detect_lang(*lang_votes(ledger), previous)
