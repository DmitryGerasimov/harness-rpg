"""Session parsing: Claude Code transcripts into ledger records, and the ledger update."""

import glob
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from .constants import (
    ACTIVE_GAP_CAP_SECONDS, BUILTIN_COMMANDS, COMMAND_NAME_RE, COMMIT_RE, COUNT_KEYS, DENIAL_KINDS, DESTRUCTIVE_RE,
    DOCS_BASH_RE, DOC_TOOLS, EDIT_TOOLS, ENV_ASSIGNMENT_RE, EXTENSION_MAX_LENGTH, HOOK_NAME_MAX_LENGTH, HOOK_SCRIPT_RE,
    LEDGER_VERSION, NIGHT_END_HOUR, OUTBOUND_RE, PLAN_TOOLS, PR_RE, TOKEN_KEYS, VERIFY_RE,
)
from .lang import message_lang
from .names import is_plumbing, normalize_skill, split_mcp
from .storage import ledger_path, load_json, save_json


def parse_ts(value):
    """Parse an ISO timestamp into an aware datetime, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def local_day(moment):
    """Local calendar day of an aware datetime as an ISO string."""
    return moment.astimezone().date().isoformat()


def hook_script(command):
    """File name of the script a hook runs, or the program of an inline command; None without a command."""
    if not isinstance(command, str) or not command.strip():
        return None
    match = HOOK_SCRIPT_RE.search(command)
    if match:
        name = match.group(0)
    else:
        name = next((word for word in command.split() if not ENV_ASSIGNMENT_RE.match(word)), '')
    name = os.path.basename(name)
    return name[:HOOK_NAME_MAX_LENGTH] or None


class SessionParser:

    """Accumulate one session's metrics from its main and subagent transcripts."""

    def __init__(self, sid):
        self.sid = sid
        self.project = None
        self.entrypoint = None
        self.timestamps = []
        # Moments of real work, the human's turns and the agent's replies and tool results; bookkeeping records
        # (away summaries, queue operations, reminders) would stitch idle minutes into active time.
        self.work_stamps = []
        self.human_days = set()
        self.counts = Counter()
        self.plan_mode = False
        self.tools = Counter()
        self.skills = {}
        self.mcp = {}
        self.night_days = set()
        self.extensions = set()
        self.modes = set()
        self.hooks = Counter()
        self.hook_names = defaultdict(Counter)
        # Language votes of the human's messages: counts only, never the text.
        self.langs = Counter()
        # One model reply is split into several records that repeat its usage: keep the last per message id.
        self.usage = {}

    def parse_file(self, path, is_sub):
        """Feed every JSON line of one transcript file; a file that vanished meanwhile gives nothing."""
        tool_names = {}
        try:
            handle = open(path, encoding='utf-8', errors='replace')
        except OSError:
            return
        with handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                # The transcript format is Claude Code's, not ours, and it changes: a record with fields of an
                # unexpected shape is skipped like a broken line instead of failing the whole update.
                try:
                    self._record(record, is_sub, tool_names)
                except (AttributeError, KeyError, TypeError, ValueError):
                    continue

    def _record(self, record, is_sub, tool_names):
        moment = parse_ts(record.get('timestamp'))
        kind = record.get('type')
        if not is_sub:
            if moment:
                self.timestamps.append(moment)
                if kind in ('user', 'assistant'):
                    self.work_stamps.append(moment)
            if self.project is None and isinstance(record.get('cwd'), str) and record['cwd']:
                self.project = record['cwd']
            if self.entrypoint is None and isinstance(record.get('entrypoint'), str) and record['entrypoint']:
                self.entrypoint = record['entrypoint']
            if record.get('permissionMode'):
                self.modes.add(str(record['permissionMode']))
            if record.get('permissionMode') == 'plan':
                self.plan_mode = True
            if kind == 'system' and record.get('subtype') == 'compact_boundary':
                self.counts['compactions'] += 1
            attachment = record.get('attachment') if kind == 'attachment' else None
            if isinstance(attachment, dict) and attachment.get('hookEvent'):
                event = str(attachment['hookEvent'])
                self.hooks[event] += 1
                # Only the script's file name is kept, never the command line with its arguments.
                name = hook_script(attachment.get('command'))
                if name:
                    self.hook_names[event][name] += 1
        if record.get('attributionSkill'):
            # The assistant worked under a skill that may have been loaded without a Skill call.
            self._skill(record['attributionSkill'], moment, invoked=False)
        message = record.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if kind == 'assistant' and isinstance(message, dict) and isinstance(message.get('usage'), dict):
            key = message.get('id') or record.get('uuid') or len(self.usage)
            self.usage[key] = message['usage']
        if kind == 'assistant' and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    self._tool_use(block, moment, is_sub, tool_names)
        elif kind == 'user':
            self._user(record, content, moment, is_sub, tool_names)

    def _tool_use(self, block, moment, is_sub, tool_names):
        name = block.get('name') or ''
        tool_input = block.get('input') if isinstance(block.get('input'), dict) else {}
        tool_names[block.get('id')] = name
        if name == 'Skill':
            self._skill(tool_input.get('skill'), moment, invoked=True)
        mcp = split_mcp(name)
        excluded = bool(mcp) and is_plumbing(mcp[0])
        if mcp and not excluded:
            self._mcp(mcp[0], mcp[1], moment)
        if is_sub:
            return
        self.counts['tool_calls'] += 1
        if mcp:
            if not excluded and OUTBOUND_RE.search(mcp[1]):
                self.counts['outbound'] += 1
            if 'context7' in mcp[0].lower():
                self.counts['doc_lookups'] += 1
            return
        self.tools[name] += 1
        if name in EDIT_TOOLS:
            self.counts['edits'] += 1
            path = str(tool_input.get('file_path') or tool_input.get('notebook_path') or '')
            extension = os.path.splitext(path)[1].lower()
            if 1 < len(extension) <= EXTENSION_MAX_LENGTH:
                self.extensions.add(extension)
        elif name in DOC_TOOLS:
            self.counts['doc_lookups'] += 1
        elif name in PLAN_TOOLS:
            self.plan_mode = True
        elif name == 'Bash':
            command = str(tool_input.get('command') or '')
            if COMMIT_RE.search(command):
                self.counts['commits'] += 1
            if PR_RE.search(command):
                self.counts['prs'] += 1
            if DOCS_BASH_RE.search(command):
                self.counts['doc_lookups'] += 1
            if DESTRUCTIVE_RE.search(command):
                self.counts['destructive'] += 1
            if VERIFY_RE.search(command):
                self.counts['verifications'] += 1

    def _user(self, record, content, moment, is_sub, tool_names):
        texts = []
        has_result = False
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_result':
                    has_result = True
                    if not is_sub and block.get('is_error'):
                        self.counts['tool_errors'] += 1
                        if tool_names.get(block.get('tool_use_id')) in EDIT_TOOLS:
                            self.counts['edit_errors'] += 1
                elif block.get('type') == 'text':
                    texts.append(block.get('text') or '')
        if is_sub or record.get('isSidechain'):
            return
        denial = record.get('toolDenialKind')
        if denial in DENIAL_KINDS:
            self.counts['denials'] += 1
        elif denial == 'interrupted':
            self.counts['interrupts'] += 1
        if has_result or record.get('isMeta') or record.get('isCompactSummary') or record.get('scheduledTaskId'):
            return
        text = '\n'.join(texts).strip()
        if not text:
            return
        if text.startswith('[Request interrupted'):
            self.counts['interrupts'] += 1
            return
        commands = [command.strip() for command in COMMAND_NAME_RE.findall(text)]
        user_commands = [command for command in commands if command.lstrip('/').lower() not in BUILTIN_COMMANDS]
        for command in user_commands:
            self._skill(command, moment, invoked=True)
        if (commands and not user_commands) or text.startswith('<local-command'):
            return
        origin = record.get('origin')
        origin_kind = origin.get('kind') if isinstance(origin, dict) else None
        if origin_kind is not None:
            is_human = origin_kind == 'human'
        else:
            is_human = not text.startswith('<') or bool(user_commands)
        if is_human:
            self.counts['human_turns'] += 1
            # A suggested prompt the human accepted was written by the agent: it is a turn, not a vote.
            vote = None if record.get('promptSource') == 'suggestion_accepted' else message_lang(text)
            if vote:
                self.langs[vote] += 1
            if moment:
                self.human_days.add(local_day(moment))
                local = moment.astimezone()
                if local.hour < NIGHT_END_HOUR:
                    self.night_days.add(local.date().isoformat())

    def _skill(self, raw_name, moment, invoked):
        key, display = normalize_skill(raw_name)
        if not key:
            return
        entry = self.skills.setdefault(key, {'display': display, 'n': 0, 'day': None})
        if invoked:
            entry['n'] += 1
        self._touch(entry, moment)

    def _mcp(self, server, tool, moment):
        entry = self.mcp.setdefault(server, {'n': 0, 'day': None, 'tools': {}})
        entry['n'] += 1
        entry['tools'][tool] = entry['tools'].get(tool, 0) + 1
        self._touch(entry, moment)

    @staticmethod
    def _touch(entry, moment):
        if moment is None:
            return
        day = local_day(moment)
        if entry['day'] is None or day < entry['day']:
            entry['day'] = day

    def result(self):
        """Serializable per-session aggregate for the ledger."""
        stamps = sorted(self.timestamps)
        work = sorted(self.work_stamps)
        active = 0.0
        stretch = longest = 0.0
        for previous, current in zip(work, work[1:]):
            # The hero's time: the human's and the agent's alike; a longer pause is a break and counts not at all.
            gap = (current - previous).total_seconds()
            if gap <= ACTIVE_GAP_CAP_SECONDS:
                active += gap
                stretch += gap
                longest = max(longest, stretch)
            else:
                stretch = 0.0
        fallback_day = local_day(stamps[0]) if stamps else None
        for entry in list(self.skills.values()) + list(self.mcp.values()):
            if entry['day'] is None:
                entry['day'] = fallback_day
        for entry in self.mcp.values():
            entry['tools'] = dict(sorted(entry['tools'].items()))
        tokens = {name: 0 for name, _ in TOKEN_KEYS}
        for usage in self.usage.values():
            for name, field in TOKEN_KEYS:
                value = usage.get(field)
                tokens[name] += value if isinstance(value, int) else 0
        return {
            'id': self.sid,
            'project': self.project,
            'entrypoint': self.entrypoint,
            'start': stamps[0].isoformat() if stamps else None,
            'end': stamps[-1].isoformat() if stamps else None,
            'active_seconds': round(active),
            # The longest run of work where no pause reaches ACTIVE_GAP_CAP_SECONDS.
            'longest_stretch': round(longest),
            'days': sorted(self.human_days),
            'plan_mode': self.plan_mode,
            'counts': {key: self.counts[key] for key in COUNT_KEYS},
            'tools': dict(sorted(self.tools.items())),
            'skills': dict(sorted(self.skills.items())),
            'mcp': dict(sorted(self.mcp.items())),
            'night_days': sorted(self.night_days),
            'extensions': sorted(self.extensions),
            'modes': sorted(self.modes),
            'hooks': dict(sorted(self.hooks.items())),
            'hook_names': {event: dict(sorted(names.items())) for event, names in sorted(self.hook_names.items())},
            'tokens': tokens,
            'langs': {key: self.langs[key] for key in ('ru', 'other')},
        }


