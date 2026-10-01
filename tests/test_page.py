"""The page: render, the archive, the game view, the insights layer and the chat card."""

import json
import os
import unittest
from datetime import timedelta

from harness_rpg.archive import refresh_texts
from harness_rpg.card import avatar_script, chat_card
from harness_rpg.catalog import classify
from harness_rpg.character import compute_character
from harness_rpg.constants import ACHIEVEMENTS, DATA_PLACEHOLDER
from harness_rpg.page import render, template_path, write_page
from harness_rpg.storage import catalog_path, history_path, load_catalog, load_json, save_json
from harness_rpg.texts import TEXTS
from harness_rpg.transcripts import update
from harness_rpg.views import game_view, public_view

from .support import NOW, UUID_SERVER, TranscriptsCase, tooling_words_in


class PageCase(TranscriptsCase):

    def test_page_replaces_leaking_cached_alias(self):
        ledger, _ = update(self.projects, self.home)
        save_json(catalog_path(self.home), {
            'skills': {'my-skill': {'school': 'smith', 'alias': 'Приём My-Skill'}},
            'mcp': {'notebook': {'alias': 'Шкатулка Notebook'}},
        })
        view = public_view(compute_character(ledger, load_catalog(self.home), NOW))
        payload = json.dumps(game_view(view), ensure_ascii=False)
        self.assertNotIn('My-Skill', payload)
        self.assertNotIn('Notebook', payload)
        self.assertIn(TEXTS['ru']['skill_fallback'], payload)
        self.assertIn(TEXTS['ru']['gear_fallback'], payload)

    def test_page_data_carries_no_markup(self):
        # '</script>' would end the script early, '<!--' with '<script' would keep its real end from ending it.
        history = [{'note': '<!-- <script> </script>'}]
        os.makedirs(self.home)
        with open(write_page(self.home, history), encoding='utf-8') as handle:
            page = handle.read()
        with open(template_path(), encoding='utf-8') as handle:
            head, tail = handle.read().split(DATA_PLACEHOLDER)
        payload = page[len(head):len(page) - len(tail)]
        self.assertNotIn('<', payload)
        self.assertEqual(json.loads(payload), history)

    def test_render_embeds_character(self):
        update(self.projects, self.home)
        classify(self.home, {'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Око дозора'}}})
        character, html_path, _ = render(self.home, now=NOW)
        with open(html_path, encoding='utf-8') as handle:
            html = handle.read()
        self.assertNotIn(DATA_PLACEHOLDER, html)
        self.assertIn('"Око дозора"', html)
        self.assertIn(f'"{TEXTS["ru"]["gear_fallback"]} 1"', html)
        self.assertEqual(character['stats']['sessions'], 1)
        self.assertEqual(character['level']['xp'], 10 + 2 * 3 + 20)
        self.assertEqual({item['name'] for item in character['gear']}, {'notebook', 'Acme-Ops'})
        self.assertEqual(len(character['attributes']), 6)

    def test_render_archives_snapshots(self):
        update(self.projects, self.home)
        render(self.home, now=NOW)
        _, _, history = render(self.home, now=NOW + timedelta(minutes=5))
        self.assertEqual(len(history), 1, 'a snapshot that differs only by time replaces the latest')
        self.assertEqual(history[0]['generated_at'], (NOW + timedelta(minutes=5)).astimezone().isoformat(timespec='seconds'))
        classify(self.home, {'mcp': {'notebook': {'alias': 'Шкатулка памяти'}}})
        _, html_path, history = render(self.home, now=NOW + timedelta(minutes=10))
        self.assertEqual(len(history), 2)
        aliases = [{item['alias'] for item in snapshot['gear']} for snapshot in history]
        self.assertNotIn('Шкатулка памяти', aliases[0])
        self.assertIn('Шкатулка памяти', aliases[1])
        self.assertEqual(load_json(history_path(self.home), None), history)
        with open(html_path, encoding='utf-8') as handle:
            html = handle.read()
        start = html.index('const H = ') + len('const H = ')
        self.assertEqual(json.loads(html[start:html.index(';\n', start)]), history)

    def test_game_view_has_no_real_names_or_usage_numbers(self):
        ledger, _ = update(self.projects, self.home)
        classify(self.home, {
            'skills': {'my-skill': {'school': 'ranger', 'alias': 'Охота на ошибки'}},
            'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Око дозора'}},
        })
        catalog = load_catalog(self.home)
        # Everything real lives under one key, shown only in the insights mode; the rest is the game view.
        view = game_view(public_view(compute_character(ledger, catalog, NOW)))
        payload = json.dumps(view, ensure_ascii=False)
        secrets = {entry.get('name') for entry in catalog['mcp'].values()} - {None}
        secrets |= {family['name'] for entry in catalog['mcp'].values() for family in (entry.get('families') or {}).values()}
        for session in ledger['sessions'].values():
            secrets.add(session['project'])
            secrets.update(session['tools'])
            for key, entry in session['skills'].items():
                secrets.update((key, entry['display']))
            for server, entry in session['mcp'].items():
                secrets.add(server)
                secrets.update(entry['tools'])
        leaked = sorted(secret for secret in secrets if secret in payload)
        self.assertEqual(leaked, [])

        def keys(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys(value)
            elif isinstance(node, list):
                for value in node:
                    yield from keys(value)

        forbidden = {
            'sessions', 'calls', 'last_day', 'top_tools', 'servers', 'details', 'score', 'weights', 'xp', 'stats',
            'units', 'count', 'tokens',
        }
        self.assertEqual(forbidden & set(keys(view)), set())
        self.assertEqual([group['name'] for group in view['skill_groups']], ['Следопыт', 'Без школы'])
        self.assertTrue(view['auras'])
        self.assertTrue(all(set(aura) == {'key', 'name', 'effect', 'tier', 'tier_name'} for aura in view['auras']))
        self.assertEqual(set(view['alignment']), {'law', 'moral', 'name', 'desc'})
        self.assertNotIn('secret-lint', payload)

    def test_insights_layer_explains_every_game_value(self):
        ledger, _ = update(self.projects, self.home)
        classify(self.home, {
            'skills': {'my-skill': {'school': 'ranger', 'alias': 'Охота на ошибки'}},
            'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Око дозора'}},
        })
        character = compute_character(ledger, load_catalog(self.home), NOW)
        view = public_view(character)
        insights = view['insights']
        self.assertEqual(insights['findings'], [])
        skill = insights['skills']['Охота на ошибки']
        self.assertEqual((skill['name'], skill['school'], skill['sessions'], skill['rank']), ('My_Skill', 'ranger', 1, 'Новичок'))
        self.assertEqual(skill['next'], {'name': 'Ученик', 'at': 2})
        item = insights['gear']['Око дозора']
        self.assertEqual((item['name'], item['tools'], item['rarity_at']), ('Acme-Ops', [['logs_search', 1]], 0))
        self.assertEqual(insights['auras']['temper']['hooks'], {'secret-lint.sh': 2})
        self.assertEqual(insights['auras']['temper']['events'], {'PostToolUse': 2})
        self.assertEqual(sum(insights['hero']['xp_parts'].values()), insights['hero']['xp'])
        # No comparison with the window before: cleanup has already removed most of it.
        self.assertNotIn('before', insights['hero']['stats'])
        self.assertEqual(set(insights['achievements']), set(dict(ACHIEVEMENTS)))
        self.assertEqual(insights['achievements']['phoenix']['value'], 1)
        self.assertEqual(set(insights['attributes']), {attr['key'] for attr in view['attributes']})
        self.assertTrue(all(attr['rule'] and attr['metrics'] for attr in insights['attributes'].values()))
        # Every alias the page draws has its details.
        skill_aliases = {skill['alias'] for group in view['skill_groups'] for skill in group['skills']}
        self.assertEqual(set(insights['skills']), skill_aliases)
        self.assertEqual(set(insights['gear']), {item['alias'] for item in view['gear']})

    def test_chat_card_shows_the_game_view_only(self):
        ledger, _ = update(self.projects, self.home)
        classify(self.home, {
            'skills': {'my-skill': {'school': 'ranger', 'alias': 'Охота на ошибки'}},
            'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Око дозора', 'slot': 'helmet'}},
        })
        render(self.home, now=NOW)
        with open(template_path(), encoding='utf-8') as handle:
            template = handle.read()
        card = chat_card(load_json(history_path(self.home), None)[-1], avatar_script(template))
        self.assertIn('Охота на ошибки', card)
        self.assertIn('Око дозора', card)
        # A JS string literal inside the attribute: a quote in the text can't break the call.
        self.assertIn('sendPrompt(&quot;Открой страницу героя&quot;)', card)
        self.assertIn('drawAvatar(document.getElementById', card)
        # The widget host forbids comments; the card carries no real names, tools, hooks or paths.
        self.assertNotIn('<!--', card)
        self.assertFalse(any(line.lstrip().startswith('//') for line in card.splitlines()))
        leaked = [secret for secret in ('My_Skill', 'my-skill', 'Acme-Ops', UUID_SERVER, 'notebook', 'secret-lint',
                                        'logs_search', '/work/repo') if secret in card]
        self.assertEqual(leaked, [])
        self.assertLess(len(card.encode('utf-8')), 20_000)


