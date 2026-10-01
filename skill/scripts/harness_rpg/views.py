"""Public view of the character: the game part of the page and the insights layer behind it."""

from collections import Counter, defaultdict

from .constants import (
    ALIGNMENTS, ATTR_WINDOW_DAYS, AURA_TIERS, DAILY_SESSIONS_CAP, GEAR_SLOTS, GOLD_WEIGHTS, HALF_LIFE_DAYS,
    HYBRID_RATIO, LAW_CHAOTIC_UPTO, LAW_LAWFUL_FROM, LAW_PLAN_SHARE_FULL, LAW_RULES_MID, LEVEL_BASE_XP, LEVEL_GROWTH,
    MORAL_EVIL_BELOW, MORAL_EVIL_WEIGHT, MORAL_GOOD_FROM, PERMISSION_STRICTNESS, PUBLIC_SCHEMA_VERSION, RARITIES,
    SCHOOLS, SKILL_RANKS, SLOT_KEYS, XP_HUMAN_TURNS_CAP, XP_PER_ACTIVE_DAY, XP_PER_HUMAN_TURN, XP_SESSION_BASE,
)
from .names import alias_problem
from .texts import TEXTS, named, school_texts
from .treasury import treasury_steps


def unique_aliases(items, fallback):
    """Aliases for items in order; missing ones get a numbered fallback, repeats get a counter."""
    seen = Counter()
    unnamed = 0
    result = []
    for item in items:
        alias = (item.get('alias') or '').strip()
        if not alias:
            unnamed += 1
            alias = f'{fallback} {unnamed}'
        seen[alias] += 1
        result.append(alias if seen[alias] == 1 else f'{alias} ({seen[alias]})')
    return result


def public_view(character):
    """Page payload for sharing: game values only, no real names, tools, paths or usage numbers."""
    lang = character.get('lang', 'ru')
    words = TEXTS[lang]
    weights = character['class']['weights']
    top = max(weights.values(), default=0.0) or 1.0
    ranked = sorted((key for key in SCHOOLS if weights.get(key, 0) > 0), key=lambda key: (-weights[key], key))
    # Re-check cached aliases: a hand-edited catalog must not leak real names either.
    skill_aliases = unique_aliases(
        [
            {'alias': None if alias_problem(skill['alias'], (skill['key'], skill['name']), lang) else skill['alias']}
            for skill in character['skills']
        ],
        words['skill_fallback'],
    )
    gear_aliases = unique_aliases(
        [
            {'alias': None if alias_problem(item['alias'], [item['name'], *item['servers']], lang) else item['alias']}
            for item in character['gear']
        ],
        words['gear_fallback'],
    )
    groups = []
    for school in ranked + [key for key in SCHOOLS if key not in ranked] + [None]:
        rows = [
            {
                'alias': alias,
                'rank': skill['rank'],
                'rank_name': skill['rank_name'],
                'peak_rank': skill['peak_rank'],
                'peak_rank_name': skill['peak_rank_name'],
                'rusty': skill['rusty'],
            }
            for skill, alias in zip(character['skills'], skill_aliases)
            if (skill['school'] if skill['school'] in SCHOOLS else None) == school
        ]
        if rows:
            name, desc = school_texts(school, lang)
            groups.append({'key': school, 'name': name, 'desc': desc, 'skills': rows})
    gear = [
        {
            'alias': alias,
            'rarity': item['rarity'],
            'rarity_name': item['rarity_name'],
            'peak_rarity': item['peak_rarity'],
            'peak_rarity_name': item['peak_rarity_name'],
            'affixes': item['affixes'],
            'slot': item['slot'] if item['slot'] in SLOT_KEYS else None,
            'equipped': item['equipped'],
        }
        for item, alias in zip(character['gear'], gear_aliases)
    ]
    hero_class = character['class']
    return {
        'insights': insight_view(character, skill_aliases, gear_aliases),
        'schema': PUBLIC_SCHEMA_VERSION,
        'lang': lang,
        'generated_at': character['generated_at'],
        'period': {'from': character['stats']['first_day'], 'to': character['stats']['last_day']},
        'hero': character['hero'],
        'level': {key: character['level'][key] for key in ('level', 'into', 'need')},
        'class': {key: hero_class[key] for key in ('name', 'primary', 'secondary', 'basis', 'epithet', 'lore')},
        'title': character['title'],
        'title_key': character.get('title_key'),
        'achievements': [
            {key: item[key] for key in ('key', 'name', 'tier', 'tier_name', 'criteria', 'earned')}
            for item in character['achievements']
        ],
        'auras': [
            {key: aura[key] for key in ('key', 'name', 'effect', 'tier', 'tier_name')} for aura in character['auras']
        ],
        'alignment': {key: character['alignment'][key] for key in ('law', 'moral', 'name', 'desc')},
        'treasury': {
            'gold': {key: character['treasury']['gold'][key] for key in ('tier', 'name')},
            'camp': {key: character['treasury']['camp'][key] for key in ('tier', 'name')},
            'gold_tiers': list(words['gold_tiers']),
            'camp_tiers': list(words['camp_tiers']),
            **treasury_steps(lang),
        },
        'alignment_grid': [
            {'law': law, 'moral': moral, 'name': words['alignments'][(law, moral)][0],
             'desc': words['alignments'][(law, moral)][1]}
            for law, moral in ALIGNMENTS
        ],
        'schools': [
            {
                'key': key, 'name': words['schools'][key][0], 'desc': words['schools'][key][1],
                'lore': words['schools'][key][2], 'share': round(weights[key] / top, 3),
            }
            for key in ranked
        ],
        'attributes': [
            {key: attr[key] for key in ('key', 'abbr', 'name', 'desc', 'value')}
            for attr in character['attributes']
        ],
        'skill_groups': groups,
        'gear': gear,
        'ranks': character['ranks'],
        'rarities': character['rarities'],
        'slots': [{'key': key, 'name': words['slots'][key][0], 'desc': words['slots'][key][1]} for key in GEAR_SLOTS],
    }


