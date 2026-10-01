"""Archive of snapshots: old snapshots reworded into the page language, an equal snapshot replaced."""

import json

from .constants import ACHIEVEMENTS, AURA_TIERS, LANGS, LEGACY_ACH_THRESHOLDS, RARITIES, ROMAN, SCHOOLS
from .skills import pick_class
from .texts import TEXTS, achievement_criteria, localized, school_texts
from .treasury import treasury_steps
from .views import game_view


def name_index(name, field):
    """Position of a name in a list of names of any language (ranks, tiers), or None."""
    for lang in LANGS:
        if name in TEXTS[lang][field]:
            return TEXTS[lang][field].index(name)
    return None


def word_key(name, field):
    """Key of a name in a keyed table of any language (rarities, achievements), or None."""
    for lang in LANGS:
        for key, value in TEXTS[lang][field].items():
            if (value[0] if isinstance(value, tuple) else value) == name:
                return key
    return None


def tier_name(name, field, lang, index=None):
    """A tier name in another language, the roman level of an open top kept: Драконья казна II -> Dragon's hoard II."""
    base, _, level = (name or '').rpartition(' ')
    if not base or not (level in ROMAN or level.isdigit()):
        base, level = name, ''
    if index is None:
        index = name_index(base, field)
    names = TEXTS[lang][field]
    if not isinstance(index, int) or not 0 <= index < len(names):
        return name
    return f'{names[index]} {level}' if level else names[index]


def refresh_texts(snapshot, lang=None):
    """Today's wording for an archived snapshot, in the page language.

    Labels, descriptions, rules and the names of ranks, tiers, classes and medals are not the hero's data: old
    snapshots get the current vocabulary of the page language, rebuilt from their keys, and only in the fields they
    already have. Values, ranks, medals and the class itself stay exactly as they were; aliases, findings and the
    values of the attribute metrics keep the language they were written in.
    """
    snapshot = json.loads(json.dumps(snapshot))
    lang = lang or snapshot.get('lang') or 'ru'
    words = TEXTS[lang]
    for school in snapshot.get('schools') or []:
        if school.get('key') in SCHOOLS:
            name, desc, lore = words['schools'][school['key']]
            school['name'], school['desc'] = name, desc
            if 'lore' in school:
                school['lore'] = lore
    for group in snapshot.get('skill_groups') or []:
        if 'key' in group and (group['key'] in SCHOOLS or group['key'] is None):
            group['name'], group['desc'] = school_texts(group['key'], lang)
        for skill in group.get('skills') or []:
            for index_field, name_field in (('rank', 'rank_name'), ('peak_rank', 'peak_rank_name')):
                index = skill.get(index_field)
                if name_field in skill and isinstance(index, int) and 0 <= index < len(words['ranks']):
                    skill[name_field] = words['ranks'][index]
    hero_class = snapshot.get('class') or {}
    if 'name' in hero_class:
        # Equal weights rebuild the same class: one school gives the pure class, two give their hybrid.
        schools = [key for key in (hero_class.get('primary'), hero_class.get('secondary')) if key in SCHOOLS]
        texts = pick_class({key: 1.0 for key in schools}, lang)
        hero_class['name'] = texts['name']
        if 'lore' in hero_class:
            hero_class['epithet'], hero_class['lore'] = texts['epithet'], texts['lore']
    thresholds = dict(ACHIEVEMENTS)
    for item in snapshot.get('achievements') or []:
        key = item.get('key')
        if key not in thresholds:
            continue
        name, template, forms = words['achievements'][key]
        item['name'] = name
        if isinstance(item.get('criteria'), list):
            item['criteria'] = [achievement_criteria(template, forms, threshold, lang) for threshold in thresholds[key]]
        else:
            legacy = LEGACY_ACH_THRESHOLDS.get(key, thresholds[key][0])
            item['criteria'] = achievement_criteria(template, forms, legacy, lang)
        if 'tier_name' in item:
            tier = item.get('tier')
            item['tier_name'] = words['medals'][tier] if isinstance(tier, int) and tier >= 0 else None
    if snapshot.get('title'):
        key = snapshot.get('title_key') or word_key(snapshot['title'], 'achievements')
        if key in thresholds:
            snapshot['title'] = words['achievements'][key][0]
    for aura in snapshot.get('auras') or []:
        if aura.get('key') not in words['auras']:
            continue
        name, effect = words['auras'][aura['key']]
        for field, value in (('name', name), ('effect', effect)):
            if field in aura:
                aura[field] = value
        tier = aura.get('tier')
        if 'tier_name' in aura and isinstance(tier, int):
            aura['tier_name'] = words['aura_tiers'][tier] if 0 <= tier < len(AURA_TIERS) else words['aura_dormant']
    for cell in [snapshot.get('alignment') or {}] + list(snapshot.get('alignment_grid') or []):
        pair = (cell.get('law'), cell.get('moral'))
        if pair in words['alignments']:
            for field, value in zip(('name', 'desc'), words['alignments'][pair]):
                if field in cell:
                    cell[field] = value
    treasury = snapshot.get('treasury') or {}
    for part, field in (('gold', 'gold_tiers'), ('camp', 'camp_tiers')):
        item = treasury.get(part)
        if isinstance(item, dict) and item.get('name'):
            item['name'] = tier_name(item['name'], field, lang, item.get('tier'))
        if field in treasury:
            treasury[field] = list(words[field])
    for field, value in treasury_steps(lang).items():
        if field in treasury:
            treasury[field] = value
    for attr in snapshot.get('attributes') or []:
        if attr.get('key') in words['attributes']:
            for field, value in zip(('abbr', 'name', 'desc'), words['attributes'][attr['key']]):
                if field in attr:
                    attr[field] = value
    for slot in snapshot.get('slots') or []:
        if isinstance(slot, dict) and slot.get('key') in words['slots']:
            slot['name'], slot['desc'] = words['slots'][slot['key']]
    if isinstance(snapshot.get('ranks'), list) and len(snapshot['ranks']) == len(words['ranks']):
        snapshot['ranks'] = list(words['ranks'])
    for rarity in snapshot.get('rarities') or []:
        if isinstance(rarity, dict) and rarity.get('key') in words['rarities']:
            rarity['name'] = words['rarities'][rarity['key']]
    for item in snapshot.get('gear') or []:
        for key_field, name_field in (('rarity', 'rarity_name'), ('peak_rarity', 'peak_rarity_name')):
            if name_field in item and item.get(key_field) in words['rarities']:
                item[name_field] = words['rarities'][item[key_field]]
    if isinstance(snapshot.get('insights'), dict):
        refresh_insights(snapshot['insights'], lang)
    snapshot['lang'] = lang
    return snapshot


