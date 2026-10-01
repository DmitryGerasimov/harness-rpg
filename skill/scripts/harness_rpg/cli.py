"""Command line of rpg.py."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import __version__
from .archive import refresh_texts
from .card import avatar_script, chat_card
from .catalog import classify, pending_items
from .constants import ATTR_WINDOW_DAYS, BAG, LANGS
from .insights import attach_findings, insight_digest, reality_digest
from .lang import lang_votes, page_lang
from .page import render, template_path
from .storage import catalog_path, claude_dir, history_path, ledger_path, load_catalog, load_json, rpg_home
from .texts import TEXTS
from .transcripts import update


def load_answer(path):
    """The agent's answer file as a JSON object; None, with the reason on stderr, when it is not one."""
    try:
        answer = load_json(path, None)
    except ValueError as error:
        print(f'not valid JSON: {path}: {error}', file=sys.stderr)
        return None
    if not isinstance(answer, dict):
        print(f'answer file not found or not a JSON object: {path}', file=sys.stderr)
        return None
    return answer


def cmd_update(args):
    """Update the ledger, print the page language and what still needs classification."""
    ledger, parsed = update(args.projects_dir, args.home)
    print(f'parsed sessions: {parsed}, sessions in ledger: {len(ledger["sessions"])}')
    print(f'ledger: {ledger_path(args.home)}')
    if not ledger['sessions']:
        # Even the running conversation has a transcript, so an empty ledger means the wrong folder.
        print(f'NO SESSIONS FOUND in {args.projects_dir}: point --projects-dir (or CLAUDE_CONFIG_DIR) '
              f'at the folder where Claude Code keeps its transcripts')
    lang = page_lang(args.home, ledger, args.lang)
    ru, other = lang_votes(ledger)
    print(f'language: {lang} (human messages: {ru} Russian, {other} other{"; set by --lang" if args.lang else ""})')
    pending = pending_items(ledger, load_catalog(args.home), lang)
    if not pending['skills'] and not pending['mcp']:
        print('classification: nothing pending')
        return 0
    words = TEXTS[lang]
    pending['lang'] = lang
    pending['schools'] = {key: f'{name}: {desc}' for key, (name, desc, _) in words['schools'].items()}
    pending['slots'] = {key: f'{name}: {desc}' for key, (name, desc) in words['slots'].items()}
    pending['slots'][BAG] = words['bag']
    alias = f'<fantasy alias in {"Russian" if lang == "ru" else "English"}>'
    pending['answer_format'] = {
        'skills': {'<name>': {'school': '<school key>', 'alias': alias}},
        'mcp': {'<one of servers>': {
            'name': '<real name, only when name is needed>', 'alias': alias, 'slot': '<slot key>',
            'families': {'<category>': {
                'name': '<real name of the category>', 'alias': alias, 'slot': '<slot key>',
                'prefixes': ['<tool family>', '...'],
            }},
        }},
    }
    print('PENDING CLASSIFICATION (answer with "rpg.py classify FILE"):')
    print(json.dumps(pending, ensure_ascii=False, indent=1))
    return 0


def cmd_classify(args):
    """Merge classification answers from a JSON file."""
    answers = load_answer(args.file)
    if answers is None:
        return 1
    errors = classify(args.home, answers, args.lang)
    for error in errors:
        print(f'error: {error}', file=sys.stderr)
    print(f'catalog: {catalog_path(args.home)}')
    return 1 if errors else 0


