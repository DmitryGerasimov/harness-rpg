"""Names of skills and MCP servers, aliases, and classification into the catalog."""

import os
import unittest
from datetime import date

from harness_rpg.catalog import classify, pending_items
from harness_rpg.constants import SCHOOL_RULES_VERSION
from harness_rpg.gear import build_gear
from harness_rpg.names import alias_problem, auto_mcp_name, normalize_skill, split_mcp
from harness_rpg.storage import catalog_path, ledger_path, load_catalog, save_json
from harness_rpg.transcripts import update

from .support import UUID_SERVER, SessionsCase, TranscriptsCase, fake_session


class ClassifyCase(TranscriptsCase):

    def test_pending_and_classify(self):
        ledger, _ = update(self.projects, self.home)
        pending = pending_items(ledger, load_catalog(self.home))
        self.assertEqual(
            {(item['name'], tuple(item['need'])) for item in pending['skills']},
            {('my-skill', ('school', 'alias')), ('pair-coder', ('school', 'alias')), ('auto-loaded', ('school', 'alias'))},
        )
        self.assertEqual(
            {(tuple(item['servers']), tuple(item['need'])) for item in pending['mcp']},
            {((UUID_SERVER,), ('name', 'alias', 'slot')), (('notebook',), ('alias', 'slot'))},
        )
        errors = classify(self.home, {
            'skills': {
                'My_Skill': 'ranger',
                'pair-coder': {'school': 'summoner', 'alias': 'Призыв подмастерья'},
                'auto-loaded': 'wizard',
            },
            'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Око дозора', 'slot': 'helmet'},
                    'notebook': {'slot': 'crown'}},
        })
        self.assertEqual(len(errors), 2)
        pending = pending_items(ledger, load_catalog(self.home))
        self.assertEqual(
            {(item['name'], tuple(item['need'])) for item in pending['skills']},
            {('my-skill', ('alias',)), ('auto-loaded', ('school', 'alias'))},
        )
        self.assertEqual([item['servers'] for item in pending['mcp']], [['notebook']])
        # An alias-only answer keeps the cached school.
        classify(self.home, {'skills': {'my-skill': {'alias': 'Охота на ошибки'}}})
        self.assertEqual(load_catalog(self.home)['skills']['my-skill'],
                         {'school': 'ranger', 'alias': 'Охота на ошибки', 'school_rules': SCHOOL_RULES_VERSION})

    def test_classify_rejects_leaking_aliases(self):
        update(self.projects, self.home)
        errors = classify(self.home, {
            'skills': {'my-skill': {'school': 'smith', 'alias': 'Удар My Skill'}},
            'mcp': {UUID_SERVER: {'name': 'Acme-Ops', 'alias': 'Око дозора'}, 'notebook': {'alias': 'Шкатулка notebook'}},
        })
        self.assertEqual(len(errors), 2)
        catalog = load_catalog(self.home)
        self.assertEqual(catalog['skills']['my-skill'], {'school': 'smith', 'school_rules': SCHOOL_RULES_VERSION})
        self.assertEqual(catalog['mcp'][UUID_SERVER], {'name': 'Acme-Ops', 'alias': 'Око дозора'})
        self.assertEqual(catalog['mcp']['notebook'], {})


