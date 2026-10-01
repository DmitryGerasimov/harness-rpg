#!/usr/bin/env python3
"""Synthetic example of the harness-rpg data folder: an imagined average Claude Code user.

Fake transcripts of two months of work go through the real skill pipeline (update, classify, render,
insights) on several irregular runs, the way a person runs the skill, so the archive has a progression.
Projects, skills and MCP servers are popular public ones; no real user's data is involved. The output is
deterministic: the same seed gives the same files on any machine. The same work is built twice: by a person who
writes in Russian (data/, a Russian page) and by one who writes in English (data/en/, an English page).

    python3 data/generate.py
    open data/character.html data/en/character.html
"""

import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
import uuid
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

# Days and hours of the example are fixed to one timezone, so every machine gets the same data.
os.environ['TZ'] = 'Europe/Moscow'
time.tzset()
sys.path.insert(0, os.path.join(HERE, '..', 'skill', 'scripts'))

from harness_rpg.catalog import classify, pending_items  # noqa: E402
from harness_rpg.constants import EDIT_TOOLS  # noqa: E402
from harness_rpg.insights import attach_findings  # noqa: E402
from harness_rpg.page import render  # noqa: E402
from harness_rpg.storage import ledger_path, load_catalog, load_json, save_json  # noqa: E402
from harness_rpg.transcripts import update  # noqa: E402

SEED = 20261001
USER_HOME = '/Users/alex'
MODEL = 'claude-sonnet-4-5'
FIRST_DAY = date(2026, 8, 3)
VACATION = (date(2026, 8, 14), date(2026, 8, 18))
# Local times the person ran the skill: irregular, with a gap of almost two weeks in the middle.
RUNS = (
    datetime(2026, 9, 2, 22, 10), datetime(2026, 9, 4, 21, 40), datetime(2026, 9, 9, 23, 5),
    datetime(2026, 9, 10, 20, 30), datetime(2026, 9, 22, 22, 15), datetime(2026, 9, 27, 13, 20),
    datetime(2026, 10, 1, 12, 40),
)
# Claude Code deletes transcripts older than this (cleanupPeriodDays); the ledger keeps what it has seen.
CLEANUP_DAYS = 30
OUTPUTS = ('achievements.json', 'catalog.json', 'character.html', 'character.json', 'history.json', 'ledger.json')

BASE_CONTEXT = 28000
COMPACT_AT = 600000
WEEKDAY_SESSIONS = (6.5, 7.5, 7.5, 7.0, 6.0, 1.6, 2.4)
START_HOURS = {
    0: 1.0, 1: 0.5, 9: 3, 10: 7, 11: 8, 12: 6, 13: 4, 14: 7, 15: 8, 16: 8, 17: 7, 18: 5, 19: 3, 20: 3, 21: 4,
    22: 3, 23: 2,
}
ENTRYPOINTS = {'cli': 55, 'claude-vscode': 25, 'claude-desktop': 20}
MODES = {'default': 40, 'acceptEdits': 35, 'auto': 20, 'bypassPermissions': 5}
DENIAL_CHANCE = {'default': 0.35, 'acceptEdits': 0.15, 'auto': 0.15, 'bypassPermissions': 0.0, 'plan': 0.35}

CODE = ('shop-api', 'web-app', 'mobile-app', 'data-notebooks', 'recipe-bot')
WORK = CODE + ('infra', 'docs-site')
EVERYWHERE = WORK + ('dotfiles', 'notes')

PROJECTS = {
    'shop-api': {
        'path': 'Projects/shop-api',
        'files': ('src/orders/service.py', 'src/orders/models.py', 'src/payments/stripe_client.py',
                  'tests/test_orders.py', 'tests/test_refunds.py', 'pyproject.toml', 'migrations/0042_refunds.sql'),
        'checks': ('pytest -q', 'pytest tests/test_orders.py -q', 'ruff check .', 'mypy src'),
        'run': ('docker compose up -d db', 'python -m src.manage migrate', 'git log --oneline -5', 'git diff --stat'),
    },
    'web-app': {
        'path': 'Projects/web-app',
        'files': ('src/pages/Checkout.tsx', 'src/components/Cart.tsx', 'src/api/client.ts', 'src/styles/cart.css',
                  'src/hooks/useOrders.ts', 'package.json'),
        'checks': ('npm test', 'npm run lint', 'npx tsc --noEmit', 'npx vitest run src/components'),
        'run': ('npm run dev', 'git status', 'git diff', 'npm install'),
    },
    'infra': {
        'path': 'Projects/infra',
        'files': ('main.tf', 'modules/vpc/main.tf', 'k8s/deployment.yaml', 'k8s/ingress.yaml', 'scripts/deploy.sh'),
        'checks': ('make test',),
        'run': ('terraform plan', 'kubectl get pods -n shop', 'helm list -n shop', 'git status'),
    },
    'mobile-app': {
        'path': 'Projects/mobile-app',
        'files': ('app/src/main/java/shop/CartScreen.kt', 'app/src/main/res/layout/cart.xml',
                  'ios/Shop/CartView.swift', 'app/build.gradle'),
        'checks': ('./gradlew test', 'swift test'),
        'run': ('./gradlew assembleDebug', 'adb devices', 'git status'),
    },
    'docs-site': {
        'path': 'Projects/docs-site',
        'files': ('docs/getting-started.md', 'docs/api/orders.mdx', 'docs/faq.md', 'sidebars.js'),
        'checks': ('npm run lint',),
        'run': ('npm run build', 'git status'),
    },
    'data-notebooks': {
        'path': 'Projects/data-notebooks',
        'files': ('analysis/cohorts.ipynb', 'analysis/retention.ipynb', 'queries/retention.sql', 'etl/load.py'),
        'checks': ('pytest -q',),
        'run': ('python etl/load.py --dry-run', 'git status'),
    },
    'recipe-bot': {
        'path': 'Projects/recipe-bot',
        'files': ('bot.py', 'recipes/scale.py', 'tests/test_scale.py', 'recipes.json'),
        'checks': ('pytest -q',),
        'run': ('python bot.py --check', 'git status'),
    },
    'dotfiles': {
        'path': 'dotfiles',
        'files': ('.zshrc', 'nvim/init.lua', '.gitconfig', 'install.sh'),
        'checks': (),
        'run': ('source ~/.zshrc', 'git status'),
    },
    'notes': {
        'path': 'Documents/notes',
        'files': ('trips/lisbon.md', 'reading.md', 'ideas.md'),
        'checks': (),
        'run': ('ls',),
    },
}
# The person's messages in each language: the same number of them, so both examples draw the very same work.
PROMPTS = {
    'ru': (
        'почини падающий тест', 'добавь возврат заказа', 'разберись, почему растёт время ответа',
        'сделай ревью ветки', 'обнови зависимости', 'напиши миграцию', 'перепиши компонент корзины',
        'посмотри логи ошибки', 'подготовь релиз', 'объясни, как устроен этот модуль', 'ускорь запрос',
        'добавь тесты', 'продолжай', 'да, так и делай', 'а теперь то же для мобильного экрана',
    ),
    'en': (
        'fix the failing test', 'add order refunds', 'find out why the response time grows',
        'review the branch', 'update the dependencies', 'write a migration', 'rewrite the cart component',
        'look at the error logs', 'prepare the release', 'explain how this module works', 'speed up the query',
        'add tests', 'go on', 'yes, do it that way', 'now the same for the mobile screen',
    ),
}
# The agent's short answer and the prompt of the scheduled night run, in the language of the person.
DONE = {'ru': 'Готово.', 'en': 'Done.'}
AUDIT = {'ru': 'Проверь зависимости на уязвимости.', 'en': 'Check the dependencies for vulnerabilities.'}
SUBAGENT_TYPES = ('Explore', 'Explore', 'general-purpose', 'Plan')

