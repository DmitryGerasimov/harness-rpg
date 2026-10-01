"""Stats of the sheet: totals, the last window and the busiest working places."""

import os
from collections import Counter
from datetime import timedelta

from .constants import ATTR_WINDOW_DAYS
from .transcripts import local_day, parse_ts


def location_of(cwd):
    """Collapse scratch workspaces and worktrees into one location each."""
    if not cwd:
        return None
    if '/Library/Application Support/Claude/' in cwd:
        return 'Claude desktop scratch'
    return cwd.split('/.claude/worktrees/')[0]


def place_name(cwd):
    """Short name of a working place: the folder of its location."""
    location = location_of(cwd)
    return (os.path.basename(location.rstrip('/')) or location) if location else None


def activity(human_sessions, active_days, start, end):
    """Sessions, active days and human turns of the sessions that ended in [start, end)."""
    chosen = [session for session in human_sessions if start <= parse_ts(session['end']) < end]
    first, last = local_day(start), local_day(end)
    return {
        'sessions': len(chosen),
        'active_days': sum(1 for day in active_days if first <= day < last),
        'human_turns': sum(session['counts']['human_turns'] for session in chosen),
        'hours': round(sum(session['active_seconds'] for session in chosen) / 3600, 1),
    }


def build_stats(sessions, human_sessions, active_days, now):
    """Totals over the whole path, the last window and the busiest places.

    There is no "window before" to compare with: Claude Code deletes transcripts after about 30 days, so any
    older window would be counted from whatever happened to survive, not from what really happened.
    """
    starts = [parse_ts(session['start']) for session in sessions]
    ends = [parse_ts(session['end']) for session in sessions]
    places = Counter(place_name(session.get('project')) for session in human_sessions)
    places.pop(None, None)
    window = timedelta(days=ATTR_WINDOW_DAYS)
    return {
        'first_day': local_day(min(starts)) if starts else None,
        'last_day': local_day(max(ends)) if ends else None,
        'sessions': len(human_sessions),
        'all_sessions': len(sessions),
        'human_turns': sum(session['counts']['human_turns'] for session in sessions),
        'tool_calls': sum(session['counts']['tool_calls'] for session in sessions),
        # The hero's working time: the human's and the agent's, long pauses left out.
        'hero_hours': round(sum(session['active_seconds'] for session in human_sessions) / 3600, 1),
        'active_days': len(active_days),
        'locations': len({location_of(session.get('project')) for session in human_sessions} - {None}),
        'top_places': [{'name': name, 'sessions': count} for name, count in places.most_common(5)],
        'recent': activity(human_sessions, active_days, now - window, now + timedelta(days=1)),
    }
