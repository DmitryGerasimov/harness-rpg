"""The whole character sheet from the ledger and the catalog."""

from datetime import datetime, timezone

from .achievements import build_achievements, pick_title, title_of
from .alignment import build_alignment
from .attributes import build_attributes
from .auras import build_auras
from .constants import (
    ATTR_WINDOW_DAYS, RARITIES, XP_HUMAN_TURNS_CAP, XP_PER_ACTIVE_DAY, XP_PER_HUMAN_TURN, XP_SESSION_BASE,
)
from .gear import build_gear
from .scoring import level_from_xp
from .skills import build_class, build_skills
from .stats import build_stats
from .texts import TEXTS
from .treasury import build_treasury


def compute_character(ledger, catalog, now=None, lang='ru'):
    """Whole character sheet as a JSON-serializable dict, worded in the page language."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone().date()
    sessions = [session for session in ledger.get('sessions', {}).values() if session.get('start')]
    human_sessions = [session for session in sessions if session['counts']['human_turns'] > 0]
    active_days = sorted({day for session in human_sessions for day in session['days']})
    counted_turns = sum(min(session['counts']['human_turns'], XP_HUMAN_TURNS_CAP) for session in human_sessions)
    xp_parts = {
        'sessions': XP_SESSION_BASE * len(human_sessions),
        'turns': XP_PER_HUMAN_TURN * counted_turns,
        'days': XP_PER_ACTIVE_DAY * len(active_days),
    }
    xp = sum(xp_parts.values())
    level, into, need = level_from_xp(xp)
    skills = build_skills(sessions, catalog, today, lang)
    achievements = build_achievements(sessions, active_days, catalog, lang)
    words = TEXTS[lang]
    return {
        'generated_at': now.astimezone().isoformat(timespec='seconds'),
        'lang': lang,
        'hero': {'name': 'Claude Code'},
        'level': {
            'level': level, 'xp': xp, 'into': into, 'need': need, 'xp_parts': xp_parts,
            'counted_turns': counted_turns,
        },
        'class': build_class(skills, lang),
        'title': pick_title(achievements),
        'title_key': (title_of(achievements) or {}).get('key'),
        'achievements': achievements,
        'auras': build_auras(sessions, now, lang),
        'alignment': build_alignment(sessions, now, lang),
        'treasury': build_treasury(sessions, now, lang),
        'attributes': build_attributes(sessions, active_days, catalog, now, today, lang),
        'skills': skills,
        'gear': build_gear(sessions, catalog, today, lang),
        'stats': build_stats(sessions, human_sessions, active_days, now),
        'schools': {key: {'name': name, 'desc': desc} for key, (name, desc, _) in words['schools'].items()},
        'ranks': list(words['ranks']),
        'rarities': [{'key': key, 'name': words['rarities'][key]} for _, key in RARITIES],
        'window_days': ATTR_WINDOW_DAYS,
    }
