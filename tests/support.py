"""Fixtures shared by the tests: transcript records, fake sessions, page text helpers."""

import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from harness_rpg.constants import COUNT_KEYS

SID ='11111111-2222-3333-4444-555555555555'
UUID_SERVER = '7c2e4f19-3a8d-4b6e-9f05-d1a6c8b3e274'
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def ts(minutes):
    """Timestamp a given number of minutes after 09:00 UTC on the NOW day."""
    return (datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)).isoformat()


def human(text, minutes):
    return {'type': 'user', 'timestamp': ts(minutes), 'cwd': '/work/repo', 'origin': {'kind': 'human'},
            'message': {'role': 'user', 'content': text}}


def tool_use(tool_id, name, tool_input, minutes, sidechain=False):
    return {'type': 'assistant', 'timestamp': ts(minutes), 'isSidechain': sidechain,
            'message': {'content': [{'type': 'tool_use', 'id': tool_id, 'name': name, 'input': tool_input}]}}


def tool_result(tool_id, minutes, is_error=False, **extra):
    record = {'type': 'user', 'timestamp': ts(minutes),
              'message': {'content': [{'type': 'tool_result', 'tool_use_id': tool_id, 'is_error': is_error}]}}
    record.update(extra)
    return record


MAIN_RECORDS = [
    {'type': 'permission-mode', 'permissionMode': 'plan', 'sessionId': SID},
    human('посмотри баг', 0),
    tool_use('t1', 'Skill', {'skill': 'plug:My_Skill'}, 1),
    tool_result('t1', 1),
    tool_use('t2', 'mcp__notebook__pages_write', {}, 2),
    tool_result('t2', 2),
    tool_use('t3', 'Edit', {'file_path': '/x'}, 3),
    tool_result('t3', 3, is_error=True),
    tool_use('t4', 'Bash', {'command': 'git commit -m "x"'}, 4),
    tool_result('t4', 4, toolDenialKind='user-rejected'),
    tool_use('t5', 'mcp__ccd_session__mark_chapter', {}, 5),
    tool_result('t5', 5),
    {'type': 'user', 'timestamp': ts(6), 'message': {'content': [{'type': 'text', 'text': '[Request interrupted by user]'}]}},
    {'type': 'system', 'subtype': 'compact_boundary', 'timestamp': ts(7)},
    human('<command-name>/exit</command-name>', 8),
    human('<command-name>/pair-coder</command-name>\n<command-args>почини задачу</command-args>', 9),
    {'type': 'user', 'timestamp': ts(10), 'isMeta': True, 'message': {'content': 'skill body'}},
    {'type': 'assistant', 'timestamp': ts(11), 'attributionSkill': 'anthropic-skills:auto_loaded',
     'message': {'content': [{'type': 'text', 'text': 'ok'}]}},
    tool_use('t6', 'Write', {'file_path': '/work/repo/a.PY'}, 12),
    tool_result('t6', 12),
    tool_use('t7', 'Bash', {'command': 'git push --force origin main'}, 13),
    tool_result('t7', 13),
    tool_use('t8', 'Bash', {'command': 'docker compose exec web pytest -q'}, 14),
    tool_result('t8', 14),
    {'type': 'attachment', 'timestamp': ts(15), 'attachment': {
        'type': 'hook_success', 'hookEvent': 'PostToolUse', 'hookName': 'PostToolUse:Write',
        'command': '~/.claude/hooks/secret-lint.sh'}},
    {'type': 'attachment', 'timestamp': ts(16), 'attachment': {
        'type': 'hook_success', 'hookEvent': 'PostToolUse', 'hookName': 'PostToolUse:Write',
        'command': '~/.claude/hooks/secret-lint.sh'}},
    {'type': 'attachment', 'timestamp': ts(17), 'attachment': {'type': 'hook_success', 'hookEvent': 'Stop'}},
    {'type': 'user', 'timestamp': datetime(2026, 9, 30, 2, 0).astimezone().isoformat(), 'origin': {'kind': 'human'},
     'permissionMode': 'auto', 'message': {'content': 'ночная работа'}},
    # One reply split into two records repeating its usage: the last one is final and counts once.
    {'type': 'assistant', 'timestamp': ts(18), 'message': {'id': 'm1', 'content': [{'type': 'text', 'text': 'a'}],
     'usage': {'input_tokens': 10, 'output_tokens': 1, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 1000}}},
    {'type': 'assistant', 'timestamp': ts(18), 'message': {'id': 'm1', 'content': [{'type': 'text', 'text': 'b'}],
     'usage': {'input_tokens': 10, 'output_tokens': 5, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 1000}}},
]
SUB_RECORDS = [
    {'type': 'assistant', 'timestamp': ts(12), 'isSidechain': True, 'message': {'id': 's1m', 'content': [],
     'usage': {'input_tokens': 2, 'output_tokens': 3, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}}},
    tool_use('s1', f'mcp__{UUID_SERVER}__logs_search', {}, 12, sidechain=True),
    tool_result('s1', 12, is_error=True, isSidechain=True),
]


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record) + '\n')


