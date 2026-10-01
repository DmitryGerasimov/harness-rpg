"""Insights: the digest of the real work for the agent, and the findings it attaches to the latest snapshot."""

import statistics
from collections import Counter, defaultdict
from datetime import timedelta

from .alignment import loosest_mode
from .archive import refresh_texts
from .constants import (
    ATTR_WINDOW_DAYS, DIGEST_TOP_TOOLS, FINDINGS_MAX, FINDING_TEXT_MAX_LENGTH, FINDING_TITLE_MAX_LENGTH, FINDING_TONES,
    GOLD_WEIGHTS,
)
from .lang import message_lang
from .names import gear_parts
from .page import write_page
from .scoring import percentile
from .stats import place_name
from .storage import history_path, load_json, save_json
from .transcripts import local_day, parse_ts
from .treasury import gold_of


def reality_digest(ledger, catalog, now):
    """Plain facts about the real work behind the hero, for findings about reality rather than the game.

    Counted over the last ATTR_WINDOW_DAYS days; "all_time" keys look at the whole ledger. Gold is
    price-weighted tokens in millions, hours are active time.
    """
    sessions = [session for session in ledger.get('sessions', {}).values() if session.get('start')]
    today = now.astimezone().date()
    window = [session for session in sessions if parse_ts(session['end']) >= now - timedelta(days=ATTR_WINDOW_DAYS)]
    in_window = {id(session) for session in window}
    human = [session for session in window if session['counts']['human_turns'] > 0]

    def total(pool, key):
        return sum(session['counts'].get(key, 0) for session in pool)

    def subagents(session):
        return session['tools'].get('Agent', 0) + session['tools'].get('Task', 0)

    def gold(pool):
        return round(sum(gold_of(session) for session in pool) / 1e6, 1)

    def hours(session):
        return session['active_seconds'] / 3600

    def spread(values, digits=1):
        values = list(values)
        if not values:
            return None
        return {'median': round(statistics.median(values), digits), 'p90': round(percentile(values, 0.9), digits),
                'max': round(max(values), digits)}

    def day_of(session):
        return local_day(parse_ts(session['start']))

    by_place = defaultdict(list)
    for session in window:
        by_place[place_name(session.get('project')) or '-'].append(session)
    places = sorted(by_place.items(), key=lambda item: -len(item[1]))[:8]

    # Four whole weeks fit in the window that transcripts always cover; an older week would be cut by cleanup.
    weeks = []
    for back in range(3, -1, -1):
        start, end = now - timedelta(days=7 * (back + 1)), now - timedelta(days=7 * back)
        pool = [session for session in sessions if start <= parse_ts(session['end']) < end]
        people = [session for session in pool if session['counts']['human_turns'] > 0]
        weeks.append({
            'from': local_day(start), 'sessions': len(people), 'turns': total(people, 'human_turns'),
            'tool_calls': total(people, 'tool_calls'), 'gold': gold(pool),
        })

    tokens = {name: sum((session.get('tokens') or {}).get(name, 0) for session in window) for name in GOLD_WEIGHTS}
    read = tokens['input'] + tokens['cache_write'] + tokens['cache_read']
    dearest = sorted(window, key=gold_of, reverse=True)[:5]

    skill_sessions, skill_last, skill_first, skill_names = Counter(), {}, {}, {}
    for session in sessions:
        for key, entry in session['skills'].items():
            if not entry.get('day'):
                continue
            skill_names.setdefault(key, entry['display'])
            skill_last[key] = max(skill_last.get(key, ''), entry['day'])
            skill_first[key] = min(skill_first.get(key, '9999'), entry['day'])
            if id(session) in in_window:
                skill_sessions[key] += 1
    quiet_from = (today - timedelta(days=14)).isoformat()
    fresh_from = (today - timedelta(days=7)).isoformat()
    all_time = Counter(key for session in sessions for key, entry in session['skills'].items() if entry.get('day'))

    mcp = defaultdict(lambda: {'sessions': 0, 'calls': 0, 'tools': Counter(), 'first_day': '9999', 'last_day': ''})
    for session in sessions:
        for server, entry in session['mcp'].items():
            if not entry.get('day'):
                continue
            for part in gear_parts(server, entry, catalog).values():
                item = mcp[part['name']]
                item['first_day'] = min(item['first_day'], entry['day'])
                item['last_day'] = max(item['last_day'], entry['day'])
                if id(session) in in_window:
                    item['sessions'] += 1
                    item['calls'] += sum(part['tools'].values())
                    item['tools'].update(part['tools'])

    hooks = defaultdict(lambda: {'fires': 0, 'sessions': 0, 'scripts': Counter()})
    for session in human:
        for event, fired in session.get('hooks', {}).items():
            hooks[event]['fires'] += fired
            hooks[event]['sessions'] += 1
            hooks[event]['scripts'].update(session.get('hook_names', {}).get(event, {}))

    builtin = Counter()
    for session in human:
        builtin.update(session['tools'])
    starts_by_hour = Counter(parse_ts(session['start']).astimezone().hour for session in human)
    starts_by_weekday = Counter(parse_ts(session['start']).astimezone().weekday() for session in human)
    working = [session for session in human if session['counts']['edits'] > 0]
    return {
        'window_days': ATTR_WINDOW_DAYS,
        'sessions': {
            'with_human': len(human), 'background': len(window) - len(human),
            'background_gold': gold([session for session in window if session['counts']['human_turns'] == 0]),
            'active_days': len({day for session in human for day in session['days']}),
            'hours': spread(hours(session) for session in human),
            'turns': spread((session['counts']['human_turns'] for session in human), 0),
            'long_over_3h': sum(1 for session in human if hours(session) >= 3),
            'entrypoints': dict(Counter(session.get('entrypoint') or '-' for session in human).most_common()),
        },
        'rhythm': {
            'by_hour': [starts_by_hour[hour] for hour in range(24)],
            'by_weekday_mon_first': [starts_by_weekday[day] for day in range(7)],
            'night_sessions': sum(1 for session in human if session.get('night_days')),
            'weeks': weeks,
        },
        'places': [
            {
                'name': name, 'sessions': len(pool), 'hours': round(sum(hours(session) for session in pool), 1),
                'turns': total(pool, 'human_turns'), 'tool_calls': total(pool, 'tool_calls'),
                'tool_errors': total(pool, 'tool_errors'), 'compactions': total(pool, 'compactions'),
                'gold': gold(pool),
            }
            for name, pool in places
        ],
        'money': {
            'gold': gold(window),
            'tokens_millions': {name: round(value / 1e6, 1) for name, value in tokens.items()},
            'gold_weights': GOLD_WEIGHTS,
            'cache_read_share_of_input': round(tokens['cache_read'] / read, 3) if read else None,
            'gold_per_human_session': spread((gold_of(session) / 1e6 for session in human), 1),
            'dearest': [
                {'day': day_of(session), 'place': place_name(session.get('project')),
                 'gold': round(gold_of(session) / 1e6, 1), 'hours': round(hours(session), 1),
                 'turns': session['counts']['human_turns'], 'compactions': session['counts']['compactions'],
                 'subagents': subagents(session)}
                for session in dearest
            ],
        },
        'autonomy': {
            'tool_calls_per_turn': spread(
                (session['counts']['tool_calls'] / session['counts']['human_turns'] for session in human), 1),
            'interrupts': total(human, 'interrupts'), 'denials': total(human, 'denials'),
            'turns': total(human, 'human_turns'),
            'sessions_with_friction': sum(1 for s in human if s['counts']['interrupts'] + s['counts']['denials']),
            'loosest_permission_mode': dict(Counter(loosest_mode(session) for session in human).most_common()),
            'plan_mode_sessions': sum(1 for session in human if session['plan_mode']),
            'subagent_calls': sum(subagents(session) for session in human),
            'sessions_with_subagents': sum(1 for session in human if subagents(session)),
            'compactions': total(human, 'compactions'),
            'sessions_with_compactions': sum(1 for session in human if session['counts']['compactions']),
        },
        'quality': {
            'tool_calls': total(human, 'tool_calls'), 'tool_errors': total(human, 'tool_errors'),
            'edits': total(human, 'edits'), 'edit_errors': total(human, 'edit_errors'),
            'sessions_with_edits': len(working),
            'sessions_with_edits_and_no_checks': sum(
                1 for session in working if not session['counts']['verifications']
            ),
            'test_and_lint_runs': total(human, 'verifications'), 'destructive_commands': total(human, 'destructive'),
            'commits': total(human, 'commits'), 'prs': total(human, 'prs'), 'outbound_mcp': total(human, 'outbound'),
            'doc_lookups': total(human, 'doc_lookups'),
        },
        'builtin_tools': dict(builtin.most_common(15)),
        'skills': {
            'top': [
                {'name': skill_names[key], 'sessions': count, 'last_day': skill_last[key]}
                for key, count in skill_sessions.most_common(12)
            ],
            'new_this_week': [skill_names[key] for key, day in sorted(skill_first.items()) if day >= fresh_from],
            'quiet_for_2_weeks': [
                {'name': skill_names[key], 'all_time_sessions': all_time[key], 'last_day': skill_last[key]}
                for key in sorted(skill_last, key=lambda key: -all_time[key])
                if skill_last[key] < quiet_from and all_time[key] >= 2
            ][:10],
            'used_in_window': len(skill_sessions),
        },
        'mcp': [
            {'name': name, 'sessions': item['sessions'], 'calls': item['calls'], 'first_day': item['first_day'],
             'last_day': item['last_day'], 'top_tools': dict(item['tools'].most_common(DIGEST_TOP_TOOLS)),
             'tools_used': len(item['tools'])}
            for name, item in sorted(mcp.items(), key=lambda pair: -pair[1]['calls'])
        ],
        'hooks': {
            event: {
                'fires': item['fires'], 'sessions': item['sessions'],
                'scripts': dict(item['scripts'].most_common()),
            }
            for event, item in sorted(hooks.items(), key=lambda pair: -pair[1]['fires'])
        },
    }