class CatalogCase(SessionsCase):

    def test_split_covers_every_tool_family_of_every_server_id(self):
        home = os.path.join(self.tmp.name, 'home')
        usage = {'n': 4, 'day': '2026-09-30', 'tools': {'a_one': 1, 'a_two': 1, 'b_one': 1, 'b_two': 1}}
        other_id = {'n': 1, 'day': '2026-09-30', 'tools': {'c_one': 1}}
        ledger = {'sessions': {
            '1': fake_session(id='1', mcp={'box': usage}), '2': fake_session(id='2', mcp={'claude_ai_box': other_id}),
        }}
        save_json(ledger_path(home), ledger)
        classify(home, {'mcp': {'box': {'alias': 'Шкатулка', 'slot': 'grimoire'}}})
        pending = pending_items(ledger, load_catalog(home))['mcp']
        self.assertEqual([item['need'] for item in pending], [['split']])
        self.assertEqual(set(pending[0]['families']), {'a', 'b', 'c'})
        bee = {'name': 'Bee', 'alias': 'Улей', 'slot': 'ring'}
        self.assertEqual(len(classify(home, {'mcp': {'box': {'families': {'b': {**bee, 'slot': 'crown'}}}}})), 1)
        # A partial split would leave a catch-all item for the rest: it is refused and nothing changes.
        errors = classify(home, {'mcp': {'box': {'families': {'b': bee}}}})
        self.assertEqual(len(errors), 1)
        self.assertIn("['a', 'c']", errors[0])
        self.assertEqual([item['need'] for item in pending_items(ledger, load_catalog(home))['mcp']], [['split']])
        self.assertEqual(classify(home, {'mcp': {'box': {'families': {}}}}), [])
        self.assertEqual(pending_items(ledger, load_catalog(home))['mcp'], [])
        split = {'first': {'name': 'Ay', 'alias': 'Ларец', 'slot': 'grimoire', 'prefixes': ['a', 'c']}, 'b': bee}
        self.assertEqual(classify(home, {'mcp': {'claude_ai_box': {'families': split}}}), [])
        catalog = load_catalog(home)
        self.assertEqual(pending_items(ledger, catalog)['mcp'], [])
        gear = build_gear(list(ledger['sessions'].values()), catalog, date(2026, 9, 30))
        self.assertEqual({item['name']: item['calls'] for item in gear}, {'Ay': 3, 'Bee': 2})
        # A new tool family shows up later: the server is asked again, with the categories it already has.
        ledger['sessions']['3'] = fake_session(id='3', mcp={'box': {'n': 1, 'day': '2026-09-30', 'tools': {'d_one': 1}}})
        pending = pending_items(ledger, catalog)['mcp']
        self.assertEqual([item['need'] for item in pending], [['split']])
        self.assertEqual(set(pending[0]['current_families']), {'first', 'b'})

    def test_bard_marked_under_the_old_rule_is_asked_once_more(self):
        home = os.path.join(self.tmp.name, 'home')
        used = {'display': 'x', 'n': 1, 'day': '2026-09-30'}
        ledger = {'sessions': {'1': fake_session(id='1', skills={'notes': used, 'docs': used, 'tests': used})}}
        # A catalog of the old rule: no school_rules version on its entries.
        save_json(catalog_path(home), {'mcp': {}, 'skills': {
            'notes': {'school': 'bard', 'alias': 'Свиток заметок'},
            'docs': {'school': 'bard', 'alias': 'Летопись'},
            'tests': {'school': 'smith', 'alias': 'Закалка'},
        }})
        pending = pending_items(ledger, load_catalog(home))['skills']
        self.assertEqual({item['name']: (item['need'], item['school']) for item in pending},
                         {'notes': (['school'], 'bard'), 'docs': (['school'], 'bard')})
        # The agent moves the notes for agents to the summoner and keeps the documentation for people a bard.
        self.assertEqual(classify(home, {'skills': {'notes': 'summoner', 'docs': 'bard'}}), [])
        catalog = load_catalog(home)
        self.assertEqual(pending_items(ledger, catalog)['skills'], [])
        self.assertEqual((catalog['skills']['notes']['school'], catalog['skills']['notes']['alias']),
                         ('summoner', 'Свиток заметок'))

    def test_host_widget_server_is_neither_gear_nor_pending(self):
        # The skill draws its chat card with the host's widget server: it must not turn into the hero's gear.
        widget = {'n': 2, 'day': '2026-09-30', 'tools': {'read_me': 1, 'show_widget': 1}}
        ledger = {'sessions': {'1': fake_session(id='1', mcp={'visualize': widget, 'terminal': widget})}}
        self.assertEqual(build_gear(list(ledger['sessions'].values()), self.catalog, date(2026, 9, 30)), [])
        self.assertEqual(pending_items(ledger, self.catalog)['mcp'], [])


class NamesCase(unittest.TestCase):

    def test_alias_problem(self):
        self.assertIsNone(alias_problem('Око дозора', ('acme-ops-knowledge', UUID_SERVER)))
        self.assertIn('Latin', alias_problem('Око Datadog', ('dd',)))
        self.assertIn('real name', alias_problem('Заметки мудреца', ('заметки-дня',)))
        self.assertIn('longer', alias_problem('Очень ' * 10, ()))
        self.assertEqual(alias_problem('  ', ()), 'empty')
        # Short name parts are not treated as leaks.
        self.assertIsNone(alias_problem('Сон под дубом', ('сон',)))
        # An English page takes English aliases, with the same care about real names and tooling words.
        self.assertIsNone(alias_problem('Scroll of Notes', ('notion',), 'en'))
        self.assertIn('Cyrillic', alias_problem('Око дозора', (), 'en'))
        self.assertIn('Latin', alias_problem('Scroll of Notes', ()))
        self.assertIn('tooling', alias_problem('Session Ward', (), 'en'))
        self.assertIn('tooling', alias_problem('Свиток скилов', ()))
        self.assertIn('real name', alias_problem('Lin Ear Ring', ('linear',), 'en'))

    def test_names(self):
        self.assertEqual(normalize_skill('/anthropic-skills:Make_Release_Notes'), ('make-release-notes', 'Make_Release_Notes'))
        self.assertEqual(split_mcp('mcp__claude_ai_Slack__slack_send_message'), ('claude_ai_Slack', 'slack_send_message'))
        self.assertIsNone(split_mcp('Bash'))
        self.assertEqual(auto_mcp_name('claude_ai_Acme-Ops'), 'Acme-Ops')
        self.assertEqual(auto_mcp_name('plugin_context7_context7'), 'context7')
        self.assertEqual(auto_mcp_name('Claude_Browser'), 'Claude Browser')
        self.assertIsNone(auto_mcp_name(UUID_SERVER))
        self.assertIsNone(auto_mcp_name('ccd_session'))


if __name__ == '__main__':
    unittest.main()
