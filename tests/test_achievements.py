"""Achievements, their medals and the title."""

import os
import unittest
from datetime import date, timedelta

from harness_rpg.achievements import build_achievements, keep_earned, medal_for
from harness_rpg.character import compute_character
from harness_rpg.constants import ACHIEVEMENTS, LEDGER_VERSION, PUBLIC_SCHEMA_VERSION, SCHOOLS
from harness_rpg.page import render
from harness_rpg.storage import ledger_path, save_json
from harness_rpg.texts import TEXTS, achievement_criteria

from .support import NOW, SessionsCase, fake_session


class AchievementsCase(SessionsCase):

    def medals(self, sessions):
        days = sorted({day for session in sessions for day in session['days']})
        return {item['key']: item['tier'] for item in build_achievements(sessions, days, self.catalog)}

    def test_each_medal_needs_its_threshold(self):
        thresholds = dict(ACHIEVEMENTS)
        start = date(2026, 1, 1)
        self.catalog['skills'] = {f's{i}': {'school': school} for i, school in enumerate(SCHOOLS)}
        builders = {
            'phoenix': lambda n: [fake_session(counts={'compactions': n})],
            'flawless': lambda n: [fake_session(counts={'tool_calls': n})],
            'warlord': lambda n: [fake_session(tools={'Agent': n})],
            'marathon': lambda n: [fake_session(longest_stretch=n * 3600)],
            'trek': lambda n: [fake_session(active_seconds=n * 3600)],
            'tireless': lambda n: [fake_session((start + timedelta(days=i)).isoformat()) for i in range(n)],
            'versatile': lambda n: [fake_session(skills={
                f's{i}': {'display': f's{i}', 'n': 1, 'day': '2026-09-30'} for i in range(n)})],
            'strategist': lambda n: [fake_session(id=str(i), plan_mode=True) for i in range(n)],
            'polyglot': lambda n: [fake_session(extensions=[f'.e{i}' for i in range(n)])],
            'explorer': lambda n: [fake_session(id=str(i), project=f'/p{i}') for i in range(n)],
            'night_owl': lambda n: [fake_session(night_days=[
                (start + timedelta(days=i)).isoformat() for i in range(n)])],
        }
        self.assertEqual(set(builders), set(thresholds))
        for key, build in builders.items():
            with self.subTest(key=key):
                self.assertEqual(self.medals(build(thresholds[key][0] - 1))[key], -1)
                for tier, threshold in enumerate(thresholds[key]):
                    self.assertEqual(self.medals(build(threshold))[key], tier)
        flawed = fake_session(counts={'tool_calls': thresholds['flawless'][2], 'tool_errors': 1})
        self.assertEqual(self.medals([flawed])['flawless'], -1)
        _, template, forms = TEXTS['ru']['achievements']['marathon']
        self.assertEqual([achievement_criteria(template, forms, n) for n in (2, 6)],
                         ['проработать 2 часа подряд — без пауз дольше 10 минут',
                          'проработать 6 часов подряд — без пауз дольше 10 минут'])
        _, template, forms = TEXTS['en']['achievements']['marathon']
        self.assertEqual([achievement_criteria(template, forms, n, 'en') for n in (1, 6)],
                         ['work 1 hour in a row — no pauses longer than 10 minutes',
                          'work 6 hours in a row — no pauses longer than 10 minutes'])

    def test_legacy_registry_and_snapshots_map_to_medals(self):
        character = compute_character({'sessions': {'a': fake_session()}}, self.catalog, NOW)
        old_snapshot = {'generated_at': '2026-09-01T00:00:00+03:00',
                        'achievements': [{'key': 'polyglot', 'earned': True, 'criteria': 'old text'}]}
        registry = keep_earned(character, {'flawless': '2026-09-30T19:42:16+03:00'}, [old_snapshot])
        tiers = {item['key']: item['tier'] for item in character['achievements']}
        thresholds = dict(ACHIEVEMENTS)
        self.assertEqual(tiers['flawless'], medal_for(thresholds['flawless'], 300))
        self.assertEqual(tiers['polyglot'], medal_for(thresholds['polyglot'], 15))
        self.assertEqual(registry['flawless'], {'tier': 1, 'at': '2026-09-30T19:42:16+03:00', 'schema': 0})

    def test_medals_from_before_a_recount_are_dropped(self):
        # Marathon gold was once earned by counting every long pause as ten minutes of work, then the marathon
        # became the longest stretch without pauses: medals from both older counts are dropped.
        three_hours = fake_session(longest_stretch=3 * 3600, active_seconds=10 * 3600)
        character = compute_character({'sessions': {'a': three_hours}}, self.catalog, NOW)
        old = {'generated_at': '2026-09-30T20:00:00+03:00', 'schema': 11,
               'achievements': [{'key': 'marathon', 'tier': 2, 'earned': True, 'criteria': []}]}
        registry = keep_earned(character, {'marathon': {'tier': 2, 'at': '2026-09-30T20:00:00+03:00', 'schema': 11}}, [old])
        medals = {item['key']: item['tier'] for item in character['achievements']}
        self.assertEqual(medals['marathon'], 1, 'a three-hour stretch gives silver, the old gold is not kept')
        self.assertEqual(medals['trek'], 1, 'ten hours of work in one session give silver on the long trek')
        self.assertEqual(registry['marathon']['schema'], PUBLIC_SCHEMA_VERSION)
        # A medal recorded after the recount stays for good.
        later = compute_character({'sessions': {'a': fake_session(longest_stretch=3600)}}, self.catalog, NOW)
        keep_earned(later, registry, [])
        self.assertEqual(next(item for item in later['achievements'] if item['key'] == 'marathon')['tier'], 1)

    def test_achievements_stay_earned_when_the_session_changes(self):
        home = os.path.join(self.tmp.name, 'home')
        flawless = fake_session(counts={'tool_calls': 400})
        save_json(ledger_path(home), {'version': LEDGER_VERSION, 'files': {}, 'sessions': {'a': flawless}})
        character, _, _ = render(home, now=NOW)
        self.assertEqual(character['title'], 'Безупречный')
        # The same live session later gets an error: the earned achievement must not disappear.
        flawless['counts']['tool_errors'] = 1
        save_json(ledger_path(home), {'version': LEDGER_VERSION, 'files': {}, 'sessions': {'a': flawless}})
        character, _, history = render(home, now=NOW + timedelta(minutes=5))
        self.assertEqual(character['title'], 'Безупречный')
        kept = next(item for item in history[-1]['achievements'] if item['key'] == 'flawless')
        self.assertEqual((kept['earned'], kept['tier_name']), (True, 'золото'))
        # Even without the registry file, the archive keeps the achievement.
        os.remove(os.path.join(home, 'achievements.json'))
        character, _, _ = render(home, now=NOW + timedelta(minutes=10))
        self.assertEqual(character['title'], 'Безупречный')

    def test_title_is_the_best_medal_then_prestige(self):
        nights = lambda n: [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]  # noqa: E731
        silver_both = {'sessions': {'a': fake_session(counts={'compactions': 3}, night_days=nights(10))}}
        self.assertEqual(compute_character(silver_both, self.catalog, NOW)['title'], 'Феникс')
        gold_owl = {'sessions': {'a': fake_session(counts={'compactions': 3}, night_days=nights(30))}}
        self.assertEqual(compute_character(gold_owl, self.catalog, NOW)['title'], 'Ночная сова')


if __name__ == '__main__':
    unittest.main()
