"""Skills and the class: ranks from decayed usage, the class from the leading schools."""

from collections import Counter, defaultdict

from .constants import HYBRID_RATIO, RUSTED_CLASS_THRESHOLD, SCHOOLS, SKILL_RANKS
from .names import alias_field
from .scoring import next_step, threshold_index, usage_details, usage_profile
from .texts import TEXTS, named


def pick_class(weights, lang='ru'):
    """Pure class from the top school, hybrid when the second one is close."""
    words = TEXTS[lang]
    ranked = [(key, weight) for key, weight in sorted(weights.items(), key=lambda kv: (-kv[1], kv[0])) if weight > 0]
    if not ranked:
        name, lore = words['no_class']
        return {'name': name, 'primary': None, 'secondary': None, 'epithet': None, 'lore': lore}
    primary, top = ranked[0]
    if len(ranked) > 1 and ranked[1][1] >= HYBRID_RATIO * top:
        secondary = ranked[1][0]
        name, lore = words['hybrids'][frozenset((primary, secondary))]
        return {'name': name, 'primary': primary, 'secondary': secondary, 'epithet': None, 'lore': lore}
    name, desc, _ = words['schools'][primary]
    return {'name': name, 'primary': primary, 'secondary': None, 'epithet': words['epithets'][primary], 'lore': desc}


def build_skills(sessions, catalog, today, lang='ru'):
    """Skill list with current and peak ranks."""
    ranks = named(SKILL_RANKS, TEXTS[lang]['ranks'])
    days = defaultdict(Counter)
    calls = Counter()
    sessions_count = Counter()
    last_day = {}
    displays = defaultdict(Counter)
    for session in sessions:
        for key, entry in session['skills'].items():
            if not entry.get('day'):
                continue
            days[key][entry['day']] += 1
            calls[key] += entry['n']
            sessions_count[key] += 1
            last_day[key] = max(last_day.get(key, ''), entry['day'])
            displays[key][entry['display']] += 1
    skills = []
    for key, day_sessions in days.items():
        current, peak = usage_profile(day_sessions, today)
        rank = threshold_index(current, ranks)
        peak_rank = threshold_index(peak, ranks)
        cached = catalog['skills'].get(key) or {}
        skills.append({
            'key': key,
            'name': displays[key].most_common(1)[0][0],
            'alias': cached.get(alias_field(lang)),
            'school': cached.get('school'),
            'sessions': sessions_count[key],
            'calls': calls[key],
            'last_day': last_day[key],
            'score': round(current, 2),
            'peak_score': round(peak, 2),
            'rank': rank,
            'rank_name': ranks[rank][1],
            'peak_rank': peak_rank,
            'peak_rank_name': ranks[peak_rank][1],
            'rusty': rank < peak_rank,
            'next_rank': next_step(current, ranks),
            **usage_details(day_sessions, today),
        })
    skills.sort(key=lambda skill: (-skill['score'], -skill['peak_score'], skill['name']))
    return skills


def build_class(skills, lang='ru'):
    """Class from school weights; falls back to peak scores when everything rusted."""
    weights = Counter()
    for skill in skills:
        if skill['school'] in SCHOOLS:
            weights[skill['school']] += skill['score']
    basis = 'current'
    if not weights or max(weights.values()) < RUSTED_CLASS_THRESHOLD:
        weights = Counter()
        for skill in skills:
            if skill['school'] in SCHOOLS:
                weights[skill['school']] += skill['peak_score']
        basis = 'peak'
    hero_class = pick_class(weights, lang)
    hero_class['basis'] = basis
    hero_class['weights'] = {key: round(weights.get(key, 0.0), 2) for key in SCHOOLS}
    return hero_class