# Popular public skills and plugin commands, plus a few personal commands most people have in some form:
# (name as invoked, how, chance per session where it fits, places, first day, last day).
SKILLS = (
    ('superpowers:brainstorming', 'skill', 0.06, WORK, None, None),
    ('superpowers:writing-plans', 'skill', 0.05, WORK, None, None),
    ('superpowers:executing-plans', 'skill', 0.035, WORK, None, None),
    ('superpowers:systematic-debugging', 'skill', 0.08, CODE + ('infra',), None, None),
    ('superpowers:test-driven-development', 'skill', 0.06, ('shop-api', 'web-app', 'recipe-bot'), None, None),
    ('superpowers:requesting-code-review', 'skill', 0.03, CODE, None, None),
    ('superpowers:using-git-worktrees', 'skill', 0.02, CODE, date(2026, 9, 1), None),
    ('superpowers:subagent-driven-development', 'skill', 0.08, WORK, date(2026, 9, 25), None),
    ('commit-commands:commit', 'command', 0.16, WORK + ('dotfiles',), None, None),
    ('commit-commands:commit-push-pr', 'command', 0.05, CODE + ('infra',), None, None),
    ('code-review:code-review', 'command', 0.05, CODE, None, None),
    ('feature-dev:feature-dev', 'command', 0.04, CODE, None, date(2026, 9, 5)),
    ('frontend-design:frontend-design', 'skill', 0.22, ('web-app',), None, None),
    ('webapp-testing', 'skill', 0.12, ('web-app',), None, None),
    ('pdf', 'skill', 0.05, ('notes', 'docs-site', 'data-notebooks'), None, None),
    ('docx', 'skill', 0.06, ('notes', 'docs-site'), None, None),
    ('xlsx', 'skill', 0.18, ('data-notebooks',), None, None),
    ('pptx', 'skill', 0.12, ('notes', 'docs-site'), None, date(2026, 8, 21)),
    ('skill-creator', 'skill', 0.02, WORK + ('dotfiles',), date(2026, 9, 8), None),
    ('mcp-builder', 'skill', 0.05, ('shop-api', 'dotfiles'), date(2026, 9, 24), None),
    ('simplify', 'skill', 0.03, CODE, None, None),
    ('loop', 'command', 0.02, WORK, date(2026, 9, 25), None),
    ('claude-api', 'skill', 0.1, ('recipe-bot',), None, None),
    ('deploy', 'command', 0.07, ('shop-api', 'infra', 'web-app'), None, None),
    ('standup', 'command', 0.07, WORK, None, None),
    ('mobile-release', 'command', 0.25, ('mobile-app',), None, date(2026, 8, 24)),
    ('trip-planner', 'skill', 0.25, ('notes',), None, None),
    ('update-config', 'skill', 0.03, ('dotfiles',) + WORK, None, date(2026, 9, 12)),
)

# Popular MCP servers under the ids Claude Code records: (server, tools with weights, chance per place, first day).
MCP = (
    ('plugin_github_github', {
        'search_code': 6, 'get_file_contents': 6, 'list_pull_requests': 4, 'get_pull_request': 3,
        'create_pull_request': 1, 'add_issue_comment': 1, 'list_issues': 2, 'get_issue': 2, 'list_commits': 2,
        'list_workflow_runs': 2, 'get_workflow_run_logs': 2,
    }, dict.fromkeys(CODE + ('infra', 'docs-site'), 0.3), None),
    ('claude_ai_Linear', {
        'list_issues': 5, 'get_issue': 6, 'update_issue': 3, 'create_comment': 2, 'create_issue': 1, 'list_projects': 1,
    }, dict.fromkeys(WORK, 0.2), None),
    ('sentry', {
        'search_issues': 4, 'get_issue_details': 5, 'search_events': 2, 'get_trace_details': 2, 'find_releases': 1,
    }, {'shop-api': 0.12, 'web-app': 0.1, 'mobile-app': 0.15}, None),
    ('claude_ai_Notion', {
        'notion-search': 5, 'notion-fetch': 6, 'notion-create-pages': 1, 'notion-update-page': 1,
    }, {**dict.fromkeys(WORK, 0.06), 'notes': 0.3}, None),
    ('claude_ai_Slack', {
        'slack_search_public': 3, 'slack_read_thread': 3, 'slack_read_channel': 2, 'slack_send_message': 1,
    }, dict.fromkeys(WORK, 0.06), None),
    ('plugin_playwright_playwright', {
        'browser_navigate': 5, 'browser_snapshot': 6, 'browser_click': 5, 'browser_type': 3,
        'browser_take_screenshot': 3, 'browser_evaluate': 2, 'browser_console_messages': 2,
    }, {'web-app': 0.3, 'docs-site': 0.05}, None),
    ('plugin_context7_context7', {'resolve-library-id': 1, 'query-docs': 2}, dict.fromkeys(CODE, 0.07), None),
    ('postgres', {
        'execute_sql': 8, 'list_schemas': 1, 'list_objects': 2, 'get_object_details': 2, 'explain_query': 2,
    }, {'data-notebooks': 0.5, 'shop-api': 0.08}, None),
    ('google_workspace', {
        'gmail_search_messages': 3, 'gmail_get_message': 3, 'gmail_send_message': 1, 'calendar_list_events': 3,
        'calendar_create_event': 1, 'drive_search_files': 2, 'drive_read_file': 2,
    }, {**dict.fromkeys(WORK, 0.03), 'notes': 0.35}, None),
    ('figma', {
        'get_design_context': 4, 'get_screenshot': 3, 'get_metadata': 2, 'get_variable_defs': 1,
    }, {'web-app': 0.15}, date(2026, 9, 8)),
)