def cmd_render(args):
    """Render the character sheet and print a short summary."""
    character, html_path, history = render(args.home, lang=args.lang)
    level = character['level']
    words = TEXTS[character['lang']]
    print(f'language: {character["lang"]}')
    print(f'level {level["level"]} ({level["into"]}/{level["need"]} xp, total {level["xp"]})')
    print(f'class: {character["class"]["name"]}')
    for skill in character['skills'][:3]:
        alias = skill['alias'] or words['skill_fallback']
        print(f'skill: {alias} ({skill["name"]}) — {skill["rank_name"]} (peak {skill["peak_rank_name"]})')
    for item in character['gear']:
        alias = item['alias'] or words['gear_fallback']
        place = item['slot'] if item['equipped'] else BAG
        print(f'gear: {alias} ({item["name"]}) — {item["rarity_name"]}, affixes {item["affixes"]}, {place}')
    rusty = [skill['name'] for skill in character['skills'] if skill['rusty']]
    if rusty:
        print(f'rusty skills: {", ".join(rusty[:8])}')
    earned = [f'{item["name"]} ({item["tier_name"]})' for item in character['achievements'] if item['earned']]
    print(f'title: {character["title"] or "-"}; achievements: {", ".join(earned) or "-"}')
    alignment = character['alignment']
    print(f'alignment: {alignment["name"]} {json.dumps(alignment["details"], ensure_ascii=False)}')
    treasury = character['treasury']
    print(f'treasury: {treasury["gold"]["name"]} ({treasury["gold"]["units"] / 1e6:.1f}M gold over '
          f'{ATTR_WINDOW_DAYS} days); campfire: {treasury["camp"]["name"]} ({treasury["camp"]["count"]} compactions)')
    for aura in character['auras']:
        print(f'aura: {aura["name"]} — {aura["tier_name"]} (share {aura["share"]})')
    print(f'history: {len(history)} snapshots in {history_path(args.home)}')
    findings = history[-1]['insights']['findings']
    if findings:
        print(f'insights: {len(findings)} findings kept from the same hero')
    else:
        print('INSIGHTS PENDING: read "rpg.py digest", write findings, attach them with "rpg.py insights FILE"')
    print(f'html: {html_path}')
    return 0


def cmd_card(args):
    """Print the chat card of the latest hero."""
    history = load_json(history_path(args.home), [])
    if not history:
        raise SystemExit('no hero yet: run "rpg.py render" first')
    with open(template_path(), encoding='utf-8') as handle:
        template = handle.read()
    print(chat_card(refresh_texts(history[-1], history[-1].get('lang', 'ru')), avatar_script(template)))
    return 0


def cmd_digest(args):
    """Print the compact stats of the latest snapshot for finding insights."""
    ledger = load_json(ledger_path(args.home), None)
    if ledger is None:
        raise SystemExit('ledger not found: run "rpg.py update" first')
    reality = reality_digest(ledger, load_catalog(args.home), datetime.now(timezone.utc))
    digest = insight_digest(load_json(history_path(args.home), []), reality)
    digest['answer_format'] = {
        'about': 'the real work behind the hero and what to change in using Claude Code, not ranks or medals',
        'findings': [{'title': '<short headline>', 'text': '<1-3 sentences: a fact with numbers from the digest, '
                      'what it means, what to change in Claude Code>', 'tone': '<rise | fall | note>'}],
    }
    print(json.dumps(digest, ensure_ascii=False, separators=(',', ':')))
    return 0


def cmd_insights(args):
    """Attach the agent's findings to the latest snapshot."""
    answer = load_answer(args.file)
    if answer is None:
        return 1
    errors, html_path = attach_findings(args.home, answer)
    for error in errors:
        print(f'error: {error}', file=sys.stderr)
    if errors:
        return 1
    print(f'insights: {len(answer["findings"])} findings attached')
    print(f'html: {html_path}')
    return 0


def main(argv=None):
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Claude Code harness as an RPG character.')
    parser.add_argument('--version', action='version', version=f'harness-rpg {__version__}')
    parser.add_argument('--home', default=rpg_home(), help='data directory (default ~/.harness-rpg)')
    parser.add_argument(
        '--projects-dir',
        default=os.path.join(claude_dir(), 'projects'),
        help='Claude Code transcripts directory',
    )
    # The page language follows the human; --lang or HARNESS_RPG_LANG overrides it for update, classify and render.
    language = argparse.ArgumentParser(add_help=False)
    env_lang = os.environ.get('HARNESS_RPG_LANG')
    language.add_argument(
        '--lang', choices=LANGS, default=env_lang if env_lang in LANGS else None,
        help='page language instead of the one the human mostly writes in (default: HARNESS_RPG_LANG)',
    )
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('update', parents=[language], help='parse transcripts into the ledger').set_defaults(
        func=cmd_update)
    classify_parser = commands.add_parser('classify', parents=[language], help='merge classification answers')
    classify_parser.add_argument('file')
    classify_parser.set_defaults(func=cmd_classify)
    commands.add_parser('render', parents=[language], help='write character.json and character.html').set_defaults(
        func=cmd_render)
    commands.add_parser('digest', help='print stats of the latest snapshot for insights').set_defaults(func=cmd_digest)
    commands.add_parser('card', help='print a compact chat card of the latest hero').set_defaults(func=cmd_card)
    insights_parser = commands.add_parser('insights', help='attach findings to the latest snapshot')
    insights_parser.add_argument('file')
    insights_parser.set_defaults(func=cmd_insights)
    args = parser.parse_args(argv)
    return args.func(args)
