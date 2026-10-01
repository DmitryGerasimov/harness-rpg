"""Auras: hooks grouped by event, strong by the share of recent sessions where they fired."""

from collections import Counter, defaultdict

from .constants import AURAS, AURA_TIERS
from .scoring import next_step, recent_sessions, threshold_index
from .texts import TEXTS, named
from .transcripts import local_day, parse_ts


def aura_theme(event):
    """Aura key for a hook event, or None for events without a theme."""
    for key, events in AURAS:
        if event in events:
            return key
    return None


def build_auras(sessions, now, lang='ru'):
    """Auras from hooks: tier by the share of recent sessions where they fired; dormant when only in the past."""
    window = recent_sessions(sessions, now)

    def themes(session):
        return {aura_theme(event) for event in session.get('hooks', {})} - {None}

    ever = set().union(*(themes(session) for session in sessions)) if sessions else set()
    recent = Counter(theme for session in window for theme in themes(session))
    events = defaultdict(Counter)
    scripts = defaultdict(Counter)
    last_day = {}
    for session in sessions:
        day = local_day(parse_ts(session['start']))
        for event, fired in session.get('hooks', {}).items():
            theme = aura_theme(event)
            if not theme:
                continue
            events[theme][event] += fired
            scripts[theme].update(session.get('hook_names', {}).get(event, {}))
            last_day[theme] = max(last_day.get(theme, ''), day)
    words = TEXTS[lang]
    tiers = named(AURA_TIERS, words['aura_tiers'])
    auras = []
    for key, _ in AURAS:
        if key not in ever:
            continue
        name, effect = words['auras'][key]
        share = recent[key] / len(window) if window else 0.0
        tier = threshold_index(share, tiers) if recent[key] else -1
        auras.append({
            'key': key,
            'name': name,
            'effect': effect,
            'share': round(share, 3),
            'tier': tier,
            'tier_name': tiers[tier][1] if tier >= 0 else words['aura_dormant'],
            'sessions': recent[key],
            'window': len(window),
            'events': dict(events[key].most_common()),
            'hooks': dict(scripts[key].most_common()),
            'last_day': last_day.get(key),
            'next_tier': next_step(share, tiers) if recent[key] else None,
        })
    auras.sort(key=lambda aura: (-aura['share'], aura['key']))
    return auras
