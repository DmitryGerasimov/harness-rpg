"""Classification support: what the agent still has to classify, and its answers merged into the catalog."""

import glob
import os
import re
from collections import Counter, defaultdict

from .constants import BAG, LANGS, RECHECKED_SCHOOLS, SCHOOLS, SCHOOL_RULES_VERSION, SLOT_KEYS
from .lang import detect_lang, lang_votes, page_lang
from .names import (
    alias_field, alias_problem, auto_mcp_name, family_of, mcp_families, mcp_field, normalize_skill, resolve_mcp,
    server_prefixes, tool_family,
)
from .storage import catalog_path, claude_dir, ledger_path, load_catalog, load_json, save_json


def read_frontmatter(path):
    """Minimal YAML frontmatter reader for SKILL.md: top-level scalar fields only."""
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            text = handle.read(12000)
    except OSError:
        return {}
    if not text.startswith('---'):
        return {}
    end = text.find('\n---', 3)
    if end < 0:
        return {}
    fields = {}
    current = None
    for line in text[3:end].splitlines():
        match = re.match(r'^([A-Za-z_-]+):\s*(.*)$', line)
        if match:
            current = match.group(1)
            value = match.group(2).strip()
            fields[current] = '' if value in ('|', '>', '|-', '>-') else value.strip('"\'')
        elif current and line[:1] in (' ', '\t'):
            fields[current] = (fields[current] + ' ' + line.strip()).strip()
    return fields


def skill_descriptions(project_dirs):
    """Map canonical skill key -> description from installed SKILL.md files."""
    roots = [os.path.join(claude_dir(), 'skills'), os.path.join(claude_dir(), 'plugins')]
    roots += [os.path.join(project, '.claude', 'skills') for project in project_dirs]
    descriptions = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path in sorted(glob.glob(os.path.join(root, '**', 'SKILL.md'), recursive=True)):
            fields = read_frontmatter(path)
            key = normalize_skill(fields.get('name') or os.path.basename(os.path.dirname(path)))[0]
            if key and fields.get('description'):
                descriptions.setdefault(key, fields['description'][:200])
    return descriptions


def pending_items(ledger, catalog, lang=None):
    """Skills without a school or alias, MCP items without a readable name or alias, in the page language."""
    lang = lang or detect_lang(*lang_votes(ledger))
    alias_key = alias_field(lang)
    skill_sessions = Counter()
    displays = {}
    groups = {}
    for session in ledger['sessions'].values():
        for key, entry in session['skills'].items():
            skill_sessions[key] += 1
            displays.setdefault(key, entry['display'])
        counted = set()
        for server, entry in session['mcp'].items():
            name, known = resolve_mcp(server, catalog)
            if name is None:
                continue
            group_key = name.lower()
            group = groups.setdefault(group_key, {
                'name': name if known else None, 'servers': set(), 'sessions': 0, 'tools': Counter(),
            })
            group['servers'].add(server)
            group['tools'].update(entry['tools'])
            if group_key not in counted:
                counted.add(group_key)
                group['sessions'] += 1
    skills = []
    for key, count in skill_sessions.most_common():
        entry = catalog['skills'].get(key) or {}
        need = [field for field in ('school', 'alias') if not entry.get(alias_key if field == 'alias' else field)]
        outdated = entry.get('school_rules', 1) < SCHOOL_RULES_VERSION
        if entry.get('school') in RECHECKED_SCHOOLS and outdated:
            need.insert(0, 'school')
        if need:
            skills.append({
                'name': key, 'display': displays[key], 'sessions': count,
                'school': entry.get('school'), 'need': need,
            })
    if skills:
        projects = {session['project'] for session in ledger['sessions'].values() if session.get('project')}
        descriptions = skill_descriptions(sorted(p for p in projects if os.path.isdir(p)))
        for item in skills:
            item['description'] = descriptions.get(item['name'], '')
    mcp = []
    for group in sorted(groups.values(), key=lambda g: -g['sessions']):
        prefixes = defaultdict(Counter)
        for tool, calls in group['tools'].items():
            prefixes[tool_family(tool)][tool] = calls
        families = mcp_families(group['name'], catalog) if group['name'] else {}
        need = [] if group['name'] else ['name']
        if families:
            # A split server is nothing but its categories: a tool family outside all of them needs one, and so
            # does a category without an alias in the page language.
            if (any(family_of(families, tool) is None for tool in group['tools'])
                    or any(not family.get(alias_key) for family in families.values())):
                need.append('split')
        else:
            need += [field for field in ('alias', 'slot')
                     if not mcp_field(group['servers'], catalog, alias_key if field == 'alias' else field)]
            # Several tool families of two or more tools each may be different items in one server.
            wide = sum(len(tools) >= 2 for tools in prefixes.values())
            if wide >= 2 and not mcp_field(group['servers'], catalog, 'split_checked'):
                need.append('split')
        if need:
            item = {
                'servers': sorted(group['servers']), 'name': group['name'], 'sessions': group['sessions'],
                'need': need, 'sample_tools': [tool for tool, _ in group['tools'].most_common(8)],
            }
            if 'split' in need:
                item['families'] = {
                    prefix: [tool for tool, _ in tools.most_common(4)] for prefix, tools in sorted(prefixes.items())
                }
                if families:
                    item['current_families'] = families
            mcp.append(item)
    return {'skills': skills, 'mcp': mcp}


