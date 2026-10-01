"""Gear: MCP servers and their categories as items in slots, rarity from decayed usage."""

from collections import Counter

from .constants import RARITIES, SLOT_KEYS
from .names import alias_field, gear_parts, mcp_alias, mcp_field
from .scoring import next_step, threshold_index, usage_details, usage_profile
from .texts import TEXTS, named


def build_gear(sessions, catalog, today, lang='ru'):
    """MCP servers (or their carved tool families) as items: rarity from usage, affixes from distinct tools."""
    names = TEXTS[lang]['rarities']
    rarities = named([threshold for threshold, _ in RARITIES], [names[key] for _, key in RARITIES])
    groups = {}
    for session in sessions:
        counted = set()
        for server, entry in session['mcp'].items():
            if not entry.get('day'):
                continue
            for group_key, part in gear_parts(server, entry, catalog).items():
                group = groups.setdefault(group_key, {
                    'name': part['name'], 'known': part['known'], 'family': part['family'], 'servers': set(),
                    'days': Counter(), 'tools': Counter(), 'calls': 0, 'sessions': 0, 'last_day': '',
                })
                group['servers'].add(server)
                group['tools'].update(part['tools'])
                group['calls'] += sum(part['tools'].values())
                group['last_day'] = max(group['last_day'], entry['day'])
                if group_key not in counted:
                    counted.add(group_key)
                    group['days'][entry['day']] += 1
                    group['sessions'] += 1
    gear = []
    for group in groups.values():
        current, peak = usage_profile(group['days'], today)
        rarity = threshold_index(current, rarities)
        peak_rarity = threshold_index(peak, rarities)
        family = group['family']
        gear.append({
            'name': group['name'],
            'alias': family.get(alias_field(lang)) if family else mcp_alias(group['servers'], catalog, lang),
            'known': group['known'],
            'servers': sorted(group['servers']),
            'sessions': group['sessions'],
            'calls': group['calls'],
            'last_day': group['last_day'],
            'score': round(current, 2),
            'peak_score': round(peak, 2),
            'rarity': RARITIES[rarity][1],
            'rarity_name': rarities[rarity][1],
            'peak_rarity': RARITIES[peak_rarity][1],
            'peak_rarity_name': rarities[peak_rarity][1],
            'affixes': len(group['tools']),
            'tools': [{'name': tool, 'calls': count} for tool, count in group['tools'].most_common()],
            'slot': family.get('slot') if family else mcp_field(group['servers'], catalog, 'slot'),
            'next_rarity': next_step(current, rarities),
            **usage_details(group['days'], today),
        })
    gear.sort(key=lambda item: (-item['score'], -item['peak_score'], item['name'].lower()))
    # The strongest item of each slot is worn; everything else rides in the bag.
    worn = {}
    for item in gear:
        item['equipped'] = item['slot'] in SLOT_KEYS and item['slot'] not in worn
        if item['equipped']:
            worn[item['slot']] = item['name']
        item['worn_instead'] = None if item['equipped'] else worn.get(item['slot'])
    return gear