class ArchiveCase(unittest.TestCase):

    def test_archived_snapshot_gets_current_wording(self):
        old = {
            'generated_at': '2026-09-30T19:00:00+03:00',
            'hero': {'name': 'Claude Code'},
            'class': {'name': 'Чародей', 'primary': 'bard', 'secondary': 'summoner', 'basis': 'current',
                      'epithet': None, 'lore': 'заклинает словом: промпт — его заклинание, агенты — его свита'},
            'schools': [{'key': 'summoner', 'name': 'Призыватель', 'share': 1.0, 'lore': 'скилы харнесса',
                         'desc': 'ведёт свиту: агенты, оркестрация, автоматизация, настройка харнесса'}],
            'skill_groups': [{'key': 'summoner', 'name': 'Призыватель', 'desc': 'агенты харнесса', 'skills': []}],
            'achievements': [
                {'key': 'warlord', 'name': 'Полководец', 'tier': 2, 'earned': True,
                 'criteria': ['призвать 2 помощников-сабагентов в одной сессии'] * 3},
                {'key': 'flawless', 'name': 'Безупречный', 'earned': True, 'criteria': 'сессия без ошибки'},
            ],
        }
        fresh = refresh_texts(old)
        fresh.pop('hero')
        self.assertEqual(tooling_words_in(json.dumps(fresh, ensure_ascii=False)), [])
        self.assertEqual(fresh['class']['lore'], TEXTS['ru']['hybrids'][frozenset(('bard', 'summoner'))][1])
        self.assertEqual((fresh['class']['name'], fresh['class']['epithet']), ('Чародей', None))
        self.assertEqual(fresh['achievements'][0]['tier'], 2, 'medals stay as they were')
        self.assertEqual(old['schools'][0]['lore'], 'скилы харнесса', 'the original snapshot is not mutated')


if __name__ == '__main__':
    unittest.main()
