"""Every constant and threshold of the skill. What they mean is described in reference.md."""

import re

# ---------------------------------------------------------------------------
# Tunable constants. Every formula that uses them is described in reference.md.
# ---------------------------------------------------------------------------

XP_SESSION_BASE = 10
XP_PER_HUMAN_TURN = 2
XP_HUMAN_TURNS_CAP = 40
XP_PER_ACTIVE_DAY = 20
LEVEL_BASE_XP = 100
LEVEL_GROWTH = 1.15

HALF_LIFE_DAYS = 30
DAILY_SESSIONS_CAP = 3

# Thresholds of the skill ranks and gear rarities; their names are in TEXTS.
SKILL_RANKS = (0, 2, 4, 8, 15, 30, 60)
RARITIES = ((0, 'common'), (3, 'uncommon'), (8, 'rare'), (20, 'epic'), (45, 'legendary'))

ATTR_WINDOW_DAYS = 30
ACTIVE_GAP_CAP_SECONDS = 600
HYBRID_RATIO = 0.75
RUSTED_CLASS_THRESHOLD = 0.5

# Attribute curve parameters: a metric equal to its midpoint scores 10.5 of 20.
STR_EDITS_MID = 5
DEX_SUCCESS_LO = 0.85
CON_HOURS_MID = 1.5
CON_COMPACTIONS_MID = 3
CON_STREAK_MID = 7
INT_BREADTH_MID = 20
INT_DOCS_MID = 1
WIS_AUTONOMY_MID = 8
WIS_FRICTION_HI = 0.3
WIS_PLAN_SHARE_MID = 0.2
CHA_ACTIONS_MID = 3
ATTRIBUTES = ('str', 'dex', 'con', 'int', 'wis', 'cha')

# ---------------------------------------------------------------------------
# Game structure: keys, thresholds and events. Every word of the game is in TEXTS below.
# ---------------------------------------------------------------------------

SCHOOLS = ('smith', 'ranger', 'engineer', 'alchemist', 'bard', 'summoner', 'wanderer')
# Bumped when a school's meaning narrows: skills of a rechecked school marked under an older version are asked
# once more. Version 2: the bard keeps only text written for people; text as the medium of work with the agent
# (prompts, notes and memory for agents, plans, task descriptions) goes to the work it serves.
SCHOOL_RULES_VERSION = 2
RECHECKED_SCHOOLS = frozenset(('bard',))
# Equipment slots by MCP purpose. One item per slot, the strongest; the rest and 'bag' items go to the bag.
GEAR_SLOTS = ('helmet', 'amulet', 'horn', 'boots', 'grimoire', 'ring', 'gloves', 'cloak')
SLOT_KEYS = frozenset(GEAR_SLOTS)
BAG = 'bag'
ALIAS_MAX_LENGTH = 40
ALIAS_NAME_TOKEN_MIN = 4

# Achievements are earned for all time, each in three medals with growing thresholds, so a light user
# still gets bronze somewhere and a heavy one keeps a gold to chase. The order is prestige: the title is
# the achievement with the best medal, ties broken by this order.
NIGHT_END_HOUR = 5
# key, bronze/silver/gold thresholds.
ACHIEVEMENTS = (
    ('phoenix', (1, 3, 6)),
    ('flawless', (30, 150, 400)),
    ('warlord', (2, 10, 25)),
    ('marathon', (1, 2, 4)),
    ('trek', (1, 6, 12)),
    ('tireless', (3, 30, 90)),
    ('versatile', (2, 5, 7)),
    ('strategist', (5, 50, 200)),
    ('polyglot', (3, 12, 25)),
    ('explorer', (3, 15, 40)),
    ('night_owl', (1, 10, 30)),
)
# Single thresholds of the pre-medal version: old registry entries and snapshots map to a medal by them.
LEGACY_ACH_THRESHOLDS = {
    'phoenix': 3, 'flawless': 300, 'warlord': 10, 'marathon': 6, 'tireless': 30, 'versatile': 6,
    'strategist': 100, 'polyglot': 15, 'explorer': 25, 'night_owl': 10,
}

# Auras come from hooks, grouped by hook event. Strength is the share of recent sessions where the aura
# fired, so a hook that fires hundreds of times per session is no stronger than one that fires once.
AURAS = (
    ('guard', ('PreToolUse',)),
    ('temper', ('PostToolUse', 'PostToolUseFailure')),
    ('mentor', ('UserPromptSubmit',)),
    ('dawn', ('SessionStart', 'Setup')),
    ('herald', ('Stop', 'SubagentStop', 'SubagentStart', 'Notification')),
    ('seal', ('PermissionRequest',)),
    ('memory', ('PreCompact', 'PostCompact', 'SessionEnd')),
)
AURA_TIERS = (0.0, 0.1, 0.3, 0.6, 0.9)

