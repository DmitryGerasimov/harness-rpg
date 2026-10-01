"""The page language: votes of human messages, the English page, one catalog for both languages."""

import json
import unittest
from datetime import date, timedelta

from harness_rpg.archive import refresh_texts
from harness_rpg.card import avatar_script, chat_card
from harness_rpg.catalog import classify, pending_items
from harness_rpg.character import compute_character
from harness_rpg.constants import LANGS, LANG_FALLBACK, SCHOOL_RULES_VERSION
from harness_rpg.gear import build_gear
from harness_rpg.insights import attach_findings, insight_digest
from harness_rpg.lang import detect_lang, lang_votes, message_lang, page_lang
from harness_rpg.page import render, template_path
from harness_rpg.storage import history_path, ledger_path, load_catalog, load_json, save_json
from harness_rpg.texts import TEXTS
from harness_rpg.transcripts import SessionParser, update
from harness_rpg.views import game_view, public_view

from .support import (
    CYRILLIC, ENGLISH_RECORDS, NOW, SID, TOOLING_WORDS_EN, UUID_SERVER, TranscriptsCase, fake_session, human,
    string_values, tooling_words_in,
)


class LanguageCase(TranscriptsCase):

    records = ENGLISH_RECORDS

    def test_a_message_votes_with_the_words_of_the_human(self):
        votes = {
            'почини /Users/alex/app/models.py, там падает compute_character': 'ru',
            'посмотри, почему падает тест\nTraceback (most recent call last): File "a.py", line 3, in main '
            'raise ValueError("bad value for the parser configuration")': 'ru',
            'да': 'ru',
            'fix the failing test in models.py': 'other',
            'привіт, подивись на тест': 'other',
            '```python\nprint("код")\n```': None,
            '<command-name>/deploy</command-name>\n<command-message>deploy</command-message>': None,
            '<command-name>/deploy</command-name>\n<command-args>выкати на прод</command-args>': 'ru',
            '<system-reminder>Long English reminder of the host app</system-reminder>\nсделай ревью': 'ru',
            '<bash-input>ls</bash-input><bash-stdout>README.md docs src tests</bash-stdout>': None,
            'глянь <pasted_content id="1">a long English paste without its closing tag': 'ru',
            '<pasted_content id="1">a long English paste without its closing tag': None,
            '[Image #1] https://example.com/screenshot.png': None,
        }
        for text, vote in votes.items():
            with self.subTest(text=text):
                self.assertEqual(message_lang(text), vote)

    def test_page_language_follows_the_majority_and_holds_on_a_tie(self):
        self.assertEqual(detect_lang(5, 3), 'ru')
        self.assertEqual(detect_lang(5, 5), 'ru')
        self.assertEqual(detect_lang(1, 3), 'en')
        self.assertEqual(detect_lang(0, 0), LANG_FALLBACK)
        self.assertEqual(detect_lang(0, 0, 'ru'), 'ru')
        # A page that already has a language switches only when the other side clearly leads.
        self.assertEqual(detect_lang(3, 4, 'ru'), 'ru')
        self.assertEqual(detect_lang(2, 8, 'ru'), 'en')
        self.assertEqual(detect_lang(4, 3, 'en'), 'en')
        self.assertEqual(detect_lang(8, 2, 'en'), 'ru')
        # Sessions of an older ledger have no votes and do not count.
        ledger = {'sessions': {'a': fake_session(id='a', langs={'ru': 2, 'other': 1}), 'b': fake_session(id='b')}}
        del ledger['sessions']['b']['langs']
        self.assertEqual(lang_votes(ledger), (2, 1))
        self.assertEqual(page_lang(self.home, ledger), 'ru')
        self.assertEqual(page_lang(self.home, ledger, 'en'), 'en')
        # The latest snapshot holds its language unless the other side clearly leads; one without a language is Russian.
        save_json(history_path(self.home), [{'lang': 'en'}])
        self.assertEqual(page_lang(self.home, ledger), 'ru')
        even = {'sessions': {'a': fake_session(id='a', langs={'ru': 1, 'other': 1})}}
        self.assertEqual(page_lang(self.home, even), 'en')
        save_json(history_path(self.home), [{}])
        self.assertEqual(page_lang(self.home, {'sessions': {}}), 'ru')

    def test_a_suggested_prompt_is_a_turn_but_not_a_vote(self):
        parser = SessionParser('s')
        parser._record({**human('run the tests and fix what fails', 0), 'promptSource': 'suggestion_accepted'},
                       False, {})
        parser._record(human('поехали', 1), False, {})
        result = parser.result()
        self.assertEqual(result['counts']['human_turns'], 2)
        self.assertEqual(result['langs'], {'ru': 1, 'other': 0})

    def test_a_person_writing_in_english_gets_an_english_page(self):
        ledger, _ = update(self.projects, self.home)
        self.assertEqual(ledger['sessions'][SID]['langs'], {'ru': 0, 'other': 3})
        pending = pending_items(ledger, load_catalog(self.home))
        self.assertTrue(all('alias' in item['need'] for item in pending['skills']))
        errors = classify(self.home, {
            'skills': {'my-skill': {'school': 'ranger', 'alias': 'Охота на ошибки'},
                       'pair-coder': {'school': 'summoner', 'alias': 'Session Ward'}},
            'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Eye of the Watch', 'slot': 'helmet'}},
        })
        self.assertEqual(len(errors), 2, 'a Russian alias and a tooling word are refused on an English page')
        classify(self.home, {'skills': {'my-skill': {'alias': 'Hunt for Bugs'}}})
        catalog = load_catalog(self.home)
        self.assertEqual(catalog['skills']['my-skill']['alias_en'], 'Hunt for Bugs')
        self.assertNotIn('alias', catalog['skills']['my-skill'])
        character, html_path, history = render(self.home, now=NOW)
        self.assertEqual(character['lang'], 'en')
        snapshot = history[-1]
        self.assertEqual((snapshot['lang'], snapshot['title'], snapshot['title_key']), ('en', 'Phoenix', 'phoenix'))
        game = game_view(snapshot)
        game['hero'] = {}
        words = ' '.join(string_values(game))
        self.assertIsNone(CYRILLIC.search(words))
        self.assertEqual(tooling_words_in(words, TOOLING_WORDS_EN), [])
        self.assertIn('Eye of the Watch', words)
        self.assertIn(f'{TEXTS["en"]["skill_fallback"]} 1', words)
        self.assertIsNone(CYRILLIC.search(json.dumps(snapshot['insights'], ensure_ascii=False)))
        with open(html_path, encoding='utf-8') as handle:
            self.assertIn('"lang": "en"', handle.read())
        _, _, history = render(self.home, now=NOW + timedelta(minutes=5))
        self.assertEqual(len(history), 1, 'the same English hero replaces its snapshot')
        # The findings are written in the page language.
        finding = {'title': 'Кэш спасает казну', 'text': 'Чтение кэша — 90% токенов.', 'tone': 'rise'}
        errors, _ = attach_findings(self.home, {'findings': [finding]})
        self.assertIn('English', errors[0])
        english = {'title': 'The cache saves the treasury', 'text': 'Cache reads are 90% of the tokens.', 'tone': 'rise'}
        self.assertEqual(attach_findings(self.home, {'findings': [english]})[0], [])
        self.assertEqual(insight_digest(load_json(history_path(self.home), []), {})['lang'], 'en')
        with open(template_path(), encoding='utf-8') as handle:
            card = chat_card(load_json(history_path(self.home), None)[-1], avatar_script(handle.read()))
        self.assertIn('sendPrompt(&quot;Open the hero page&quot;)', card)
        self.assertIsNone(CYRILLIC.search(card))

    def test_one_catalog_keeps_the_aliases_of_both_languages(self):
        usage = {'n': 4, 'day': '2026-09-30', 'tools': {'mail_send': 1, 'mail_read': 1, 'cal_add': 1, 'cal_list': 1}}
        skill = {'display': 'notes', 'n': 1, 'day': '2026-09-30'}
        ledger = {'sessions': {'1': fake_session(id='1', skills={'notes': skill}, mcp={'box': usage})}}
        save_json(ledger_path(self.home), ledger)
        split = {
            'mail': {'name': 'Box Mail', 'alias': 'Голубиная почта', 'slot': 'horn', 'prefixes': ['mail']},
            'cal': {'name': 'Box Calendar', 'alias': 'Песочные часы', 'slot': 'bag', 'prefixes': ['cal']},
        }
        self.assertEqual(classify(self.home, {
            'skills': {'notes': {'school': 'bard', 'alias': 'Свиток заметок'}}, 'mcp': {'box': {'families': split}},
        }), [])
        self.assertEqual(pending_items(ledger, load_catalog(self.home), 'ru'), {'skills': [], 'mcp': []})
        # The page turns English: every alias is asked once more, the split server through its categories.
        pending = pending_items(ledger, load_catalog(self.home), 'en')
        self.assertEqual([item['need'] for item in pending['skills']], [['alias']])
        self.assertEqual([item['need'] for item in pending['mcp']], [['split']])
        english = {
            'mail': {'name': 'Box Mail', 'alias': 'Carrier Pigeon', 'slot': 'horn', 'prefixes': ['mail']},
            'cal': {'name': 'Box Calendar', 'alias': 'Hourglass', 'slot': 'bag', 'prefixes': ['cal']},
        }
        self.assertEqual(classify(self.home, {
            'skills': {'notes': {'alias': 'Scroll of Lore'}}, 'mcp': {'box': {'families': english}},
        }, 'en'), [])
        catalog = load_catalog(self.home)
        self.assertEqual(pending_items(ledger, catalog, 'en'), {'skills': [], 'mcp': []})
        self.assertEqual(pending_items(ledger, catalog, 'ru'), {'skills': [], 'mcp': []})
        self.assertEqual(catalog['skills']['notes'], {'school': 'bard', 'school_rules': SCHOOL_RULES_VERSION,
                                                     'alias': 'Свиток заметок', 'alias_en': 'Scroll of Lore'})
        self.assertEqual(catalog['mcp']['box']['families']['mail']['alias'], 'Голубиная почта')
        today = date(2026, 9, 30)
        sessions = list(ledger['sessions'].values())
        self.assertEqual({item['alias'] for item in build_gear(sessions, catalog, today, 'en')},
                         {'Carrier Pigeon', 'Hourglass'})
        self.assertEqual({item['alias'] for item in build_gear(sessions, catalog, today, 'ru')},
                         {'Голубиная почта', 'Песочные часы'})

    def test_the_archive_is_reworded_into_the_page_language(self):
        skills = {'notes': {'display': 'notes', 'n': 1, 'day': '2026-09-30'}}
        usage = {'n': 2, 'day': '2026-09-30', 'tools': {'read': 2}}
        sessions = {str(i): fake_session(id=str(i), skills=skills, mcp={'box': usage}, plan_mode=True,
                                         counts={'compactions': 3, 'tool_calls': 40, 'edits': 4},
                                         tokens={'output': 3_000_000_000}, hooks={'Stop': 1, 'PreToolUse': 2})
                    for i in range(4)}
        catalog = {'skills': {'notes': {'school': 'bard', 'alias': 'Свиток', 'alias_en': 'Scroll'}},
                   'mcp': {'box': {'alias': 'Шкатулка', 'alias_en': 'Casket', 'slot': 'grimoire'}}}
        views = {lang: public_view(compute_character({'sessions': sessions}, catalog, NOW, lang))
                 for lang in LANGS}
        for lang in LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(refresh_texts(views[lang], lang), views[lang], 'rewording is idempotent')
        # Russian into English: everything but the aliases and the values of the attribute metrics.
        english = refresh_texts(views['ru'], 'en')
        dump = json.dumps(english, ensure_ascii=False).replace('Свиток', 'Scroll').replace('Шкатулка', 'Casket')
        english = json.loads(dump)
        for key, item in english['insights']['attributes'].items():
            for metric, ready in zip(item['metrics'], views['en']['insights']['attributes'][key]['metrics']):
                metric['value'] = ready['value']
        self.assertEqual(english, views['en'])
        self.assertEqual((views['ru']['treasury']['gold']['name'], views['en']['treasury']['gold']['name']),
                         ('Драконья казна III', "Dragon's hoard III"))
        # And back: the Russian snapshot comes back as it was.
        self.assertEqual(refresh_texts(refresh_texts(views['ru'], 'en'), 'ru'), views['ru'])
        # A snapshot before schema 13 has no title key: its title is found by name.
        old = dict(views['ru'])
        old.pop('title_key')
        old.pop('lang')
        self.assertEqual(refresh_texts(old, 'en')['title'], views['en']['title'])


if __name__ == '__main__':
    unittest.main()