# Hook scripts: event -> (command, first day). Format after edits, a guard before shell commands.
HOOKS = {
    'Stop': ('~/.claude/hooks/notify.sh', FIRST_DAY),
    'PostToolUse': ('~/.claude/hooks/format.sh', date(2026, 8, 10)),
    'SessionStart': ('~/.claude/hooks/load-context.sh', date(2026, 9, 14)),
    'PreToolUse': ('~/.claude/hooks/guard-bash.sh', date(2026, 9, 24)),
}

# What the agent answers to "rpg.py classify": schools and aliases of skills, names, aliases and slots of MCP.
CATALOG_RU = {
    'skills': {
        'brainstorming': {'school': 'summoner', 'alias': 'Круг замыслов'},
        'writing-plans': {'school': 'summoner', 'alias': 'Карта похода'},
        'executing-plans': {'school': 'summoner', 'alias': 'Поход по карте'},
        'systematic-debugging': {'school': 'ranger', 'alias': 'Охота на сбой'},
        'test-driven-development': {'school': 'smith', 'alias': 'Испытание до ковки'},
        'requesting-code-review': {'school': 'smith', 'alias': 'Суд мастеров'},
        'using-git-worktrees': {'school': 'engineer', 'alias': 'Параллельные мастерские'},
        'subagent-driven-development': {'school': 'summoner', 'alias': 'Свита исполнителей'},
        'commit': {'school': 'smith', 'alias': 'Клеймо мастера'},
        'commit-push-pr': {'school': 'engineer', 'alias': 'Отправка обоза'},
        'code-review': {'school': 'smith', 'alias': 'Взгляд оружейника'},
        'feature-dev': {'school': 'smith', 'alias': 'Ковка новинки'},
        'frontend-design': {'school': 'smith', 'alias': 'Резьба по фасаду'},
        'webapp-testing': {'school': 'smith', 'alias': 'Пробный штурм'},
        'pdf': {'school': 'bard', 'alias': 'Чтение пергаментов'},
        'docx': {'school': 'bard', 'alias': 'Переписчик грамот'},
        'xlsx': {'school': 'alchemist', 'alias': 'Таблицы алхимика'},
        'pptx': {'school': 'bard', 'alias': 'Живые гобелены'},
        'skill-creator': {'school': 'summoner', 'alias': 'Создатель приёмов'},
        'mcp-builder': {'school': 'summoner', 'alias': 'Сотворение артефактов'},
        'simplify': {'school': 'smith', 'alias': 'Шлифовка клинка'},
        'loop': {'school': 'summoner', 'alias': 'Вечный караул'},
        'claude-api': {'school': 'smith', 'alias': 'Связь с оракулом'},
        'deploy': {'school': 'engineer', 'alias': 'Поднятие знамени'},
        'standup': {'school': 'bard', 'alias': 'Утренний сбор'},
        'mobile-release': {'school': 'engineer', 'alias': 'Караван в лавки'},
        'trip-planner': {'school': 'wanderer', 'alias': 'Карта странствий'},
        'update-config': {'school': 'summoner', 'alias': 'Настройка шатра'},
    },
    'mcp': {
        'plugin_github_github': {'name': 'GitHub', 'alias': 'Латные перчатки', 'slot': 'gloves', 'families': {}},
        'claude_ai_Linear': {'alias': 'Кольцо замыслов', 'slot': 'ring', 'families': {}},
        'sentry': {'name': 'Sentry', 'alias': 'Шлем часового', 'slot': 'helmet', 'families': {}},
        'claude_ai_Notion': {'alias': 'Фолиант заметок', 'slot': 'grimoire'},
        'claude_ai_Slack': {'alias': 'Рог вестового', 'slot': 'horn'},
        'plugin_playwright_playwright': {'name': 'Playwright', 'alias': 'Сапоги лазутчика', 'slot': 'boots'},
        'plugin_context7_context7': {'alias': 'Свиток справок', 'slot': 'grimoire'},
        'postgres': {'name': 'PostgreSQL', 'alias': 'Амулет глубин', 'slot': 'amulet'},
        'google_workspace': {'name': 'Google Workspace', 'families': {
            'mail': {'name': 'Google Workspace Mail', 'alias': 'Голубиная почта', 'slot': 'horn', 'prefixes': ['gmail']},
            'calendar': {'name': 'Google Workspace Calendar', 'alias': 'Песочные часы', 'slot': 'bag',
                         'prefixes': ['calendar']},
            'files': {'name': 'Google Workspace Drive', 'alias': 'Плащ странника', 'slot': 'cloak', 'prefixes': ['drive']},
        }},
        'figma': {'name': 'Figma', 'alias': 'Палитра зодчего', 'slot': 'bag'},
    },
}