# Treasury: gold is tokens weighted like their price (output is the dearest, cache reads nearly free),
# summed over the recent window. Model prices differ, so the weights are model-agnostic on purpose.
GOLD_WEIGHTS = {'input': 1.0, 'cache_write': 1.25, 'cache_read': 0.1, 'output': 5.0}
GOLD_TIERS = (0, 2e6, 10e6, 50e6, 250e6, 1e9)
# Campfire: a compaction is a halt where the hero retells the road so far and walks on lighter.
CAMP_TIERS = (0, 1, 4, 15)
# The top tiers are open: every further ×factor above the last threshold adds a level (II, III, ...).
GOLD_OPEN_FACTOR = 4
CAMP_OPEN_FACTOR = 2
ROMAN = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X')
TOKEN_KEYS = (
    ('input', 'input_tokens'),
    ('output', 'output_tokens'),
    ('cache_write', 'cache_creation_input_tokens'),
    ('cache_read', 'cache_read_input_tokens'),
)

# Alignment: order (rules, planning, strict permissions) against chaos, care (checks, questions) against harm.
PERMISSION_STRICTNESS = {
    'default': 1.0, 'plan': 1.0, 'acceptEdits': 0.5, 'auto': 0.5, 'dontAsk': 0.25, 'bypassPermissions': 0.0,
}
PERMISSION_STRICTNESS_UNKNOWN = 0.5
LAW_RULES_MID = 300
LAW_PLAN_SHARE_FULL = 0.4
LAW_LAWFUL_FROM = 0.6
LAW_CHAOTIC_UPTO = 0.35
MORAL_EVIL_WEIGHT = 3
MORAL_GOOD_FROM = 0.35
MORAL_EVIL_BELOW = 0.0
# The nine cells of the alignment grid, row by row: good, neutral, evil.
ALIGNMENTS = tuple((law, moral) for moral in ('good', 'neutral', 'evil') for law in ('lawful', 'neutral', 'chaotic'))

# ---------------------------------------------------------------------------
# Page language: the language the human mostly writes in. Russian gets the Russian page, anything else English.
# ---------------------------------------------------------------------------

LANGS = ('ru', 'en')
# A human message votes only with at least this many letters left after cleaning.
LANG_MIN_LETTERS = 2
# A message is Russian with this share of Russian letters, or with this many of them: identifiers and logs pasted
# without a fence must not outweigh a Russian sentence, and non-Russian speakers hardly ever type Cyrillic.
LANG_RU_SHARE = 0.3
LANG_RU_LETTERS = 12
# Once a page has a language, the other side needs this share of the votes to switch it: no flicker at 50/50.
LANG_SWITCH_SHARE = 0.6
# Without a single vote.
LANG_FALLBACK = 'en'
RUSSIAN_LETTERS = frozenset('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')

# ---------------------------------------------------------------------------
# Transcript parsing rules.
# ---------------------------------------------------------------------------

LEDGER_VERSION = 8
# Version of the public snapshot shape; the template must keep rendering every older version.
# 13: the page language ('lang') and the key of the title achievement ('title_key').
PUBLIC_SCHEMA_VERSION = 13
# Achievements whose metric was recounted, with the snapshot schema it happened in: medals recorded before it
# (in the registry or in archived snapshots) came from the wrong count and are not kept.
# Marathon: 11 — long pauses stopped counting as work; 12 — it became the longest stretch without pauses.
ACH_RECOUNTED = {'marathon': 12}
DATA_PLACEHOLDER = '/*__HISTORY__*/null'
# The oldest Python the script runs on: the one macOS ships as /usr/bin/python3.
MIN_PYTHON = (3, 9)
# Hook scripts are named by their file; an inline command by its program, past the variables set before it
# (`TOKEN=… curl …`), whose values may be secrets.
HOOK_SCRIPT_RE = re.compile(r'[\w.~/-]+\.(?:py|sh|bash|zsh|js|mjs|cjs|ts|rb|pl|php)\b')
ENV_ASSIGNMENT_RE = re.compile(r'^[A-Za-z_]\w*=')
HOOK_NAME_MAX_LENGTH = 40
# Findings the agent writes for the insights block.
FINDING_TONES = frozenset(('rise', 'fall', 'note'))
FINDINGS_MAX = 8
FINDING_TITLE_MAX_LENGTH = 70
FINDING_TEXT_MAX_LENGTH = 400
DIGEST_TOP_TOOLS = 8

