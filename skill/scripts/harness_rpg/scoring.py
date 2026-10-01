"""Scoring helpers: decay, threshold tables, levels, attribute curves and runs of active days."""

from datetime import date, timedelta

from .constants import ATTR_WINDOW_DAYS, DAILY_SESSIONS_CAP, HALF_LIFE_DAYS, LEVEL_BASE_XP, LEVEL_GROWTH
from .transcripts import parse_ts


def decay_score(events, day_ordinal):
    """Sum of weights halved every HALF_LIFE_DAYS, counting events up to day_ordinal."""
    return sum(
        weight * 0.5 ** ((day_ordinal - event_day) / HALF_LIFE_DAYS)
        for event_day, weight in events
        if event_day <= day_ordinal
    )


def usage_profile(day_sessions, today):
    """Current and peak decayed score from {iso day: sessions with a use}."""
    events = sorted(
        (date.fromisoformat(day).toordinal(), min(count, DAILY_SESSIONS_CAP))
        for day, count in day_sessions.items()
    )
    current = decay_score(events, today.toordinal())
    peak = max((decay_score(events, event_day) for event_day, _ in events), default=0.0)
    return current, max(peak, current)


def usage_details(day_sessions, today):
    """What stands behind a decayed score: the day of its peak and the first use."""
    events = sorted(
        (date.fromisoformat(day).toordinal(), min(count, DAILY_SESSIONS_CAP))
        for day, count in day_sessions.items()
    )
    best_day, best = today.toordinal(), decay_score(events, today.toordinal())
    for event_day, _ in events:
        score = decay_score(events, event_day)
        if score > best:
            best_day, best = event_day, score
    return {
        'peak_day': date.fromordinal(best_day).isoformat(),
        'first_day': min(day_sessions, default=None),
    }


def next_step(value, table):
    """The first row of a threshold table above the value as {'name', 'at'}, or None at the top."""
    for row in table:
        if value < row[0]:
            return {'name': row[-1], 'at': row[0]}
    return None


def threshold_index(score, table):
    """Index of the highest table row whose threshold the score reaches."""
    index = 0
    for position, row in enumerate(table):
        if score >= row[0]:
            index = position
    return index


def level_from_xp(xp):
    """Return (level, xp into the level, xp needed for the next level)."""
    level = 1
    need = LEVEL_BASE_XP
    remaining = xp
    while remaining >= need:
        remaining -= need
        level += 1
        need = round(LEVEL_BASE_XP * LEVEL_GROWTH ** (level - 1))
    return level, remaining, need


def saturating(value, midpoint):
    """Map a non-negative metric onto 1..20; the midpoint lands on 10.5."""
    value = max(value, 0.0)
    return 1 + 19 * value / (value + midpoint) if value + midpoint > 0 else 1.0


def linear(value, low, high):
    """Map value onto 1..20 linearly between low and high."""
    share = (value - low) / (high - low) if high != low else 0.0
    return 1 + 19 * min(max(share, 0.0), 1.0)


def percentile(values, share):
    """Linear-interpolated percentile of a non-empty list."""
    ordered = sorted(values)
    position = share * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def current_streak(active_days, today):
    """Consecutive active days ending today or yesterday."""
    days = set(active_days)
    cursor = today if today.isoformat() in days else today - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def recent_sessions(sessions, now):
    """Sessions with a human over the last ATTR_WINDOW_DAYS days."""
    cutoff = now - timedelta(days=ATTR_WINDOW_DAYS)
    return [
        session for session in sessions
        if session['counts']['human_turns'] > 0 and parse_ts(session['end']) >= cutoff
    ]


def longest_run(active_days):
    """Longest run of consecutive active days and the day it ended, or (0, None)."""
    best, end = 0, None
    run = 0
    previous = None
    for day in sorted(date.fromisoformat(value) for value in set(active_days)):
        run = run + 1 if previous is not None and (day - previous).days == 1 else 1
        if run > best:
            best, end = run, day.isoformat()
        previous = day
    return best, end


def longest_streak(active_days):
    """Longest run of consecutive active days."""
    return longest_run(active_days)[0]
