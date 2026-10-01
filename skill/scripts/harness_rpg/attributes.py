"""Attributes: six D&D scores from quality ratios over the recent window."""

import statistics
from datetime import timedelta

from .constants import (
    ATTRIBUTES, ATTR_WINDOW_DAYS, CHA_ACTIONS_MID, CON_COMPACTIONS_MID, CON_HOURS_MID, CON_STREAK_MID, DEX_SUCCESS_LO,
    INT_BREADTH_MID, INT_DOCS_MID, STR_EDITS_MID, WIS_AUTONOMY_MID, WIS_FRICTION_HI, WIS_PLAN_SHARE_MID,
)
from .names import resolve_mcp
from .scoring import current_streak, linear, percentile, saturating
from .texts import TEXTS, grouped, localized, plural
from .transcripts import parse_ts


def attribute(key, value, metrics, lang='ru'):
    """One attribute row: the page value, and the metrics with their own 1..20 scores behind it.

    metrics are (shown value, score) in the order of the attribute's labels; a metric without its own score only
    explains the ones that have it.
    """
    abbr, name, desc, rule, labels = TEXTS[lang]['attributes'][key]
    return {
        'key': key,
        'abbr': abbr,
        'name': name,
        'desc': desc,
        'value': int(min(max(round(value), 1), 20)),
        'metrics': [
            {'label': label, 'value': localized(shown, lang), 'score': None if score is None else round(score, 1)}
            for label, (shown, score) in zip(labels, metrics)
        ],
        'rule': localized(rule, lang),
    }


def build_attributes(sessions, active_days, catalog, now, today, lang='ru'):
    """Six D&D attributes from quality ratios over the last ATTR_WINDOW_DAYS."""
    cutoff = now - timedelta(days=ATTR_WINDOW_DAYS)
    window = [
        session for session in sessions
        if session['counts']['human_turns'] > 0 and parse_ts(session['end']) >= cutoff
    ]
    if not window:
        return [attribute(key, 1, [], lang) for key in ATTRIBUTES]

    def total(key):
        return sum(session['counts'][key] for session in window)

    # Investigation-only sessions have no edits; strength is measured on working sessions.
    working = [session['counts']['edits'] for session in window if session['counts']['edits'] > 0]
    edits_median = statistics.median(working) if working else 0
    strength = saturating(edits_median, STR_EDITS_MID)

    calls = total('tool_calls')
    tool_ok = 1 - total('tool_errors') / calls if calls else 1.0
    edits = total('edits')
    edit_ok = 1 - total('edit_errors') / edits if edits else tool_ok
    dexterity = linear((tool_ok + edit_ok) / 2, DEX_SUCCESS_LO, 1.0)

    hours_p90 = percentile([session['active_seconds'] / 3600 for session in window], 0.9)
    compactions = total('compactions')
    streak = current_streak(active_days, today)
    endurance = (
        saturating(hours_p90, CON_HOURS_MID),
        saturating(compactions, CON_COMPACTIONS_MID),
        saturating(streak, CON_STREAK_MID),
    )

    tools = {name for session in window for name in session['tools']}
    skills = {key for session in window for key in session['skills']}
    servers = {
        resolve_mcp(server, catalog)[0]
        for session in window for server in session['mcp']
    } - {None}
    breadth = len(tools) + len(skills) + len({name.lower() for name in servers})
    docs = total('doc_lookups') / len(window)
    learning = (saturating(breadth, INT_BREADTH_MID), saturating(docs, INT_DOCS_MID))

    autonomy = statistics.median(
        session['counts']['tool_calls'] / session['counts']['human_turns'] for session in window
    )
    turns = total('human_turns')
    friction = (total('interrupts') + total('denials')) / turns
    plan_share = sum(1 for session in window if session['plan_mode']) / len(window)
    judgement = (
        saturating(autonomy, WIS_AUTONOMY_MID),
        linear(WIS_FRICTION_HI - friction, 0.0, WIS_FRICTION_HI),
        saturating(plan_share, WIS_PLAN_SHARE_MID),
    )

    window_days = {day for session in window for day in session['days']}
    actions = total('commits') + total('prs') + total('outbound')
    actions_per_day = actions / max(len(window_days), 1)
    charisma = saturating(actions_per_day, CHA_ACTIONS_MID)

    values = (
        strength, dexterity, statistics.mean(endurance), statistics.mean(learning), statistics.mean(judgement),
        charisma,
    )
    words = TEXTS[lang]['metric']

    def share_of(part, whole):
        return words['of'].format(part=part, whole=whole)

    metrics = (
        [(f'{edits_median:g}', strength), (share_of(len(working), len(window)), None)],
        [
            (share_of(f'{tool_ok:.1%}', grouped(calls, lang)), linear(tool_ok, DEX_SUCCESS_LO, 1.0)),
            (share_of(f'{edit_ok:.1%}', grouped(edits, lang)), linear(edit_ok, DEX_SUCCESS_LO, 1.0)),
        ],
        [
            (words['from_hours'].format(hours=f'{hours_p90:.1f}'), endurance[0]),
            (f'{compactions}', endurance[1]),
            (f'{streak}', endurance[2]),
        ],
        [
            (f'{breadth} = {len(tools)} + {len(skills)} + {len({name.lower() for name in servers})}', learning[0]),
            (f'{docs:.2f}', learning[1]),
        ],
        [(f'{autonomy:.1f}', judgement[0]), (f'{friction:.2f}', judgement[1]), (f'{plan_share:.0%}', judgement[2])],
        [
            (f'{total("commits")}, {total("prs")}, {total("outbound")}', None),
            (words['per_days'].format(value=f'{actions_per_day:.1f}', days=len(window_days),
                                      noun=plural(lang, len(window_days), words['day_forms'])), charisma),
        ],
    )
    return [attribute(key, value, metric, lang) for key, value, metric in zip(ATTRIBUTES, values, metrics)]