# Tooling words the page must not use: it speaks about the hero. The hero's own name is the only exception.
# The English page says talents, not skills: there the RPG word and the tool's word are the same.
TOOLING_WORDS = ('харнес', 'агент', 'клод', 'промпт', 'хук', 'скил', 'сесси', 'токен', 'claude')
TOOLING_WORDS_EN = ('harness', 'agent', 'claude', 'prompt', 'hook', 'skill', 'session', 'token')
CYRILLIC = re.compile(r'[\u0400-\u052f]')


def tooling_words_in(text, words=TOOLING_WORDS):
    """Tooling words found in a text, case-insensitive."""
    lowered = text.lower()
    return sorted(word for word in words if word in lowered)


def string_values(node):
    """Every string value of a JSON-like tree; keys are names of fields, not words of the page."""
    if isinstance(node, dict):
        for value in node.values():
            yield from string_values(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from string_values(value)
    elif isinstance(node, str):
        yield node


def text_blocks(template, name):
    """The ru and en blocks of a texts dictionary of the template: {lang: [lines]}."""
    start = template.index(f'const {name} = {{')
    end = template.index('\n};', start)
    blocks, current = {}, None
    for line in template[start:end].splitlines()[1:]:
        match = re.match(r'^  (ru|en): \{$', line)
        if match:
            current = blocks.setdefault(match.group(1), [])
        elif line == '  },':
            current = None
        elif current is not None:
            current.append(line)
    return blocks


def fake_session(day='2026-09-30', **fields):
    """Minimal ledger session with one human turn on the given day."""
    counts = {key: 0 for key in COUNT_KEYS}
    counts.update(fields.pop('counts', {}))
    counts.setdefault('human_turns', 1)
    counts['human_turns'] = max(counts['human_turns'], 1)
    session = {
        'id': fields.pop('id', day), 'project': '/p', 'start': f'{day}T10:00:00+00:00', 'end': f'{day}T11:00:00+00:00',
        'active_seconds': 0, 'days': [day], 'plan_mode': False, 'counts': counts, 'tools': {}, 'skills': {},
        'mcp': {}, 'night_days': [], 'extensions': [], 'modes': [], 'hooks': {}, 'langs': {'ru': 1, 'other': 0},
    }
    session.update(fields)
    return session


# The same session as MAIN_RECORDS, written by a person who works in English.
ENGLISH_RECORDS = [
    human('look at the bug', 0) if record.get('message', {}).get('content') == 'посмотри баг'
    else {**record, 'message': {'content': 'night work'}} if record.get('message', {}).get('content') == 'ночная работа'
    else human('<command-name>/pair-coder</command-name>\n<command-args>fix the task</command-args>', 9)
    if 'pair-coder' in str(record.get('message', {}).get('content')) else record
    for record in MAIN_RECORDS
]


class TempDirCase(unittest.TestCase):
    """A temporary Claude Code config directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        env = mock.patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': self.tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self.tmp.cleanup)


class TranscriptsCase(TempDirCase):
    """One session in the transcripts directory: the main transcript of `records` and a subagent's."""

    records = MAIN_RECORDS

    def setUp(self):
        super().setUp()
        self.projects = os.path.join(self.tmp.name, 'projects')
        self.home = os.path.join(self.tmp.name, 'home')
        project = os.path.join(self.projects, '-work-repo')
        write_jsonl(os.path.join(project, f'{SID}.jsonl'), self.records)
        write_jsonl(os.path.join(project, SID, 'subagents', 'agent-a1.jsonl'), SUB_RECORDS)


class SessionsCase(TempDirCase):
    """Ledger sessions made by hand with fake_session, and an empty catalog."""

    def setUp(self):
        super().setUp()
        self.catalog = {'skills': {}, 'mcp': {}}
