"""Transcript parsing and the ledger update."""

import json
import os
import unittest

from harness_rpg.constants import DESTRUCTIVE_RE, VERIFY_RE
from harness_rpg.storage import ledger_path
from harness_rpg.transcripts import SessionParser, hook_script, parse_session, session_files, update

from .support import SID, UUID_SERVER, TranscriptsCase, tool_result, ts


class TranscriptCase(TranscriptsCase):

    def test_parse_session(self):
        session = parse_session(SID, session_files(self.projects)[SID])
        counts = session['counts']
        self.assertEqual(counts['human_turns'], 3)
        self.assertEqual(counts['tool_calls'], 8)
        self.assertEqual(counts['tool_errors'], 1)
        self.assertEqual(counts['edits'], 2)
        self.assertEqual(counts['destructive'], 1)
        self.assertEqual(counts['verifications'], 1)
        self.assertEqual(session['extensions'], ['.py'])
        self.assertEqual(session['night_days'], ['2026-09-30'])
        self.assertEqual(session['modes'], ['auto', 'plan'])
        self.assertEqual(session['hooks'], {'PostToolUse': 2, 'Stop': 1})
        self.assertEqual(session['tokens'], {'input': 12, 'output': 8, 'cache_write': 100, 'cache_read': 1000})
        # Only the hook script's file name reaches the ledger, never the command line.
        self.assertEqual(session['hook_names'], {'PostToolUse': {'secret-lint.sh': 2}})
        self.assertNotIn('~/.claude/hooks', json.dumps(session))
        self.assertEqual(counts['edit_errors'], 1)
        self.assertEqual(counts['commits'], 1)
        self.assertEqual(counts['denials'], 1)
        self.assertEqual(counts['interrupts'], 1)
        self.assertEqual(counts['compactions'], 1)
        self.assertEqual(counts['outbound'], 1)
        self.assertTrue(session['plan_mode'])
        self.assertEqual(session['project'], '/work/repo')
        self.assertEqual(set(session['skills']), {'my-skill', 'pair-coder', 'auto-loaded'})
        self.assertEqual(session['skills']['my-skill']['n'], 1)
        self.assertEqual(session['skills']['auto-loaded']['n'], 0)
        self.assertEqual(set(session['mcp']), {'notebook', UUID_SERVER})
        self.assertEqual(session['mcp'][UUID_SERVER]['tools'], {'logs_search': 1})
        self.assertEqual(session['tools'], {'Bash': 3, 'Edit': 1, 'Skill': 1, 'Write': 1})
        # Language votes of the human's messages, counts only: the command arguments vote too.
        self.assertEqual(session['langs'], {'ru': 3, 'other': 0})

    def test_long_pauses_are_not_active_time(self):
        parser = SessionParser('s')
        for minutes in (0, 5, 125, 130):
            parser._record({'type': 'user', 'timestamp': ts(minutes), 'message': {'content': []}}, False, {})
        # Bookkeeping records every few minutes must not stitch the pause into work.
        for minutes in (12, 19, 26, 33):
            parser._record({'type': 'system', 'subtype': 'away_summary', 'timestamp': ts(minutes)}, False, {})
        self.assertEqual(parser.result()['active_seconds'], 10 * 60, 'two 5-minute stretches, the 2-hour pause is out')
        self.assertEqual(parser.result()['longest_stretch'], 5 * 60)

    def test_hook_script_names(self):
        self.assertEqual(hook_script('python3 ~/.claude/hooks/lint.py --fix "$FILE"'), 'lint.py')
        self.assertEqual(hook_script('bash -c "~/bin/notify.sh done"'), 'notify.sh')
        self.assertEqual(hook_script('jq -r .tool_name'), 'jq')
        # Variables set before an inline command may hold secrets: the name is the program after them.
        self.assertEqual(hook_script('GITHUB_TOKEN=ghp_secret LEVEL=2 curl -s https://example.com'), 'curl')
        self.assertIsNone(hook_script('API_KEY=sk-secret'))
        self.assertIsNone(hook_script(None))
        self.assertIsNone(hook_script('  '))

    def test_update_is_idempotent(self):
        _, parsed = update(self.projects, self.home)
        self.assertEqual(parsed, 1)
        with open(ledger_path(self.home), 'rb') as handle:
            first = handle.read()
        _, parsed = update(self.projects, self.home)
        self.assertEqual(parsed, 0)
        with open(ledger_path(self.home), 'rb') as handle:
            self.assertEqual(handle.read(), first)

    def test_odd_records_are_skipped(self):
        # Records Claude Code may write in another shape some day: each is skipped, the rest still counts.
        odd = [
            {'type': 'assistant', 'timestamp': ts(30), 'message': {'id': ['m'], 'content': [], 'usage': {}}},
            {'type': 'assistant', 'timestamp': ts(31), 'message': {'content': [{'type': 'tool_use', 'id': 'x',
                                                                                'name': 42, 'input': {}}]}},
            tool_result('x', 32, toolDenialKind=['user-rejected']),
            {'type': 'user', 'timestamp': ts(33), 'cwd': {'path': '/work/odd'}, 'message': {'content': 'hi'}},
        ]
        path = os.path.join(self.projects, '-work-repo', f'{SID}.jsonl')
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write(''.join(json.dumps(record) + '\n' for record in odd))
        ledger, parsed = update(self.projects, self.home)
        self.assertEqual(parsed, 1)
        self.assertEqual(ledger['sessions'][SID]['project'], '/work/repo')
        self.assertEqual(ledger['sessions'][SID]['counts']['edits'], 2)

    def test_project_is_the_first_folder_given_as_text(self):
        parser = SessionParser('s')
        parser._record({'type': 'user', 'cwd': {'path': '/work/odd'}}, False, {})
        parser._record({'type': 'user', 'cwd': '/work/shop'}, False, {})
        self.assertEqual(parser.result()['project'], '/work/shop')

    def test_vanished_file_gives_nothing(self):
        parser = SessionParser('s')
        parser.parse_file(os.path.join(self.projects, 'gone.jsonl'), is_sub=False)
        self.assertIsNone(parser.result()['start'])

    def test_first_update_without_transcripts_writes_the_ledger(self):
        empty = os.path.join(self.home, 'no-projects')
        ledger, parsed = update(empty, self.home)
        self.assertEqual((parsed, ledger['sessions']), (0, {}))
        self.assertTrue(os.path.exists(ledger_path(self.home)))

    def test_ledger_keeps_deleted_sessions(self):
        update(self.projects, self.home)
        os.remove(os.path.join(self.projects, '-work-repo', f'{SID}.jsonl'))
        os.remove(os.path.join(self.projects, '-work-repo', SID, 'subagents', 'agent-a1.jsonl'))
        ledger, _ = update(self.projects, self.home)
        self.assertIn(SID, ledger['sessions'])
        self.assertEqual(ledger['files'], {})


class CommandsCase(unittest.TestCase):

    def test_destructive_and_verification_commands(self):
        for command in ('git push --force origin main', 'git push -f', 'git reset --hard HEAD~1', 'rm -rf /',
                        'rm -rf ~', 'git commit --no-verify -m x', 'kubectl delete pod x', 'git clean -fd'):
            self.assertRegex(command, DESTRUCTIVE_RE)
        for command in ('rm -rf /tmp/build', 'rm -rf node_modules', 'psql -c "DROP DATABASE test_x"', 'git push'):
            self.assertNotRegex(command, DESTRUCTIVE_RE)
        for command in ('pytest -x', 'docker compose exec web pytest', 'npm test', 'npm run lint', 'go test ./...',
                        'python3 -m unittest', './gradlew test', 'docker/ci.sh run_ruff'):
            self.assertRegex(command, VERIFY_RE)
        self.assertNotRegex('git status', VERIFY_RE)


if __name__ == '__main__':
    unittest.main()
