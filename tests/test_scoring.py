"""Scoring: decay, ranks, levels, the class, attribute curves, auras, the treasury and alignment."""

import os
import unittest
from datetime import date, datetime, timedelta, timezone

from harness_rpg.alignment import build_alignment
from harness_rpg.auras import build_auras
from harness_rpg.constants import (
    CAMP_TIERS, DAILY_SESSIONS_CAP, GOLD_TIERS, HALF_LIFE_DAYS, LANGS, RARITIES, SCHOOLS, SKILL_RANKS,
)
from harness_rpg.scoring import (
    current_streak, decay_score, level_from_xp, linear, longest_streak, saturating, threshold_index, usage_profile,
)
from harness_rpg.skills import pick_class
from harness_rpg.texts import TEXTS, named
from harness_rpg.treasury import build_treasury, gold_of, open_next, open_tier

from .support import TempDirCase, fake_session


class ScoringCase(unittest.TestCase):

    def test_decay_halves_every_half_life(self):
        today = date(2026, 9, 30).toordinal()
        self.assertAlmostEqual(decay_score([(today, 1)], today), 1.0)
        self.assertAlmostEqual(decay_score([(today - HALF_LIFE_DAYS, 1)], today), 0.5)
        self.assertEqual(decay_score([(today + 1, 1)], today), 0)

    def test_daily_cap_and_rust(self):
        today = date(2026, 9, 30)
        busy = {(today - timedelta(days=200)).isoformat(): 10}
        current, peak = usage_profile(busy, today)
        self.assertAlmostEqual(peak, DAILY_SESSIONS_CAP)
        self.assertLess(current, 0.1)
        ranks = named(SKILL_RANKS, TEXTS['ru']['ranks'])
        self.assertLess(threshold_index(current, ranks), threshold_index(peak, ranks))

    def test_ranks_and_rarities(self):
        ranks = named(SKILL_RANKS, TEXTS['ru']['ranks'])
        self.assertEqual(ranks[threshold_index(0.3, ranks)][1], 'Новичок')
        self.assertEqual(ranks[threshold_index(60, ranks)][1], 'Грандмастер')
        self.assertEqual(RARITIES[threshold_index(20, RARITIES)][1], 'epic')
        self.assertEqual(RARITIES[threshold_index(2.9, RARITIES)][1], 'common')

    def test_levels(self):
        self.assertEqual(level_from_xp(0), (1, 0, 100))
        self.assertEqual(level_from_xp(99), (1, 99, 100))
        self.assertEqual(level_from_xp(100), (2, 0, 115))
        self.assertEqual(level_from_xp(215), (3, 0, 132))

    def test_class_pure_hybrid_and_wanderer(self):
        self.assertEqual(pick_class({'ranger': 10, 'bard': 5})['name'], 'Следопыт')
        hybrid = pick_class({'ranger': 10, 'bard': 8})
        self.assertEqual((hybrid['name'], hybrid['primary'], hybrid['secondary']), ('Летописец', 'ranger', 'bard'))
        self.assertEqual(pick_class({})['name'], TEXTS['ru']['no_class'][0])
        self.assertEqual(pick_class({'wanderer': 9, 'bard': 10})['name'], 'Менестрель')
        self.assertEqual(pick_class({'wanderer': 9, 'bard': 10}, 'en')['name'], 'Minstrel')
        schools = len(SCHOOLS)
        for lang in LANGS:
            self.assertEqual(len(TEXTS[lang]['hybrids']), schools * (schools - 1) // 2)

    def test_every_class_has_its_tooltip_lore(self):
        words = TEXTS['ru']
        self.assertEqual(set(words['epithets']), set(SCHOOLS))
        self.assertEqual(set(words['schools']), set(SCHOOLS))
        pure = pick_class({'bard': 10, 'smith': 1})
        self.assertEqual((pure['epithet'], pure['lore']), ('Непревзойдённый бард', words['schools']['bard'][1]))
        hybrid = pick_class({'bard': 10, 'engineer': 9})
        self.assertEqual((hybrid['name'], hybrid['epithet']), ('Глашатай', None))
        self.assertEqual(hybrid['lore'], words['hybrids'][frozenset(('bard', 'engineer'))][1])
        self.assertEqual(pick_class({})['lore'], words['no_class'][1])

    def test_attribute_curves(self):
        self.assertAlmostEqual(saturating(5, 5), 10.5)
        self.assertEqual(saturating(0, 5), 1)
        self.assertEqual(linear(1.0, 0.85, 1.0), 20)
        self.assertEqual(linear(0.5, 0.85, 1.0), 1)

    def test_streak(self):
        today = date(2026, 9, 30)
        days = ['2026-09-27', '2026-09-28', '2026-09-29']
        self.assertEqual(current_streak(days, today), 3)
        self.assertEqual(current_streak(days + ['2026-09-30'], today), 4)
        self.assertEqual(current_streak(['2026-09-20'], today), 0)
        self.assertEqual(longest_streak(days + ['2026-09-20', '2026-09-21']), 3)


class BlocksCase(TempDirCase):

    def test_aura_strength_is_normalized_by_sessions(self):
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        loud = [fake_session(id='a', hooks={'PostToolUse': 5000}), fake_session(id='b')]
        quiet = [fake_session(id='a', hooks={'PostToolUse': 1}), fake_session(id='b')]

        def strength(sessions):
            return [(aura['key'], aura['share'], aura['tier']) for aura in build_auras(sessions, now)]

        self.assertEqual(strength(loud), strength(quiet))
        aura = build_auras(loud, now)[0]
        self.assertEqual((aura['key'], aura['tier_name']), ('temper', 'Ровная'))
        old = [fake_session('2026-06-01', id='old', hooks={'Stop': 3}), fake_session(id='new')]
        self.assertEqual([(a['key'], a['tier_name']) for a in build_auras(old, now)],
                         [('herald', TEXTS['ru']['aura_dormant'])])
        self.assertEqual(build_auras([fake_session(hooks={'UnknownEvent': 2})], now), [])

    def test_treasury_tiers(self):
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        self.assertEqual(gold_of(fake_session(tokens={'input': 1, 'output': 1, 'cache_write': 4, 'cache_read': 10})),
                         1 + 5 + 5 + 1)
        empty = build_treasury([fake_session()], now)
        self.assertEqual((empty['gold']['name'], empty['camp']['name']), ('Пустой кошель', 'Без привалов'))
        rich = fake_session(tokens={'output': 60_000_000}, counts={'compactions': 4})
        old = fake_session('2026-06-01', id='old', tokens={'output': 10**12}, counts={'compactions': 50})
        treasury = build_treasury([rich, old], now)
        self.assertEqual(treasury['gold']['name'], 'Сокровищница', 'sessions outside the window spend no gold')
        self.assertEqual(treasury['gold']['dearest'][0]['tokens'], 60_000_000)
        self.assertEqual(treasury['gold']['dearest'][0]['cache_read'], 0)
        self.assertEqual(treasury['gold']['tokens']['output'], 60_000_000)
        self.assertEqual(treasury['camp']['name'], 'Частые привалы')

    def test_top_tiers_are_open(self):
        gold = named(GOLD_TIERS, TEXTS['ru']['gold_tiers'])
        camp = named(CAMP_TIERS, TEXTS['ru']['camp_tiers'])
        top_gold = GOLD_TIERS[-1]
        self.assertEqual(open_tier(top_gold, gold, 4), (5, 'Драконья казна'))
        self.assertEqual(open_tier(top_gold * 4, gold, 4), (5, 'Драконья казна II'))
        self.assertEqual(open_tier(top_gold * 16 - 1, gold, 4), (5, 'Драконья казна II'))
        self.assertEqual(open_tier(top_gold * 16, gold, 4), (5, 'Драконья казна III'))
        self.assertEqual(open_tier(30, camp, 2), (3, 'Живёт у костра II'))
        self.assertEqual(open_tier(3, camp, 2), (1, 'Редкие привалы'))
        self.assertEqual(open_next(top_gold * 4, gold, 4), {'name': 'Драконья казна III', 'at': top_gold * 16})

    def test_alignment_axes(self):
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        rules = os.path.join(self.tmp.name, 'CLAUDE.md')
        with open(rules, 'w', encoding='utf-8') as handle:
            handle.write('rule\n' * 2000)
        careful = [fake_session(id=str(i), plan_mode=True, modes=['default'], counts={'verifications': 1})
                   for i in range(5)]
        self.assertEqual(build_alignment(careful, now)['name'], 'Законопослушный добрый')
        os.remove(rules)
        reckless = [fake_session(id=str(i), modes=['bypassPermissions'], counts={'destructive': 1}) for i in range(5)]
        self.assertEqual(build_alignment(reckless, now)['name'], 'Хаотичный злой')
        self.assertEqual(build_alignment([], now)['name'], 'Истинно нейтральный')


if __name__ == '__main__':
    unittest.main()