def game_view(snapshot):
    """The game part of a snapshot: everything the page shows with the insights mode off."""
    return {key: value for key, value in snapshot.items() if key != 'insights'}


def insight_view(character, skill_aliases, gear_aliases):
    """Payload of the insights mode: real names, usage numbers and the rules behind every game value.

    Items are keyed by their page alias (skills, gear) or key (attributes, auras, achievements), so the page
    finds the details of whatever it draws. The agent's findings are attached later by "rpg.py insights".
    """
    weights = character['class']['weights']
    ranked = sorted((weight for weight in weights.values() if weight > 0), reverse=True)
    by_school = defaultdict(list)
    for skill in character['skills']:
        by_school[skill['school'] if skill['school'] in SCHOOLS else None].append(skill['name'])
    gear_alias = {item['name']: alias for item, alias in zip(character['gear'], gear_aliases)}
    words = TEXTS[character.get('lang', 'ru')]
    rarity_at = {key: threshold for threshold, key in RARITIES}
    details = character['alignment']['details']
    level = character['level']
    return {
        'findings': [],
        'hero': {
            'xp': level['xp'],
            'xp_parts': level.get('xp_parts'),
            'counted_turns': level.get('counted_turns'),
            'class_ratio': round(ranked[1] / ranked[0], 3) if len(ranked) > 1 else None,
            'stats': character['stats'],
        },
        'schools': {
            key: {'weight': weights.get(key, 0.0), 'skills': len(by_school[key]), 'top': by_school[key][:3]}
            for key in SCHOOLS if by_school[key]
        },
        'attributes': {
            attr['key']: {'metrics': attr['metrics'], 'rule': attr['rule']} for attr in character['attributes']
        },
        'skills': {
            alias: {
                'name': skill['name'], 'school': skill['school'] if skill['school'] in SCHOOLS else None,
                'rank': skill['rank_name'], 'peak_rank': skill['peak_rank_name'],
                'score': skill['score'], 'peak': skill['peak_score'], 'peak_day': skill.get('peak_day'),
                'rank_at': SKILL_RANKS[skill['rank']], 'next': skill.get('next_rank'),
                'sessions': skill['sessions'], 'calls': skill['calls'],
                'first_day': skill.get('first_day'), 'last_day': skill['last_day'],
            }
            for skill, alias in zip(character['skills'], skill_aliases)
        },
        'gear': {
            alias: {
                'name': item['name'], 'rarity': item['rarity_name'], 'peak_rarity': item['peak_rarity_name'],
                'score': item['score'], 'peak': item['peak_score'], 'peak_day': item.get('peak_day'),
                'rarity_at': rarity_at[item['rarity']], 'next': item.get('next_rarity'),
                'sessions': item['sessions'], 'calls': item['calls'],
                'first_day': item.get('first_day'), 'last_day': item['last_day'],
                'slot': item['slot'] if item['slot'] in SLOT_KEYS else None, 'equipped': item['equipped'],
                'worn_instead': gear_alias.get(item.get('worn_instead')),
                'tools': [[tool['name'], tool['calls']] for tool in item.get('tools', [])],
            }
            for item, alias in zip(character['gear'], gear_aliases)
        },
        'auras': {
            aura['key']: {
                field: aura.get(field)
                for field in ('share', 'sessions', 'window', 'events', 'hooks', 'last_day', 'next_tier')
            } | {'tier_at': AURA_TIERS[aura['tier']] if aura['tier'] >= 0 else None}
            for aura in character['auras']
        },
        'alignment': {
            **details,
            'law_parts': [
                round(details.get('rules_lines', 0) / (details.get('rules_lines', 0) + LAW_RULES_MID), 3),
                round(min(1.0, details.get('plan_share', 0) / LAW_PLAN_SHARE_FULL), 3),
                details.get('strictness'),
            ],
            'rules_mid': LAW_RULES_MID, 'plan_full': LAW_PLAN_SHARE_FULL, 'lawful_from': LAW_LAWFUL_FROM,
            'chaotic_upto': LAW_CHAOTIC_UPTO, 'good_from': MORAL_GOOD_FROM, 'evil_below': MORAL_EVIL_BELOW,
            'evil_weight': MORAL_EVIL_WEIGHT, 'strictness_of': PERMISSION_STRICTNESS,
        },
        'treasury': {
            'gold': {key: value for key, value in character['treasury']['gold'].items() if key != 'tier'},
            'camp': {key: value for key, value in character['treasury']['camp'].items() if key != 'tier'},
            'weights': GOLD_WEIGHTS,
        },
        'achievements': {
            item['key']: {
                'metric': words['ach_metrics'][item['key']][0], 'unit': words['ach_metrics'][item['key']][1],
                'value': item['value'], 'thresholds': item.get('thresholds'), 'value_tier': item.get('value_tier'),
                'tier': item['tier'], 'record_day': item.get('record_day'), 'earned_at': item.get('earned_at'),
            }
            for item in character['achievements'] if item['key'] in words['ach_metrics']
        },
        'rules': {
            'window_days': ATTR_WINDOW_DAYS, 'half_life': HALF_LIFE_DAYS, 'daily_cap': DAILY_SESSIONS_CAP,
            'hybrid_ratio': HYBRID_RATIO,
            'ranks': [list(row) for row in named(SKILL_RANKS, words['ranks'])],
            'rarities': [[threshold, words['rarities'][key]] for threshold, key in RARITIES],
            'aura_tiers': [list(row) for row in named(AURA_TIERS, words['aura_tiers'])],
            'xp': {
                'session': XP_SESSION_BASE, 'turn': XP_PER_HUMAN_TURN, 'turn_cap': XP_HUMAN_TURNS_CAP,
                'day': XP_PER_ACTIVE_DAY, 'level_base': LEVEL_BASE_XP, 'growth': LEVEL_GROWTH,
            },
        },
    }