CATALOG_EN = {
    'skills': {
        'brainstorming': {'school': 'summoner', 'alias': 'Circle of Schemes'},
        'writing-plans': {'school': 'summoner', 'alias': 'Map of the March'},
        'executing-plans': {'school': 'summoner', 'alias': 'March by the Map'},
        'systematic-debugging': {'school': 'ranger', 'alias': 'Hunt for the Fault'},
        'test-driven-development': {'school': 'smith', 'alias': 'Trial Before the Forge'},
        'requesting-code-review': {'school': 'smith', 'alias': 'Council of Masters'},
        'using-git-worktrees': {'school': 'engineer', 'alias': 'Twin Workshops'},
        'subagent-driven-development': {'school': 'summoner', 'alias': 'Retinue of Doers'},
        'commit': {'school': 'smith', 'alias': 'Mark of the Master'},
        'commit-push-pr': {'school': 'engineer', 'alias': 'Caravan Dispatch'},
        'code-review': {'school': 'smith', 'alias': 'Eye of the Armorer'},
        'feature-dev': {'school': 'smith', 'alias': 'Forging the New'},
        'frontend-design': {'school': 'smith', 'alias': 'Facade Carving'},
        'webapp-testing': {'school': 'smith', 'alias': 'Mock Siege'},
        'pdf': {'school': 'bard', 'alias': 'Reading Parchments'},
        'docx': {'school': 'bard', 'alias': 'Charter Scribe'},
        'xlsx': {'school': 'alchemist', 'alias': 'Tables of the Alchemist'},
        'pptx': {'school': 'bard', 'alias': 'Living Tapestries'},
        'skill-creator': {'school': 'summoner', 'alias': 'Maker of Techniques'},
        'mcp-builder': {'school': 'summoner', 'alias': 'Forging Artifacts'},
        'simplify': {'school': 'smith', 'alias': 'Blade Polishing'},
        'loop': {'school': 'summoner', 'alias': 'Eternal Watch'},
        'claude-api': {'school': 'smith', 'alias': 'Line to the Oracle'},
        'deploy': {'school': 'engineer', 'alias': 'Raising the Banner'},
        'standup': {'school': 'bard', 'alias': 'Morning Muster'},
        'mobile-release': {'school': 'engineer', 'alias': 'Caravan to the Shops'},
        'trip-planner': {'school': 'wanderer', 'alias': 'Map of Wanderings'},
        'update-config': {'school': 'summoner', 'alias': 'Pitching the Tent'},
    },
    'mcp': {
        'plugin_github_github': {'name': 'GitHub', 'alias': 'Plate Gauntlets', 'slot': 'gloves', 'families': {}},
        'claude_ai_Linear': {'alias': 'Ring of Designs', 'slot': 'ring', 'families': {}},
        'sentry': {'name': 'Sentry', 'alias': 'Helm of the Watchman', 'slot': 'helmet', 'families': {}},
        'claude_ai_Notion': {'alias': 'Tome of Notes', 'slot': 'grimoire'},
        'claude_ai_Slack': {'alias': 'Horn of the Courier', 'slot': 'horn'},
        'plugin_playwright_playwright': {'name': 'Playwright', 'alias': 'Boots of the Scout', 'slot': 'boots'},
        'plugin_context7_context7': {'alias': 'Scroll of Lore', 'slot': 'grimoire'},
        'postgres': {'name': 'PostgreSQL', 'alias': 'Amulet of the Deep', 'slot': 'amulet'},
        'google_workspace': {'name': 'Google Workspace', 'families': {
            'mail': {'name': 'Google Workspace Mail', 'alias': 'Carrier Pigeon', 'slot': 'horn', 'prefixes': ['gmail']},
            'calendar': {'name': 'Google Workspace Calendar', 'alias': 'Hourglass', 'slot': 'bag',
                         'prefixes': ['calendar']},
            'files': {'name': 'Google Workspace Drive', 'alias': 'Cloak of the Wanderer', 'slot': 'cloak',
                      'prefixes': ['drive']},
        }},
        'figma': {'name': 'Figma', 'alias': 'Palette of the Architect', 'slot': 'bag'},
    },
}
CATALOG = {'ru': CATALOG_RU, 'en': CATALOG_EN}

# The agent's findings for the last run, written from "rpg.py digest" of this very data.
FINDINGS_RU = (
    {'title': 'Пять длинных сессий — 39% золота', 'tone': 'fall', 'text': (
        'Пять самых дорогих сессий — по 8–10 часов и 66–78 реплик в shop-api и web-app — съели 210 из 536 млн '
        'золота, а обычная сессия стоит 0,5 млн. 99% входа — перечитывание контекста, так что длинная сессия '
        'дорожает с каждой репликой. Разбивай большую задачу на сессии по подзадачам, план держи в файле, '
        '/compact делай раньше.')},
    {'title': 'Долгие сессии — без помощников', 'tone': 'fall', 'text': (
        'Сабагенты были только в 31 сессии из 193, а из пяти самых дорогих — лишь в одной. Разведку кода и поиск '
        'по проекту отдавай агенту Explore: он читает файлы в своём контексте и возвращает выжимку, и основная '
        'сессия не раздувается.')},
    {'title': 'Трение — в каждой третьей сессии', 'tone': 'fall', 'text': (
        '79 отказов и 21 прерывание на 1212 реплик, трение — в 62 сессиях из 193; 74 сессии шли в режиме default, '
        'где правки и команды ждут подтверждения. Частые безопасные команды — тесты, git status, git diff — вынеси '
        'в allow в настройках, опасные — в deny, а guard-bash.sh останется страховкой.')},
    {'title': 'Правки без проверок', 'tone': 'fall', 'text': (
        'В 56 из 125 сессий с правками не запускались ни тесты, ни линтер. Хук format.sh уже срабатывает после '
        'каждой правки (2481 раз) — добавь в него линтер проекта или повесь тесты на Stop-хук, и проверка '
        'перестанет зависеть от памяти агента.')},
    {'title': 'Документацию ищут в вебе, а не в context7', 'tone': 'note', 'text': (
        '202 WebSearch и 188 WebFetch за месяц против 47 вызовов context7 в 8 сессиях. Для документации библиотек '
        'context7 точнее и короче веб-страницы: пропиши в CLAUDE.md, что доки библиотек берутся через него, '
        'а веб — для остального.')},
    {'title': 'Отладка и коммиты прижились', 'tone': 'rise', 'text': (
        'commit — в 25 сессиях, systematic-debugging — в 20, writing-plans — в 13: эти приёмы стали привычкой, '
        'их стоит оставить. На этой неделе появились subagent-driven-development и mcp-builder — через пару '
        'недель проверь, прижились ли они.')},
    {'title': 'Заброшенное занимает место', 'tone': 'note', 'text': (
        'feature-dev молчит с 01.09, update-config — с 11.09, а календарь и диск Google Workspace за месяц '
        'вызывались 6 и 4 раза против 21 у почты. Описания скилов грузятся в каждую сессию: убери те, что '
        'заменили другие приёмы, и проверь, нужен ли весь Google Workspace ради почты.')},
)