def parse_session(sid, paths):
    """Parse all transcript files of one session into a ledger record."""
    parser = SessionParser(sid)
    marker = os.sep + 'subagents' + os.sep
    for path in paths:
        parser.parse_file(path, is_sub=marker in path)
    return parser.result()


def session_files(projects_dir):
    """Group transcript files by session id: main file first, then subagent files."""
    groups = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(projects_dir, '*', '*.jsonl'))):
        groups[os.path.basename(path)[:-len('.jsonl')]].append(path)
    pattern = os.path.join(projects_dir, '*', '*', 'subagents', '**', '*.jsonl')
    for path in sorted(glob.glob(pattern, recursive=True)):
        groups[os.path.relpath(path, projects_dir).split(os.sep)[1]].append(path)
    return groups


def fingerprint(path):
    """Change marker of a file: [size, mtime_ns], or None when it vanished."""
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None
    return [stat.st_size, stat.st_mtime_ns]


def update(projects_dir, home):
    """Parse new or changed sessions into the ledger; sessions whose files are gone stay."""
    path = ledger_path(home)
    ledger = load_json(path, {'version': LEDGER_VERSION, 'files': {}, 'sessions': {}})
    if ledger.get('version') != LEDGER_VERSION:
        ledger = {'version': LEDGER_VERSION, 'files': {}, 'sessions': ledger.get('sessions', {})}
    seen_files = {}
    parsed = 0
    for sid, paths in session_files(projects_dir).items():
        prints = {file_path: fingerprint(file_path) for file_path in paths}
        prints = {file_path: value for file_path, value in prints.items() if value is not None}
        seen_files.update(prints)
        known = sid in ledger['sessions']
        if known and all(ledger['files'].get(file_path) == value for file_path, value in prints.items()):
            continue
        ledger['sessions'][sid] = parse_session(sid, list(prints))
        parsed += 1
    # The ledger is written on the first run even without a single session: render needs one.
    if parsed or ledger['files'] != seen_files or not os.path.exists(path):
        ledger['files'] = seen_files
        save_json(path, ledger)
    return ledger, parsed
