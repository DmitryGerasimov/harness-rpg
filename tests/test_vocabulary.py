"""The hero's vocabulary: no tooling words on the page, every text in both languages."""

import json
import re
import unittest

from harness_rpg.card import avatar_script
from harness_rpg.character import compute_character
from harness_rpg.constants import (
    ACHIEVEMENTS, ALIGNMENTS, ATTRIBUTES, AURAS, AURA_TIERS, CAMP_TIERS, GEAR_SLOTS, GOLD_TIERS, LANGS, SCHOOLS,
    SKILL_RANKS,
)
from harness_rpg.page import template_path
from harness_rpg.skills import pick_class
from harness_rpg.texts import TEXTS
from harness_rpg.views import game_view, public_view

from .support import CYRILLIC, NOW, TOOLING_WORDS_EN, fake_session, string_values, text_blocks, tooling_words_in


class VocabularyCase(unittest.TestCase):

    def test_page_data_speaks_hero_language(self):
        catalog = {'skills': {f's{i}': {'school': school, 'alias': 'Приём'} for i, school in enumerate(SCHOOLS)},
                   'mcp': {}}
        skills = {f's{i}': {'display': f's{i}', 'n': 1, 'day': '2026-09-30'} for i in range(len(SCHOOLS))}
        sessions = {str(i): fake_session(id=str(i), skills=skills, hooks={event: 1 for _, events in AURAS
                                                                          for event in events})
                    for i in range(3)}
        for primary, secondary in [('summoner', None), ('bard', 'summoner'), (None, None)]:
            character = compute_character({'sessions': sessions}, catalog, NOW)
            character['class'].update(pick_class({key: 1.0 for key in filter(None, (primary, secondary))}))
            # The insights layer speaks plain technical words on purpose; the game view speaks about the hero.
            view = game_view(public_view(character))
            view['hero'] = {}
            with self.subTest(primary=primary, secondary=secondary):
                self.assertEqual(tooling_words_in(json.dumps(view, ensure_ascii=False)), [])

    def test_template_texts_speak_hero_language(self):
        with open(template_path(), encoding='utf-8') as handle:
            template = handle.read()
        # The insights layer speaks plain technical words on purpose; the rest of the page speaks about the hero.
        begin = template.index('// ==== Insights layer: begin ====')
        end = template.index('// ==== Insights layer: end ====')
        self.assertIn('скил', template[begin:end])
        game = template[:begin] + template[end:]
        # The hero's name is the one allowed exception.
        russian = ' '.join(re.findall(r'[А-Яа-яЁё][^\'"`<>{}]*', game.replace('Claude Code', '')))
        self.assertEqual(tooling_words_in(russian), [])
        # The English words of the game view live in TEXTS.en: none of them is a tooling word either.
        english = ' '.join(string_values(re.findall(r"'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`",
                                                     '\n'.join(text_blocks(template, 'TEXTS')['en']))))
        self.assertTrue(english)
        self.assertEqual(tooling_words_in(english.replace('Claude Code', ''), TOOLING_WORDS_EN), [])
        self.assertIn('skill', '\n'.join(text_blocks(template, 'INSIGHT_TEXTS')['en']))

    def test_template_has_every_text_in_both_languages(self):
        with open(template_path(), encoding='utf-8') as handle:
            template = handle.read()
        for name in ('TEXTS', 'INSIGHT_TEXTS'):
            blocks = text_blocks(template, name)
            keys = {}
            for lang, lines in blocks.items():
                # A line at the key indent is a key, so no text hides inside a value spread over lines.
                at_key_indent = [line for line in lines if re.match(r'^    \S', line)]
                self.assertTrue(all(re.match(r'^    \w+: ', line) for line in at_key_indent), (name, lang))
                keys[lang] = [re.match(r'^    (\w+):', line).group(1) for line in at_key_indent]
            with self.subTest(name=name):
                self.assertTrue(keys['ru'])
                self.assertEqual(keys['ru'], keys['en'])
                self.assertEqual(len(keys['ru']), len(set(keys['ru'])))

    def test_template_speaks_russian_only_in_its_russian_texts(self):
        with open(template_path(), encoding='utf-8') as handle:
            template = handle.read()
        russian = {line for name in ('TEXTS', 'INSIGHT_TEXTS') for line in text_blocks(template, name)['ru']}
        stray = [
            line.strip() for line in template.splitlines()
            if CYRILLIC.search(line) and line not in russian
            and not line.strip().startswith(('//', '<!--', '/*', '*'))
        ]
        self.assertEqual(stray, [])

    def test_chat_card_avatar_needs_no_page_texts(self):
        with open(template_path(), encoding='utf-8') as handle:
            avatar = avatar_script(handle.read())
        self.assertIsNone(re.search(r'\b(?:T|IT)\.|\bLANG\b|\bTEXTS\b', avatar))

    def test_english_page_data_speaks_hero_language(self):
        catalog = {'skills': {f's{i}': {'school': school, 'alias_en': 'Craft'} for i, school in enumerate(SCHOOLS)},
                   'mcp': {}}
        skills = {f's{i}': {'display': f's{i}', 'n': 1, 'day': '2026-09-30'} for i in range(len(SCHOOLS))}
        sessions = {str(i): fake_session(id=str(i), skills=skills, hooks={event: 1 for _, events in AURAS
                                                                          for event in events})
                    for i in range(3)}
        for primary, secondary in [('summoner', None), ('bard', 'summoner'), ('smith', 'wanderer'), (None, None)]:
            character = compute_character({'sessions': sessions}, catalog, NOW, 'en')
            character['class'].update(pick_class({key: 1.0 for key in filter(None, (primary, secondary))}, 'en'))
            view = game_view(public_view(character))
            view['hero'] = {}
            words = ' '.join(string_values(view))
            with self.subTest(primary=primary, secondary=secondary):
                self.assertEqual(view['lang'], 'en')
                self.assertIsNone(CYRILLIC.search(words))
                self.assertEqual(tooling_words_in(words, TOOLING_WORDS_EN), [])

    def test_both_languages_have_one_vocabulary(self):
        def shape(node):
            # Lists are noun forms for a count: three in Russian, two in English.
            if isinstance(node, dict):
                return {key: shape(value) for key, value in node.items()}
            if isinstance(node, tuple):
                return tuple(shape(value) for value in node)
            if isinstance(node, list):
                return list
            return type(node)

        self.assertEqual(shape(TEXTS['ru']), shape(TEXTS['en']))
        for lang in LANGS:
            words = TEXTS[lang]
            self.assertEqual(set(words['schools']), set(SCHOOLS))
            self.assertEqual(set(words['achievements']), set(dict(ACHIEVEMENTS)))
            self.assertEqual(set(words['auras']), {key for key, _ in AURAS})
            self.assertEqual(set(words['slots']), set(GEAR_SLOTS))
            self.assertEqual(set(words['alignments']), set(ALIGNMENTS))
            self.assertEqual(set(words['attributes']), set(ATTRIBUTES))
            self.assertEqual(len(words['ranks']), len(SKILL_RANKS))
            self.assertEqual(len(words['aura_tiers']), len(AURA_TIERS))
            self.assertEqual(len(words['gold_tiers']), len(GOLD_TIERS))
            self.assertEqual(len(words['camp_tiers']), len(CAMP_TIERS))
            for key, (_, _, _, _, labels) in words['attributes'].items():
                self.assertEqual(len(labels), len(TEXTS['ru']['attributes'][key][4]))


if __name__ == '__main__':
    unittest.main()
