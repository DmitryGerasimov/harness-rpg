"""Treasury and campfires: price-weighted tokens as gold, compactions as halts; the open top tiers."""

from datetime import timedelta

from .constants import ATTR_WINDOW_DAYS, CAMP_OPEN_FACTOR, CAMP_TIERS, GOLD_OPEN_FACTOR, GOLD_TIERS, GOLD_WEIGHTS, ROMAN
from .scoring import next_step, recent_sessions, threshold_index
from .stats import place_name
from .texts import TEXTS, named, plural
from .transcripts import local_day, parse_ts


def gold_of(session):
    """Price-weighted tokens of one session, subagents included."""
    tokens = session.get('tokens') or {}
    return sum(weight * tokens.get(name, 0) for name, weight in GOLD_WEIGHTS.items())


def build_treasury(sessions, now, lang='ru'):
    """Gold and campfire tiers over the recent window."""
    cutoff = now - timedelta(days=ATTR_WINDOW_DAYS)
    # Gold is spent in every session of the window, automated ones too.
    spending = [session for session in sessions if parse_ts(session['end']) >= cutoff]
    gold = sum(gold_of(session) for session in spending)
    tokens = {name: sum((session.get('tokens') or {}).get(name, 0) for session in spending) for name in GOLD_WEIGHTS}
    dearest = sorted(spending, key=gold_of, reverse=True)[:3]
    camping = [session['counts']['compactions'] for session in recent_sessions(sessions, now)]
    camps = sum(camping)
    gold_tiers = named(GOLD_TIERS, TEXTS[lang]['gold_tiers'])
    camp_tiers = named(CAMP_TIERS, TEXTS[lang]['camp_tiers'])
    gold_tier, gold_name = open_tier(gold, gold_tiers, GOLD_OPEN_FACTOR)
    camp_tier, camp_name = open_tier(camps, camp_tiers, CAMP_OPEN_FACTOR)
    return {
        'gold': {
            'units': round(gold), 'tier': gold_tier, 'name': gold_name, 'tokens': tokens,
            'sessions': len(spending), 'next': open_next(gold, gold_tiers, GOLD_OPEN_FACTOR),
            'dearest': [
                {'day': local_day(parse_ts(session['start'])), 'place': place_name(session.get('project')),
                 'units': round(gold_of(session)), 'tokens': sum((session.get('tokens') or {}).values()),
                 'cache_read': (session.get('tokens') or {}).get('cache_read', 0)}
                for session in dearest
            ],
        },
        'camp': {
            'count': camps, 'tier': camp_tier, 'name': camp_name,
            'next': open_next(camps, camp_tiers, CAMP_OPEN_FACTOR),
            'sessions': sum(1 for count in camping if count), 'max': max(camping, default=0),
        },
    }


def gold_amount(value, lang='ru'):
    """Human-readable gold amount: 2 млн, 1 млрд or 2M, 1B."""
    millions, billions = TEXTS[lang]['millions']
    return billions.format(value / 1e9) if value >= 1e9 else millions.format(value / 1e6)


def treasury_steps(lang='ru'):
    """Rules of both scales for the page tooltip: tier names with their thresholds, and the open top."""
    words = TEXTS[lang]
    rules = words['treasury']
    gold = [
        {'name': name, 'from': (rules['gold_from'].format(amount=gold_amount(threshold, lang)) if threshold
                                else rules['gold_below'].format(amount=gold_amount(GOLD_TIERS[1], lang)))}
        for threshold, name in named(GOLD_TIERS, words['gold_tiers'])
    ]
    camp = [
        {'name': name, 'from': (
            rules['camp_from'].format(n=threshold, noun=plural(lang, threshold, rules['camp_forms']))
            if threshold else rules['camp_none']
        )}
        for threshold, name in named(CAMP_TIERS, words['camp_tiers'])
    ]

    def times(factor):
        return rules['times'].get(factor) or rules['times_n'].format(n=factor)

    return {
        'gold_steps': gold,
        'gold_open': rules['gold_open'].format(name=words['gold_tiers'][-1], times=times(GOLD_OPEN_FACTOR)),
        'camp_steps': camp,
        'camp_open': rules['camp_open'].format(name=words['camp_tiers'][-1], times=times(CAMP_OPEN_FACTOR)),
    }


def open_tier(value, tiers, factor):
    """Tier index and name; past the last tier every ×factor adds a roman level to its name."""
    index = threshold_index(value, tiers)
    name = tiers[index][1]
    top = tiers[-1][0]
    if index == len(tiers) - 1 and top > 0:
        level = 1
        while value >= top * factor ** level:
            level += 1
        if level > 1:
            name = f'{name} {ROMAN[level - 1] if level <= len(ROMAN) else level}'
    return index, name


def open_next(value, tiers, factor):
    """The next tier above the value as {'name', 'at'}; past the last tier, the next roman level."""
    step = next_step(value, tiers)
    top = tiers[-1][0]
    if step or top <= 0:
        return step
    level = 1
    while value >= top * factor ** level:
        level += 1
    return {'name': f'{tiers[-1][1]} {ROMAN[level] if level < len(ROMAN) else level + 1}', 'at': top * factor ** level}