FINDINGS_EN = (
    {'title': 'Five long sessions take 39% of the gold', 'tone': 'fall', 'text': (
        'The five dearest sessions, 8–10 hours and 66–78 turns each in shop-api and web-app, ate 210 of 536M gold, '
        'while a typical session costs 0.5M. 99% of the input is re-reading the context, so a long session gets '
        'dearer with every turn. Split a big task into sessions by subtask, keep the plan in a file, run /compact '
        'earlier.')},
    {'title': 'Long sessions go without helpers', 'tone': 'fall', 'text': (
        'Subagents ran in only 31 of 193 sessions, and in just one of the five dearest. Hand code exploration and '
        'project searches to the Explore agent: it reads files in its own context and returns a summary, so the '
        'main session does not swell.')},
    {'title': 'Friction in every third session', 'tone': 'fall', 'text': (
        '79 denials and 21 interrupts over 1,212 turns, friction in 62 of 193 sessions; 74 sessions ran in the '
        'default mode, where edits and commands wait for approval. Move frequent safe commands (tests, git status, '
        'git diff) to allow in the settings and dangerous ones to deny; guard-bash.sh stays as a safety net.')},
    {'title': 'Edits without checks', 'tone': 'fall', 'text': (
        'In 56 of 125 sessions with edits neither tests nor a linter ran. The format.sh hook already fires after '
        'every edit (2,481 times): add the project linter to it or hang the tests on a Stop hook, and checking '
        'stops depending on the agent remembering it.')},
    {'title': 'Docs come from the web, not from context7', 'tone': 'note', 'text': (
        '202 WebSearch and 188 WebFetch calls in a month against 47 context7 calls in 8 sessions. For library docs '
        'context7 is more precise and shorter than a web page: say in CLAUDE.md that library docs come through it '
        'and the web is for the rest.')},
    {'title': 'Debugging and commits took root', 'tone': 'rise', 'text': (
        'commit ran in 25 sessions, systematic-debugging in 20, writing-plans in 13: these habits stuck and are '
        'worth keeping. subagent-driven-development and mcp-builder showed up this week: check in a couple of '
        'weeks whether they took root.')},
    {'title': 'Abandoned tools take up room', 'tone': 'note', 'text': (
        'feature-dev has been silent since Sep 1, update-config since Sep 11, and the Google Workspace calendar and '
        'drive were called 6 and 4 times in a month against 21 for mail. Skill descriptions load into every '
        'session: drop the ones other tools replaced, and check whether all of Google Workspace is needed for mail.')},
)
FINDINGS = {'ru': FINDINGS_RU, 'en': FINDINGS_EN}

INSTRUCTIONS_RU = {
    'CLAUDE.md': (
        '# Общие правила', '- Отвечай по-русски, код и комментарии — по-английски.', '- Перед правками читай файл целиком.',
        '- Не коммить без просьбы.', '- После правок запускай тесты и линтер проекта.', '- Не трогай секреты и .env.',
        '- Новые зависимости — только с фиксированной версией.', '- Сначала план, потом код для задач больше часа.',
        '- Пиши маленькие функции и понятные имена.', '- Объясняй, что сделал, коротко и по делу.',
    ),
    'rules/testing.md': (
        '# Тесты', '- Новый код — с тестом.', '- Фикстуры вместо ручных моков.', '- Падающий тест — сначала причина.',
        '- Не отключай тесты, чтобы пройти CI.', '- Медленные тесты помечай отдельно.',
    ),
    'rules/git.md': (
        '# Git', '- Ветка на задачу.', '- Сообщение коммита — одна строка.', '- Никаких force push в main.',
        '- Перед PR — rebase на свежий main.',
    ),
    'projects/-Users-alex-Projects-shop-api/memory/MEMORY.md': (
        '- Тесты идут в Docker: docker compose run --rm api pytest.', '- Миграции генерирует команда, руками не пишем.',
        '- Платежи — через stripe_client, напрямую API не звать.',
    ),
}

# The same rules in English, line for line: the law side of the alignment counts non-empty lines only.
INSTRUCTIONS_EN = {
    'CLAUDE.md': (
        '# General rules', '- Answer in English, code and comments too.', '- Read the whole file before editing it.',
        '- Do not commit unless asked.', '- Run the project tests and linter after edits.', '- Do not touch secrets and .env.',
        '- New dependencies only with a pinned version.', '- A plan first, then code, for tasks longer than an hour.',
        '- Write small functions with clear names.', '- Explain what you did, briefly and to the point.',
    ),
    'rules/testing.md': (
        '# Tests', '- New code comes with a test.', '- Fixtures instead of hand-made mocks.',
        '- A failing test: find the cause first.', '- Do not disable tests to pass CI.', '- Mark slow tests separately.',
    ),
    'rules/git.md': (
        '# Git', '- A branch per task.', '- A commit message is one line.', '- No force push to main.',
        '- Rebase on a fresh main before a PR.',
    ),
    'projects/-Users-alex-Projects-shop-api/memory/MEMORY.md': (
        '- Tests run in Docker: docker compose run --rm api pytest.', '- Migrations are generated by a command, never by hand.',
        '- Payments go through stripe_client, never call the API directly.',
    ),
}
INSTRUCTIONS = {'ru': INSTRUCTIONS_RU, 'en': INSTRUCTIONS_EN}


