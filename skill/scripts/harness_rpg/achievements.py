"""Achievements and the title: medals for all time and the registry that keeps them earned."""

from collections import defaultdict

from .constants import ACHIEVEMENTS, ACH_RECOUNTED, LEGACY_ACH_THRESHOLDS, PUBLIC_SCHEMA_VERSION, SCHOOLS
from .scoring import longest_run
from .stats import location_of
from .texts import TEXTS, achievement_criteria
from .transcripts import local_day, parse_ts


def medal_for(thresholds, value):
    """Index of the best medal a value reaches, -1 for none."""
    return sum(1 for threshold in thresholds if value >= threshold) - 1


def achievement_records(sessions, active_days, catalog):
    """The all-time metric behind each achievement and the day of the record, when it belongs to one day."""
    human = [session for session in sessions if session['counts']['human_turns'] > 0]
    day_schools = defaultdict(set)
    for session in sessions:
        for key, entry in session['skills'].items():
            school = (catalog['skills'].get(key) or {}).get('school')
            if school in SCHOOLS and entry.get('day'):
                day_schools[entry['day']].add(school)

    def best(metric, pool=human):
        records = [(metric(session), local_day(parse_ts(session['start']))) for session in pool]
        return max(records, key=lambda record: record[0], default=(0, None))

    flawless = [session for session in human if session['counts']['tool_errors'] == 0]
    versatile = max(((len(schools), day) for day, schools in day_schools.items()), default=(0, None))
    return {
        'phoenix': best(lambda session: session['counts']['compactions']),
        'flawless': best(lambda session: session['counts']['tool_calls'], flawless),
        'warlord': best(lambda session: session['tools'].get('Agent', 0) + session['tools'].get('Task', 0)),
        'marathon': best(lambda session: session.get('longest_stretch', 0) / 3600),
        'trek': best(lambda session: session['active_seconds'] / 3600),
        'tireless': longest_run(active_days),
        'versatile': versatile,
        'strategist': (sum(1 for session in human if session['plan_mode']), None),
        'polyglot': (len({extension for session in sessions for extension in session.get('extensions', [])}), None),
        'explorer': (len({location_of(session.get('project')) for session in human} - {None}), None),
        'night_owl': (len({night for session in human for night in session.get('night_days', [])}), None),
    }


def achievement_values(sessions, active_days, catalog):
    """The all-time metric behind each achievement."""
    return {key: value for key, (value, _) in achievement_records(sessions, active_days, catalog).items()}


def build_achievements(sessions, active_days, catalog, lang='ru'):
    """All achievements with the best medal reached now (-1 for none) and each medal's criteria."""
    records = achievement_records(sessions, active_days, catalog)
    words = TEXTS[lang]
    achievements = []
    for key, thresholds in ACHIEVEMENTS:
        name, template, forms = words['achievements'][key]
        value, record_day = records[key]
        tier = medal_for(thresholds, value)
        achievements.append({
            'key': key,
            'name': name,
            'value': round(value, 2),
            'record_day': record_day if value else None,
            'thresholds': list(thresholds),
            'tier': tier,
            'tier_name': words['medals'][tier] if tier >= 0 else None,
            'criteria': [achievement_criteria(template, forms, threshold, lang) for threshold in thresholds],
            'earned': tier >= 0,
        })
    return achievements


def title_of(achievements):
    """The achievement with the best medal, or None; ties go to the more prestigious one (earlier in ACHIEVEMENTS)."""
    earned = [item for item in achievements if item['tier'] >= 0]
    return max(earned, key=lambda item: item['tier'], default=None)


def pick_title(achievements):
    """Name of the title: the achievement with the best medal."""
    return (title_of(achievements) or {}).get('name')


def legacy_medal(key):
    """Medal of an achievement earned under the single pre-medal threshold."""
    return medal_for(dict(ACHIEVEMENTS).get(key, ()), LEGACY_ACH_THRESHOLDS.get(key, 0))


def keep_earned(character, registry, history):
    """Make medals permanent: the best medal ever reached stays, even if the session behind it changes later.

    registry maps achievement key -> {'tier': best medal, 'at': when it was reached, 'schema': snapshot schema};
    old entries (a bare timestamp) and old snapshots (an earned flag) are mapped to a medal by
    LEGACY_ACH_THRESHOLDS. Medals of a recounted achievement (ACH_RECOUNTED) recorded before the recount are
    dropped. Returns the updated registry and sets the character's medals and title from it.
    """
    known = dict(ACHIEVEMENTS)
    medals = TEXTS[character.get('lang', 'ru')]['medals']
    best = {}

    def raise_to(key, tier, when, schema):
        if key not in known or tier is None or tier < 0 or schema < ACH_RECOUNTED.get(key, 0):
            return
        if tier > best.get(key, {'tier': -1})['tier']:
            best[key] = {'tier': tier, 'at': when, 'schema': schema}

    for key, entry in registry.items():
        if isinstance(entry, dict):
            raise_to(key, entry.get('tier'), entry.get('at'), entry.get('schema', 0))
        else:
            raise_to(key, legacy_medal(key), entry, 0)
    for snapshot in history:
        for item in snapshot.get('achievements') or []:
            tier = item.get('tier') if 'tier' in item else (legacy_medal(item['key']) if item.get('earned') else -1)
            raise_to(item['key'], tier, snapshot['generated_at'], snapshot.get('schema', 0))
    for item in character['achievements']:
        # The medal today's value reaches on its own; the kept medal can be higher.
        item['value_tier'] = item['tier']
        raise_to(item['key'], item['tier'], character['generated_at'], PUBLIC_SCHEMA_VERSION)
        kept = best.get(item['key'])
        if kept:
            item['tier'] = kept['tier']
            item['tier_name'] = medals[kept['tier']]
        item['earned'] = item['tier'] >= 0
        item['earned_at'] = kept['at'] if kept else None
    character['title'] = pick_title(character['achievements'])
    character['title_key'] = (title_of(character['achievements']) or {}).get('key')
    return best
