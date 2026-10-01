"""Gear: split servers and slots."""

import unittest
from datetime import date

from harness_rpg.character import compute_character
from harness_rpg.constants import BAG
from harness_rpg.gear import build_gear
from harness_rpg.views import public_view

from .support import NOW, SessionsCase, fake_session


class GearCase(SessionsCase):

    def test_split_server_is_only_its_categories(self):
        today = date(2026, 9, 30)
        usage = {'n': 9, 'day': '2026-09-30', 'tools': {
            'notes_get': 3, 'notes_put': 2, 'db_query': 2, 'db_schema': 1, 'logs_tail': 1,
        }}
        sessions = [fake_session(id='1', mcp={'box': usage})]
        self.catalog['mcp'] = {'box': {'alias': 'Шкатулка памяти', 'slot': 'grimoire', 'split_checked': True, 'families': {
            'notes': {'name': 'Notes', 'alias': 'Свиток памяти', 'slot': 'grimoire'},
            'data': {'name': 'Base', 'alias': 'Амулет недр', 'slot': 'amulet', 'prefixes': ['db']}}}}
        gear = {item['name']: item for item in build_gear(sessions, self.catalog, today)}
        # No catch-all item named after the server, and a family no category took waits for classification.
        self.assertEqual(set(gear), {'Notes', 'Base'})
        self.assertEqual((gear['Base']['alias'], gear['Base']['slot'], gear['Base']['calls']), ('Амулет недр', 'amulet', 3))
        self.assertEqual((gear['Notes']['alias'], gear['Notes']['slot'], gear['Notes']['affixes']), ('Свиток памяти', 'grimoire', 2))
        self.assertTrue(gear['Base']['equipped'] and gear['Notes']['equipped'])

    def test_strongest_item_of_a_slot_is_worn_the_rest_go_to_the_bag(self):
        today = date(2026, 9, 30)
        busy = {'n': 5, 'day': '2026-09-30', 'tools': {'a': 5}}
        quiet = {'n': 1, 'day': '2026-09-01', 'tools': {'b': 1}}
        sessions = [fake_session(id='1', mcp={'docs': busy, 'notes': quiet, 'misc': busy, 'loose': busy})]
        self.catalog['mcp'] = {
            'docs': {'slot': 'grimoire'}, 'notes': {'slot': 'grimoire'}, 'misc': {'slot': BAG},
        }
        gear = {item['name']: item for item in build_gear(sessions, self.catalog, today)}
        self.assertTrue(gear['docs']['equipped'])
        self.assertFalse(gear['notes']['equipped'], 'the weaker item of an occupied slot goes to the bag')
        self.assertFalse(gear['misc']['equipped'])
        self.assertFalse(gear['loose']['equipped'], 'an item without a slot goes to the bag')
        view_gear = public_view(compute_character({'sessions': {'1': sessions[0]}}, self.catalog, NOW))['gear']
        self.assertEqual(sorted((item['slot'] or '', item['equipped']) for item in view_gear),
                         [('', False), ('', False), ('grimoire', False), ('grimoire', True)])


if __name__ == '__main__':
    unittest.main()