def weighted(rng, weights):
    """One key of a {key: weight} mapping, picked by weight."""
    keys = list(weights)
    return rng.choices(keys, weights=[weights[key] for key in keys])[0]


def new_id(rng):
    """Deterministic uuid4-shaped id."""
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def clamp(value, low, high):
    """Value limited to [low, high]."""
    return max(low, min(high, value))


def active(since, until, day):
    """True when a day falls into an optional [since, until] window."""
    return (since is None or day >= since) and (until is None or day <= until)


def place_weights(day):
    """How likely each place is on a day: the mobile project ends in August, hobbies take the weekends."""
    weekend = day.weekday() >= 5
    return {
        'shop-api': 30, 'web-app': 22, 'infra': 8, 'docs-site': 5, 'data-notebooks': 7, 'dotfiles': 3,
        'mobile-app': 10 if day <= date(2026, 8, 24) else 0,
        'recipe-bot': 30 if weekend else 1.5,
        'notes': 20 if weekend else 2.5,
    }


def load_factor(day):
    """Busier as the month goes on, nothing on vacation."""
    if VACATION[0] <= day <= VACATION[1]:
        return 0.0
    if day >= date(2026, 9, 21):
        return 1.35
    if day >= date(2026, 9, 1):
        return 1.0
    return 0.75


class Session:

    """One fake session: the main transcript, subagent transcripts and its time span."""

    def __init__(self, rng, place, start, entrypoint, mode, lang):
        self.rng = rng
        self.lang = lang
        self.sid = new_id(rng)
        self.place = place
        self.project = PROJECTS[place]
        self.cwd = os.path.join(USER_HOME, self.project['path'])
        self.start = start
        self.clock = start
        self.day = start.astimezone().date()
        self.entrypoint = entrypoint
        self.mode = mode
        self.context = BASE_CONTEXT
        self.records = []
        self.subagents = {}

    @property
    def end(self):
        return self.clock

    def stamp(self, moment=None):
        moment = (moment or self.clock).astimezone(timezone.utc)
        return moment.strftime('%Y-%m-%dT%H:%M:%S.') + f'{moment.microsecond // 1000:03d}Z'

    def wait(self, low, high):
        self.clock += timedelta(seconds=self.rng.uniform(low, high))

    def record(self, kind, **fields):
        entry = {
            'type': kind, 'timestamp': self.stamp(), 'sessionId': self.sid, 'cwd': self.cwd,
            'entrypoint': self.entrypoint, 'uuid': new_id(self.rng), 'isSidechain': False, 'version': '2.1.0',
        }
        entry.update(fields)
        self.records.append(entry)
        return entry

    def hook(self, event):
        command, since = HOOKS[event]
        if self.day >= since:
            self.record('attachment', attachment={
                'type': 'hook_success', 'hookEvent': event, 'hookName': event, 'command': command,
            })

    def usage(self, output, fresh=None):
        grow = fresh if fresh is not None else self.rng.randint(900, 3400)
        self.context += grow
        return {
            'input_tokens': self.rng.randint(2, 12), 'cache_creation_input_tokens': grow,
            'cache_read_input_tokens': self.context - grow, 'output_tokens': output,
        }

    def human(self, text):
        self.record('user', permissionMode=self.mode, origin={'kind': 'human'},
                    message={'role': 'user', 'content': text})

    def compact_if_full(self):
        if self.context < COMPACT_AT:
            return
        self.record('system', subtype='compact_boundary', content='Conversation compacted', level='info')
        self.record('user', isCompactSummary=True, isMeta=True,
                    message={'role': 'user', 'content': 'This session is being continued from a previous conversation.'})
        self.context = self.rng.randint(30000, 45000)

    def assistant(self, content, output):
        self.record('assistant', message={
            'id': 'msg_' + uuid.UUID(int=self.rng.getrandbits(128)).hex[:24], 'type': 'message', 'role': 'assistant',
            'model': MODEL, 'content': content, 'usage': self.usage(output),
        })

    def tool(self, name, tool_input, error=False, denial=None, result='ok'):
        self.wait(3, 22)
        if name == 'Bash':
            self.hook('PreToolUse')
        tool_id = 'toolu_' + uuid.UUID(int=self.rng.getrandbits(128)).hex[:24]
        self.assistant([{'type': 'tool_use', 'id': tool_id, 'name': name, 'input': tool_input}],
                       self.rng.randint(60, 450))
        self.wait(1, 35 if name == 'Bash' else 4)
        block = {'type': 'tool_result', 'tool_use_id': tool_id, 'content': result}
        fields = {}
        if denial:
            block.update(is_error=True, content="The user doesn't want to proceed with this tool use.")
            fields['toolDenialKind'] = denial
        elif error:
            block.update(is_error=True, content='Error: command failed')
        self.record('user', message={'role': 'user', 'content': [block]}, **fields)
        if name in EDIT_TOOLS and not denial:
            self.hook('PostToolUse')

    def say(self):
        self.wait(4, 30)
        self.assistant([{'type': 'text', 'text': DONE[self.lang]}], self.rng.randint(150, 1400))

    def agent(self):
        kind = self.rng.choice(SUBAGENT_TYPES)
        self.wait(3, 15)
        tool_id = 'toolu_' + uuid.UUID(int=self.rng.getrandbits(128)).hex[:24]
        self.assistant([{'type': 'tool_use', 'id': tool_id, 'name': 'Agent', 'input': {
            'description': 'Explore the code', 'subagent_type': kind, 'prompt': 'Find where it happens.'}}],
            self.rng.randint(150, 600))
        sub_clock = self.clock
        context = self.rng.randint(12000, 18000)
        records = []
        for _ in range(self.rng.randint(4, 18)):
            sub_clock += timedelta(seconds=self.rng.uniform(2, 12))
            grow = self.rng.randint(800, 3000)
            context += grow
            name = self.rng.choice(('Read', 'Read', 'Grep', 'Glob', 'Bash'))
            sub_id = 'toolu_' + uuid.UUID(int=self.rng.getrandbits(128)).hex[:24]
            base = {'sessionId': self.sid, 'cwd': self.cwd, 'isSidechain': True, 'agentId': tool_id[-8:]}
            records.append({**base, 'type': 'assistant', 'timestamp': self.stamp(sub_clock), 'message': {
                'id': 'msg_' + uuid.UUID(int=self.rng.getrandbits(128)).hex[:24], 'role': 'assistant', 'model': MODEL,
                'content': [{'type': 'tool_use', 'id': sub_id, 'name': name, 'input': {}}],
                'usage': {'input_tokens': 4, 'cache_creation_input_tokens': grow,
                          'cache_read_input_tokens': context - grow, 'output_tokens': self.rng.randint(50, 300)}}})
            records.append({**base, 'type': 'user', 'timestamp': self.stamp(sub_clock), 'message': {
                'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': sub_id, 'content': 'ok'}]}})
        self.subagents[f'agent-{tool_id[-12:]}'] = records
        self.clock = sub_clock + timedelta(seconds=self.rng.uniform(5, 20))
        self.record('user', message={'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': tool_id, 'content': 'Agent finished.'}]})