def refresh_insights(insights, lang):
    """The insights layer's share of refresh_texts: names of ranks and tiers, rules and the labels of metrics."""
    words = TEXTS[lang]

    def rank(name):
        index = name_index(name, 'ranks')
        return name if index is None else words['ranks'][index]

    def rarity(name):
        key = word_key(name, 'rarities')
        return words['rarities'][key] if key else name

    def rename(step, how):
        if isinstance(step, dict) and step.get('name'):
            step['name'] = how(step['name'])

    for item in (insights.get('skills') or {}).values():
        for field in ('rank', 'peak_rank'):
            if item.get(field):
                item[field] = rank(item[field])
        rename(item.get('next'), rank)
    for item in (insights.get('gear') or {}).values():
        for field in ('rarity', 'peak_rarity'):
            if item.get(field):
                item[field] = rarity(item[field])
        rename(item.get('next'), rarity)
    for aura in (insights.get('auras') or {}).values():
        rename(aura.get('next_tier'), lambda name: tier_name(name, 'aura_tiers', lang))
    treasury = insights.get('treasury') or {}
    for part, field in (('gold', 'gold_tiers'), ('camp', 'camp_tiers')):
        item = treasury.get(part)
        if isinstance(item, dict):
            rename(item, lambda name: tier_name(name, field, lang))
            rename(item.get('next'), lambda name: tier_name(name, field, lang))
    for key, item in (insights.get('achievements') or {}).items():
        if key in words['ach_metrics'] and 'metric' in item:
            item['metric'], item['unit'] = words['ach_metrics'][key]
    for key, item in (insights.get('attributes') or {}).items():
        if key not in words['attributes']:
            continue
        _, _, _, rule, labels = words['attributes'][key]
        if 'rule' in item:
            item['rule'] = localized(rule, lang)
        metrics = item.get('metrics')
        if isinstance(metrics, list) and len(metrics) == len(labels):
            for metric, label in zip(metrics, labels):
                metric['label'] = label
    rules = insights.get('rules') or {}
    names = {
        'ranks': words['ranks'], 'aura_tiers': words['aura_tiers'],
        'rarities': [words['rarities'][key] for _, key in RARITIES],
    }
    for field, row_names in names.items():
        rows = rules.get(field)
        if isinstance(rows, list) and len(rows) == len(row_names):
            for row, name in zip(rows, row_names):
                row[1] = name


def archive_snapshot(history, snapshot):
    """Append a snapshot; one whose game part differs from the latest only by time replaces it.

    The replaced snapshot's findings carry over: the hero did not change, so what was found about it holds.
    """
    def content(item):
        return {key: value for key, value in game_view(item).items() if key != 'generated_at'}

    if history and content(history[-1]) == content(snapshot):
        findings = (history[-1].get('insights') or {}).get('findings')
        if findings and 'insights' in snapshot and not snapshot['insights'].get('findings'):
            snapshot['insights']['findings'] = findings
        return history[:-1] + [snapshot]
    return history + [snapshot]
