"""What ships: one name and one version across the package, the plugin and the marketplace; no fixed install path."""

import json
import os
import re
import unittest

from harness_rpg import __version__
from harness_rpg.catalog import read_frontmatter

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SKILL_DIR = os.path.join(ROOT, 'skill')
SKILL_MD = os.path.join(SKILL_DIR, 'SKILL.md')


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as handle:
        return json.load(handle)


class ReleaseCase(unittest.TestCase):

    def test_plugin_is_the_skill_of_this_version(self):
        plugin = load('skill', '.claude-plugin', 'plugin.json')
        self.assertRegex(__version__, r'^\d+\.\d+\.\d+$')
        # The plugin reaches people only when its version changes: it is the release version.
        self.assertEqual(plugin['version'], __version__)
        self.assertEqual(plugin['name'], read_frontmatter(SKILL_MD)['name'])

    def test_marketplace_points_at_the_skill(self):
        [entry] = load('.claude-plugin', 'marketplace.json')['plugins']
        self.assertEqual(entry['name'], read_frontmatter(SKILL_MD)['name'])
        self.assertEqual(os.path.normpath(os.path.join(ROOT, entry['source'])), SKILL_DIR)

    def test_skill_runs_the_script_from_where_it_is_installed(self):
        with open(SKILL_MD, encoding='utf-8') as handle:
            text = handle.read()
        # A personal, project or plugin install puts the skill in different places: only the variable finds it.
        self.assertNotIn('~/.claude/skills', text)
        script = 'python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py'
        commands = re.findall(r'^\s*(python3 \S+rpg\.py)', text, re.MULTILINE)
        self.assertTrue(commands)
        self.assertEqual(set(commands), {script})
        # The same command is pre-approved, so running it asks nothing.
        self.assertEqual(read_frontmatter(SKILL_MD)['allowed-tools'], f'Bash({script} *)')


if __name__ == '__main__':
    unittest.main()