def insight_digest(history, reality):
    """What the agent reads to find insights: facts about the real work, and the page names to point at."""
    if not history or not history[-1].get('insights'):
        raise SystemExit('the latest snapshot has no stats: run "rpg.py render" first')
    current = history[-1]['insights']
    earlier = next((snapshot['insights']['findings'] for snapshot in reversed(history[:-1])
                    if (snapshot.get('insights') or {}).get('findings')), [])
    return {
        'snapshot': history[-1]['generated_at'],
        # Findings are written in the language of the page.
        'lang': history[-1].get('lang', 'ru'),
        'reality': reality,
        # Findings may point at the page: real name -> the name the hero page shows.
        'page_names': {
            'skills': {item['name']: alias for alias, item in current['skills'].items()},
            'mcp': {item['name']: alias for alias, item in current['gear'].items()},
        },
        'previous_findings': [finding['title'] for finding in current.get('findings') or earlier],
    }


def parse_findings(answer, lang='ru'):
    """Validate the agent's findings, written in the page language; return (findings, errors)."""
    items = answer.get('findings') if isinstance(answer, dict) else None
    if not isinstance(items, list) or not items:
        return [], ['"findings" must be a non-empty list']
    if len(items) > FINDINGS_MAX:
        return [], [f'at most {FINDINGS_MAX} findings, got {len(items)}']
    findings, errors = [], []
    for number, item in enumerate(items, 1):
        if not isinstance(item, dict):
            errors.append(f'finding {number}: must be an object')
            continue
        title = str(item.get('title') or '').strip()
        text = str(item.get('text') or '').strip()
        tone = item.get('tone') or 'note'
        if not title or len(title) > FINDING_TITLE_MAX_LENGTH:
            errors.append(f'finding {number}: title must be 1..{FINDING_TITLE_MAX_LENGTH} characters')
        elif not text or len(text) > FINDING_TEXT_MAX_LENGTH:
            errors.append(f'finding {number}: text must be 1..{FINDING_TEXT_MAX_LENGTH} characters')
        elif tone not in FINDING_TONES:
            errors.append(f'finding {number}: tone must be one of {sorted(FINDING_TONES)}')
        elif (message_lang(f'{title}\n{text}') == 'ru') != (lang == 'ru'):
            language = 'Russian' if lang == 'ru' else 'English'
            errors.append(f'finding {number}: write it in {language}, the page language')
        else:
            findings.append({'title': title, 'text': text, 'tone': tone})
    return (findings, errors) if not errors else ([], errors)


def attach_findings(home, answer):
    """Store findings in the latest snapshot and rewrite the page; return (errors, html path)."""
    history = load_json(history_path(home), [])
    if not history or not history[-1].get('insights'):
        return ['the latest snapshot has no stats: run "rpg.py render" first'], None
    lang = history[-1].get('lang', 'ru')
    findings, errors = parse_findings(answer, lang)
    if errors:
        return errors, None
    history[-1]['insights']['findings'] = findings
    save_json(history_path(home), history)
    return [], write_page(home, [refresh_texts(snapshot, lang) for snapshot in history])