EDIT_TOOLS = frozenset(('Edit', 'Write', 'MultiEdit', 'NotebookEdit'))
DOC_TOOLS = frozenset(('WebFetch', 'WebSearch'))
PLAN_TOOLS = frozenset(('EnterPlanMode', 'ExitPlanMode'))
DENIAL_KINDS = frozenset(('user-rejected', 'automode-blocked', 'permission-rule'))
# Harness-internal MCP servers of the Claude desktop app: plumbing, not gear.
EXCLUDED_MCP_PREFIXES = ('ccd_',)
# Host tools that come as MCP servers but are no gear: the inline widgets the skill itself draws its chat card with,
# and the app's own terminal pane.
EXCLUDED_MCP_SERVERS = frozenset(('visualize', 'terminal'))
BUILTIN_COMMANDS = frozenset((
    'add-dir', 'agents', 'auto-mode-setup', 'bashes', 'btw', 'bug', 'clear', 'color', 'compact', 'config',
    'context', 'copy', 'cost', 'desktop', 'doctor', 'effort', 'exit', 'export', 'extra-usage', 'fast',
    'feedback', 'help', 'hooks', 'ide', 'install-github-app', 'keybindings', 'login', 'logout', 'mcp',
    'memory', 'migrate-installer', 'mobile', 'model', 'output-style', 'permissions', 'plan', 'plugin',
    'plugins', 'privacy-settings', 'release-notes', 'reload-plugins', 'reload-skills', 'remote-control',
    'rename', 'resume', 'rewind', 'sandbox', 'stats', 'status', 'statusline', 'tasks', 'teleport',
    'terminal-setup', 'theme', 'todos', 'upgrade', 'usage', 'vim',
))
COUNT_KEYS = (
    'human_turns', 'tool_calls', 'tool_errors', 'edits', 'edit_errors', 'interrupts', 'denials',
    'compactions', 'doc_lookups', 'commits', 'prs', 'outbound', 'destructive', 'verifications',
)
EXTENSION_MAX_LENGTH = 10

COMMAND_NAME_RE = re.compile(r'<command-name>(.*?)</command-name>', re.S)
COMMIT_RE = re.compile(r'\bgit\s+(?:-C\s+\S+\s+)?commit\b')
PR_RE = re.compile(r'\b(?:gh\s+pr\s+create|glab\s+mr\s+create)\b')
DOCS_BASH_RE = re.compile(r'\bctx7\b')
# Commands that destroy work or history; they pull the alignment towards evil. Everyday cleanup
# (rm -rf of build and temp dirs, DROP of test databases) is deliberately left out: it is noise.
DESTRUCTIVE_RE = re.compile(
    r'\brm\s+-\w*\s+(?:/|~/?|\*|\$HOME/?)(?=\s|$|;|&|\|)'
    r'|\bgit\s+reset\s+--hard\b'
    r'|\bgit\s+push\b[^\n;&|]*\s(?:--force(?:-with-lease)?|-f)\b'
    r'|\bgit\s+clean\s+-\w*f'
    r'|\bkubectl\s+delete\b'
    r'|\bdocker\s+(?:system|volume|image)\s+prune\b'
    r'|--no-verify\b',
)
# Commands that check the work: tests, linters, type checkers.
VERIFY_RE = re.compile(
    r'\b(?:pytest|unittest|jest|vitest|ruff|mypy|eslint|tsc|flake8|pylint|rubocop|golangci-lint)\b'
    r'|\b(?:npm|yarn|pnpm|bun)\s+(?:run\s+)?(?:test|lint|check)\b'
    r'|\b(?:go|cargo|mvn|make|mix|dotnet|swift)\s+test\b'
    r'|\bgradlew?\b[^\n;&|]*\b(?:test|check|lint)\b'
    r'|\bci\.sh\b',
    re.I,
)
OUTBOUND_RE = re.compile(r'send|post|reply|comment|create|write|publish|update|upload|share', re.I)
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
PLUGIN_SERVER_RE = re.compile(r'^plugin_[^_]+_(.+)$')
LATIN_RE = re.compile(r'[A-Za-z]')
CYRILLIC_RE = re.compile(r'[\u0400-\u052f]')
NAME_SPLIT_RE = re.compile(r'[^0-9a-zа-яё]+')
# What a human message carries besides the human's own words, cut before its language is counted: tagged blocks
# (reminders, shell output, command names, IDE context) except the arguments of a command, pasted content up to its
# closing tag or the end, code, links, paths and attachment markers.
COMMAND_ARGS_RE = re.compile(r'<command-args>(.*?)</command-args>', re.S)
PASTED_RE = re.compile(r'<pasted_content\b.*?(?:</pasted_content>|\Z)', re.S)
TAG_BLOCK_RE = re.compile(r'<([A-Za-z][\w:-]*)\b[^>]*>.*?</\1\s*>', re.S)
TAG_RE = re.compile(r'</?[A-Za-z][^>\n]*>')
CODE_BLOCK_RE = re.compile(r'```.*?(?:```|\Z)', re.S)
INLINE_CODE_RE = re.compile(r'`[^`\n]*`')
URL_RE = re.compile(r'\b(?:https?|file)://\S+')
PATH_RE = re.compile(r'\S*[/\\]\S*')
MARKER_RE = re.compile(r'\[(?:Image|Pasted text) #\d+[^\]]*\]')

# ---------------------------------------------------------------------------
# Chat card: the portrait code is cut from the template between the markers.
# ---------------------------------------------------------------------------

AVATAR_BEGIN = '// ==== Avatar: begin ===='
AVATAR_END = '// ==== Avatar: end ===='
CARD_SKILLS = 3
CARD_GEAR = 4