def pick_tool(rng, session, edits, research):
    """One everyday tool call of the agent: reads, searches, shell and edits."""
    weights = {'Read': 24, 'Grep': 10, 'Glob': 5, 'Bash': 28, 'TodoWrite': 4, 'WebSearch': 1, 'WebFetch': 1}
    if edits and not research:
        weights.update(Edit=13, Write=3)
    name = weighted(rng, weights)
    files = session.project['files']
    if name in ('Edit', 'Write'):
        path = os.path.join(session.cwd, rng.choice(files))
        if path.endswith('.ipynb'):
            return 'NotebookEdit', {'notebook_path': path, 'new_source': '...'}
        return name, {'file_path': path, 'old_string': 'a', 'new_string': 'b'}
    if name == 'Read':
        return name, {'file_path': os.path.join(session.cwd, rng.choice(files))}
    if name == 'Bash':
        return name, {'command': rng.choice(session.project['run'] + ('git status', 'ls', 'git diff'))}
    if name in ('WebSearch', 'WebFetch'):
        return name, {'query': 'library changelog'}
    return name, {}


def build_session(rng, place, start, entrypoint, lang):
    """One human session of everyday work in a place, with the skills, MCP and helpers it happened to use."""
    day = start.astimezone().date()
    plan = place not in ('notes', 'dotfiles') and rng.random() < 0.3
    mode = 'plan' if plan else weighted(rng, MODES)
    session = Session(rng, place, start, entrypoint, mode, lang)
    turns = clamp(int(rng.lognormvariate(math.log(3), 0.95)), 1, 70)
    # Now and then a long haul: a big task carried through dozens of turns, sometimes over several days.
    if place in CODE + ('infra',) and rng.random() < 0.035:
        turns = rng.randint(25, 80)
    edits = rng.random() < (0.8 if place in CODE + ('infra', 'docs-site', 'dotfiles') else 0.35)
    verify = edits and bool(session.project['checks']) and rng.random() < 0.62
    commit = edits and place != 'notes' and rng.random() < 0.5
    extras = [[] for _ in range(turns)]
    commands = {}
    for name, how, chance, places, since, until in SKILLS:
        if place in places and active(since, until, day) and rng.random() < chance:
            index = rng.randrange(turns)
            if how == 'command':
                commands[index] = name
            else:
                extras[index].insert(0, ('Skill', {'skill': name}))
    for server, tools, chances, since in MCP:
        if rng.random() < chances.get(place, 0) and active(since, None, day):
            for _ in range(clamp(1 + int(rng.expovariate(1 / 4)), 1, 30)):
                extras[rng.randrange(turns)].append((f'mcp__{server}__{weighted(rng, tools)}', {}))
    helpers = rng.choice((1, 1, 1, 2, 2, 3, 4)) if rng.random() < 0.22 else 0
    if rng.random() < 0.015:
        helpers = rng.randint(8, 14)
    for _ in range(helpers):
        extras[rng.randrange(turns)].append(('Agent', None))
    for _ in range(rng.randint(1, 2) if plan and rng.random() < 0.6 else 1 if rng.random() < 0.08 else 0):
        extras[0 if plan else rng.randrange(turns)].append(('AskUserQuestion', {}))
    denials = rng.randint(1, 3) if rng.random() < DENIAL_CHANCE[mode] else 0
    interrupt = rng.randrange(turns) if rng.random() < 0.07 else None
    destructive = rng.random() < 0.012

    session.hook('SessionStart')
    for index in range(turns):
        session.compact_if_full()
        if index:
            pause = rng.random()
            if pause < 0.8:
                session.wait(20, 300)
            elif pause < 0.9:
                session.wait(480, 1500)
            elif pause < 0.98 or turns < 6:
                session.wait(1500, 7200)
            else:
                session.wait(86400, 3 * 86400)
        if index in commands:
            command = commands[index]
            session.human(f'<command-name>/{command}</command-name>\n<command-message>{command}</command-message>\n'
                          '<command-args></command-args>')
        else:
            session.human(rng.choice(PROMPTS[lang]))
        research = plan and index == 0
        calls = [pick_tool(rng, session, edits, research)
                 for _ in range(clamp(int(rng.lognormvariate(math.log(10), 0.85)), 0, 90))]
        for position, extra in enumerate(extras[index]):
            calls.insert(rng.randint(0, len(calls)) if position else 0, extra)
        edited = False
        for name, tool_input in calls:
            if name == 'Agent':
                session.agent()
                continue
            denial = None
            if denials and name in ('Bash', 'Edit', 'Write') and rng.random() < 0.3:
                denial = rng.choice(('user-rejected', 'user-rejected', 'permission-rule'))
                denials -= 1
            error = not denial and rng.random() < (0.04 if name == 'Bash' else 0.015)
            session.tool(name, tool_input, error=error, denial=denial)
            edited = edited or (name in EDIT_TOOLS and not denial)
            if interrupt == index and rng.random() < 0.2:
                session.wait(2, 10)
                session.record('user', message={'role': 'user', 'content': [
                    {'type': 'text', 'text': '[Request interrupted by user]'}]})
                interrupt = None
                break
        if research:
            session.tool('ExitPlanMode', {'plan': '...'})
            session.mode = rng.choice(('acceptEdits', 'default', 'auto'))
        if edited and verify:
            for check in rng.sample(session.project['checks'], k=min(2, len(session.project['checks']))):
                session.tool('Bash', {'command': check}, error=rng.random() < 0.15)
        if index == turns - 1 and commit:
            session.tool('Bash', {'command': 'git add -A && git commit -m "update"'})
            if place in CODE and rng.random() < 0.3:
                session.tool('Bash', {'command': 'gh pr create --fill'})
        if destructive and index == turns - 1:
            session.tool('Bash', {'command': rng.choice(('git reset --hard HEAD~1', 'git push --force-with-lease'))})
        session.say()
        session.hook('Stop')
    return session