def classify(home, answers, lang=None):
    """Merge agent answers into the catalog and return errors.

    skills: {name: school | {'school': ..., 'alias': ...}}
    mcp: {server: name | {'name': ..., 'alias': ..., 'slot': <GEAR_SLOTS key or 'bag'>, 'families': ...}
          | null (not gear)}
    Fields that are not given keep their cached values. An alias is in the page language and lands in its field.
    """
    catalog = load_catalog(home)
    ledger = load_json(ledger_path(home), {})
    lang = lang or page_lang(home, ledger)
    alias_key = alias_field(lang)
    errors = []
    for name, answer in (answers.get('skills') or {}).items():
        key = normalize_skill(name)[0]
        answer = {'school': answer} if isinstance(answer, str) else answer
        if not key or not isinstance(answer, dict):
            errors.append(f'bad answer for skill {name!r}')
            continue
        school = answer.get('school')
        if school is not None and school not in SCHOOLS:
            errors.append(f'unknown school {school!r} for skill {name!r}')
            continue
        entry = dict(catalog['skills'].get(key) or {})
        if school:
            entry['school'] = school
            entry['school_rules'] = SCHOOL_RULES_VERSION
        if answer.get('alias'):
            alias = str(answer['alias']).strip()
            problem = alias_problem(alias, (name, key), lang)
            if problem:
                errors.append(f'alias {alias!r} for skill {name!r} rejected: {problem}')
            else:
                entry[alias_key] = alias
        catalog['skills'][key] = entry
    for server, answer in (answers.get('mcp') or {}).items():
        if not answer:
            catalog['mcp'][server] = {'ignore': True}
            continue
        answer = {'name': answer} if isinstance(answer, str) else answer
        if not isinstance(answer, dict):
            errors.append(f'bad answer for MCP {server!r}')
            continue
        entry = {key: value for key, value in (catalog['mcp'].get(server) or {}).items() if key != 'ignore'}
        if answer.get('name'):
            entry['name'] = str(answer['name']).strip()
        slot = answer.get('slot')
        if slot is not None:
            if slot in SLOT_KEYS or slot == BAG:
                entry['slot'] = slot
            else:
                errors.append(f'unknown slot {slot!r} for MCP {server!r}')
        if answer.get('alias'):
            alias = str(answer['alias']).strip()
            problem = alias_problem(alias, (server, entry.get('name'), auto_mcp_name(server)), lang)
            if problem:
                errors.append(f'alias {alias!r} for MCP {server!r} rejected: {problem}')
            else:
                entry[alias_key] = alias
        catalog['mcp'][server] = entry
        if answer.get('families') is not None:
            name = resolve_mcp(server, catalog)[0] or server
            seen = server_prefixes(ledger, name, catalog)
            families, family_errors = parse_families(
                server, entry, answer['families'], seen, lang, mcp_families(name, catalog),
            )
            errors += family_errors
            if not family_errors:
                entry['families'] = families
                entry['split_checked'] = True
                # One server, one split: another id of the same server must not keep an older one.
                for other, other_entry in catalog['mcp'].items():
                    if other != server and (resolve_mcp(other, catalog)[0] or '').lower() == name.lower():
                        other_entry.pop('families', None)
                        other_entry['split_checked'] = True
    save_json(catalog_path(home), catalog)
    return errors


def parse_families(server, entry, answer, seen=(), lang='ru', previous=None):
    """Validate a split into categories: {key: {'name', alias field, 'slot', 'prefixes'}}; {} means no split.

    A split server is nothing but its categories, so every tool family seen for it has to land in exactly
    one of them. A category without 'prefixes' covers the tool family named by its key. The answer's alias is
    in the page language; the aliases of the other languages carry over from the previous category of the same key.
    """
    if not isinstance(answer, dict):
        return {}, [f'families for MCP {server!r} must be an object']
    families = {}
    errors = []
    owners = {}
    names = set()
    for key, family in answer.items():
        if not isinstance(family, dict) or not family.get('name') or not family.get('alias'):
            errors.append(f'family {key!r} of MCP {server!r} needs a name and an alias')
            continue
        slot = family.get('slot', BAG)
        if slot not in SLOT_KEYS and slot != BAG:
            errors.append(f'unknown slot {slot!r} for family {key!r} of MCP {server!r}')
            continue
        prefixes = family.get('prefixes') or [key]
        if not isinstance(prefixes, list) or not all(isinstance(prefix, str) and prefix for prefix in prefixes):
            errors.append(f'prefixes of family {key!r} of MCP {server!r} must be a list of tool families')
            continue
        taken = sorted(prefix for prefix in prefixes if prefix in owners)
        if taken:
            errors.append(f'tool families {taken} of MCP {server!r} are in {key!r} and in another category')
            continue
        name = str(family['name']).strip()
        if name.lower() in names:
            errors.append(f'family {key!r} of MCP {server!r} repeats the name {name!r}')
            continue
        alias = str(family['alias']).strip()
        problem = alias_problem(
            alias, (server, key, *prefixes, name, entry.get('name'), auto_mcp_name(server)), lang,
        )
        if problem:
            errors.append(f'alias {alias!r} for family {key!r} of MCP {server!r} rejected: {problem}')
            continue
        owners.update(dict.fromkeys(prefixes, key))
        names.add(name.lower())
        kept = {
            alias_field(other): (previous or {}).get(key, {}).get(alias_field(other))
            for other in LANGS if other != lang
        }
        families[key] = {
            'name': name, alias_field(lang): alias, 'slot': slot, 'prefixes': sorted(prefixes),
            **{field: value for field, value in kept.items() if value},
        }
    missing = sorted(set(seen) - set(owners))
    if families and missing and not errors:
        errors.append(
            f'tool families {missing} of MCP {server!r} are in no category: a split server has no catch-all item',
        )
    return families, errors
