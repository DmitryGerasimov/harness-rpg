"""Insights: the digest of the real work and the findings."""

import unittest
from datetime import timedelta

from harness_rpg.catalog import classify
from harness_rpg.constants import FINDINGS_MAX
from harness_rpg.insights import attach_findings, insight_digest, reality_digest
from harness_rpg.page import render
from harness_rpg.storage import history_path, ledger_path, load_catalog, load_json
from harness_rpg.transcripts import update

from .support import NOW, SessionsCase, TranscriptsCase, fake_session


class FindingsCase(TranscriptsCase):

    def test_findings_attach_to_the_latest_hero_and_survive_a_rerender(self):
        update(self.projects, self.home)
        render(self.home, now=NOW)
        finding = {'title': 'Кэш спасает казну', 'text': 'Чтение кэша — 90% токенов.', 'tone': 'rise'}
        errors, html_path = attach_findings(self.home, {'findings': [finding]})
        self.assertEqual(errors, [])
        with open(html_path, encoding='utf-8') as handle:
            self.assertIn('Кэш спасает казну', handle.read())
        _, _, history = render(self.home, now=NOW + timedelta(minutes=5))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[-1]['insights']['findings'], [finding], 'the same hero keeps its findings')
        classify(self.home, {'mcp': {'notebook': {'alias': 'Шкатулка памяти'}}})
        _, _, history = render(self.home, now=NOW + timedelta(minutes=10))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]['insights']['findings'], [], 'a changed hero waits for new findings')
        ledger = load_json(ledger_path(self.home), None)
        reality = reality_digest(ledger, load_catalog(self.home), NOW)
        digest = insight_digest(history, reality)
        self.assertEqual(digest['snapshot'], history[-1]['generated_at'])
        self.assertEqual(digest['previous_findings'], ['Кэш спасает казну'], 'the agent sees what it said before')
        self.assertEqual(digest['page_names']['mcp']['notebook'], 'Шкатулка памяти')
        self.assertEqual(digest['reality']['sessions']['with_human'], 1)
        self.assertEqual(digest['reality']['hooks']['PostToolUse']['scripts'], {'secret-lint.sh': 2})
        for bad in ({'findings': []}, {'findings': [{**finding, 'tone': 'loud'}]},
                    {'findings': [finding] * (FINDINGS_MAX + 1)}, {'findings': [{**finding, 'title': ''}]}):
            with self.subTest(bad=bad):
                self.assertTrue(attach_findings(self.home, bad)[0])
        self.assertEqual(load_json(history_path(self.home), None)[-1]['insights']['findings'], [])


class DigestCase(SessionsCase):

    def test_reality_digest_speaks_about_the_real_work(self):
        skill = {'display': 'deploy', 'n': 1}
        sessions = {
            'big': fake_session('2026-09-29', id='big', project='/work/shop', active_seconds=4 * 3600,
                                counts={'human_turns': 4, 'tool_calls': 40, 'interrupts': 1, 'denials': 2, 'edits': 3},
                                tokens={'output': 2_000_000, 'cache_read': 50_000_000},
                                tools={'Bash': 30, 'Agent': 2}, skills={'deploy': {**skill, 'day': '2026-09-29'}},
                                hooks={'Stop': 3}, hook_names={'Stop': {'notify.sh': 3}}),
            'small': fake_session('2026-09-28', id='small', project='/work/blog', counts={'human_turns': 2},
                                  tokens={'output': 100}, skills={'old': {'display': 'old', 'n': 1, 'day': '2026-09-28'}}),
            'gone': fake_session('2026-09-01', id='gone', project='/work/shop',
                                 skills={'old': {'display': 'old', 'n': 1, 'day': '2026-09-01'},
                                         'lost': {'display': 'lost', 'n': 1, 'day': '2026-09-01'}}),
            'lost2': fake_session('2026-09-02', id='lost2', skills={'lost': {'display': 'lost', 'n': 1, 'day': '2026-09-02'}}),
            'bot': fake_session('2026-09-29', id='bot', counts={'human_turns': 0}, tokens={'output': 1_000_000}),
        }
        sessions['bot']['counts']['human_turns'] = 0
        reality = reality_digest({'sessions': sessions}, self.catalog, NOW)
        self.assertEqual((reality['sessions']['with_human'], reality['sessions']['background']), (4, 1))
        self.assertEqual(reality['sessions']['background_gold'], 5.0)
        self.assertEqual([place['name'] for place in reality['places']], ['shop', 'p', 'blog'])
        dearest = reality['money']['dearest'][0]
        self.assertEqual((dearest['place'], dearest['gold'], dearest['subagents']), ('shop', 15.0, 2))
        self.assertEqual((reality['autonomy']['interrupts'], reality['autonomy']['denials']), (1, 2))
        self.assertEqual(reality['hooks']['Stop'], {'fires': 3, 'sessions': 1, 'scripts': {'notify.sh': 3}})
        self.assertEqual(reality['skills']['new_this_week'], ['deploy'])
        self.assertEqual([item['name'] for item in reality['skills']['quiet_for_2_weeks']], ['lost'])
        self.assertEqual(reality['builtin_tools'], {'Bash': 30, 'Agent': 2})
        # Weeks stay inside the window transcripts always cover: the two September sessions fall outside.
        self.assertEqual(len(reality['rhythm']['weeks']), 4)
        self.assertEqual(sum(week['sessions'] for week in reality['rhythm']['weeks']), 2)


if __name__ == '__main__':
    unittest.main()