def build_background(rng, start, lang):
    """A scheduled night run without a person: a dependency audit of the main project."""
    session = Session(rng, 'shop-api', start, 'sdk-cli', 'bypassPermissions', lang)
    session.record('user', scheduledTaskId='nightly-deps-audit', message={'role': 'user', 'content': AUDIT[lang]})
    for _ in range(rng.randint(5, 12)):
        session.tool('Bash', {'command': rng.choice(('pip-audit', 'git status', 'cat pyproject.toml'))})
    session.say()
    return session


def plan_sessions(rng, until, lang):
    """All sessions of the example, day by day, up to the last run."""
    sessions = []
    day = FIRST_DAY
    while day <= until.date():
        for _ in range(max(0, round(rng.gauss(WEEKDAY_SESSIONS[day.weekday()] * load_factor(day), 1.4)))):
            start = datetime(day.year, day.month, day.day, weighted(rng, START_HOURS), rng.randrange(60),
                             rng.randrange(60)).astimezone()
            place = weighted(rng, place_weights(day))
            sessions.append(build_session(rng, place, start, weighted(rng, ENTRYPOINTS), lang))
        if day >= date(2026, 9, 8) and rng.random() < 0.45:
            sessions.append(build_background(rng, datetime(day.year, day.month, day.day, 3, 0).astimezone(), lang))
        day += timedelta(days=1)
    return sorted(sessions, key=lambda session: session.start)


def write_session(projects_dir, session):
    """Write a session's transcripts the way Claude Code lays them out; their mtime is the session's end."""
    folder = os.path.join(projects_dir, session.cwd.replace('/', '-'))
    paths = [os.path.join(folder, f'{session.sid}.jsonl')]
    os.makedirs(folder, exist_ok=True)
    with open(paths[0], 'w', encoding='utf-8') as handle:
        handle.writelines(json.dumps(record, ensure_ascii=False) + '\n' for record in session.records)
    for name, records in session.subagents.items():
        path = os.path.join(folder, session.sid, 'subagents', f'{name}.jsonl')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.writelines(json.dumps(record, ensure_ascii=False) + '\n' for record in records)
        paths.append(path)
    stamp = int(session.end.timestamp() * 1e9)
    for path in paths:
        os.utime(path, ns=(stamp, stamp))


def remove_session(projects_dir, session):
    """Delete a session's transcripts like the cleanup of Claude Code does."""
    folder = os.path.join(projects_dir, session.cwd.replace('/', '-'))
    os.remove(os.path.join(folder, f'{session.sid}.jsonl'))
    shutil.rmtree(os.path.join(folder, session.sid), ignore_errors=True)


def write_instructions(config_dir, lang):
    """Global CLAUDE.md, rules and memory of the imagined user: the law side of the alignment counts them."""
    for name, lines in INSTRUCTIONS[lang].items():
        path = os.path.join(config_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')


def build(home, lang):
    """Run the example through the pipeline into one data folder, in the language the person writes in."""
    rng = random.Random(SEED)
    runs = [run.astimezone() for run in RUNS]
    sessions = plan_sessions(rng, runs[-1], lang)
    for name in OUTPUTS:
        if os.path.exists(os.path.join(home, name)):
            os.remove(os.path.join(home, name))
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = os.path.join(tmp, 'claude')
        projects_dir = os.path.join(config_dir, 'projects')
        write_instructions(config_dir, lang)
        os.environ['CLAUDE_CONFIG_DIR'] = config_dir
        on_disk = []
        for run in runs:
            for session in sessions:
                if session not in on_disk and session.end <= run and session.start >= run - timedelta(days=CLEANUP_DAYS):
                    write_session(projects_dir, session)
                    on_disk.append(session)
            for session in [session for session in on_disk if session.end < run - timedelta(days=CLEANUP_DAYS)]:
                remove_session(projects_dir, session)
                on_disk.remove(session)
            ledger, parsed = update(projects_dir, home)
            errors = classify(home, CATALOG[lang])
            pending = pending_items(ledger, load_catalog(home))
            if errors or pending['skills'] or pending['mcp']:
                raise SystemExit(f'classification is incomplete: {errors} {pending}')
            character, _, history = render(home, now=run)
            if character['lang'] != lang:
                raise SystemExit(f'the page came out in {character["lang"]!r}, not in {lang!r}')
            print(f'{lang} {run:%Y-%m-%d %H:%M}: +{parsed} sessions, level {character["level"]["level"]}, '
                  f'{character["class"]["name"]}, {len(history)} snapshots')
        if FINDINGS[lang]:
            errors, _ = attach_findings(home, {'findings': list(FINDINGS[lang])})
            if errors:
                raise SystemExit(f'findings rejected: {errors}')
        # The transcripts lived in a temporary folder: the ledger shows them where Claude Code keeps them.
        ledger_file = ledger_path(home)
        ledger = load_json(ledger_file, None)
        ledger['files'] = {
            path.replace(projects_dir, os.path.join(USER_HOME, '.claude', 'projects'), 1): value
            for path, value in ledger['files'].items()
        }
        save_json(ledger_file, ledger)
    print(f'html: {os.path.join(home, "character.html")}')


def main():
    build(HERE, 'ru')
    build(os.path.join(HERE, 'en'), 'en')


if __name__ == '__main__':
    main()
