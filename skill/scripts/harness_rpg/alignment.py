"""Alignment: order against chaos and care against harm over the recent window."""

import glob
import os
import statistics
from collections import Counter

from .constants import (
    LAW_CHAOTIC_UPTO, LAW_LAWFUL_FROM, LAW_PLAN_SHARE_FULL, LAW_RULES_MID, MORAL_EVIL_BELOW, MORAL_EVIL_WEIGHT,
    MORAL_GOOD_FROM, PERMISSION_STRICTNESS, PERMISSION_STRICTNESS_UNKNOWN,
)
from .scoring import recent_sessions
from .storage import claude_dir
from .texts import TEXTS


def instruction_lines(project_dirs):
    """Non-empty lines of instructions the harness follows: CLAUDE.md files, rules, memory."""
    base = claude_dir()
    patterns = [
        os.path.join(base, 'CLAUDE.md'),
        os.path.join(base, 'rules', '**', '*.md'),
        os.path.join(base, 'projects', '*', 'memory', '*.md'),
    ]
    for project in project_dirs:
        root = glob.escape(project)
        patterns += [
            os.path.join(root, 'CLAUDE.md'),
            os.path.join(root, 'CLAUDE.local.md'),
            os.path.join(root, 'AGENTS.md'),
            os.path.join(root, '.claude', 'CLAUDE.md'),
            os.path.join(root, '.claude', 'rules', '**', '*.md'),
        ]
    files = {
        os.path.realpath(path)
        for pattern in patterns for path in glob.glob(pattern, recursive=True) if os.path.isfile(path)
    }
    total = 0
    for path in files:
        try:
            with open(path, encoding='utf-8', errors='replace') as handle:
                total += sum(1 for line in handle if line.strip())
        except OSError:
            continue
    return total


def loosest_mode(session):
    """The most permissive permission mode a session ran in; a session without a mode counts as default."""
    return min(session.get('modes') or ['default'],
               key=lambda mode: PERMISSION_STRICTNESS.get(mode, PERMISSION_STRICTNESS_UNKNOWN))


def build_alignment(sessions, now, lang='ru'):
    """D&D alignment: order against chaos and care against harm over the recent window."""
    window = recent_sessions(sessions, now)
    projects = sorted({session['project'] for session in window if session.get('project')})
    rules = instruction_lines([project for project in projects if os.path.isdir(project)])
    if not window:
        name, desc = TEXTS[lang]['alignments'][('neutral', 'neutral')]
        return {'law': 'neutral', 'moral': 'neutral', 'name': name, 'desc': desc, 'details': {'rules_lines': rules}}

    def share(predicate):
        return sum(1 for session in window if predicate(session)) / len(window)

    plan_share = share(lambda session: session['plan_mode'])
    strictness = statistics.mean(
        min((PERMISSION_STRICTNESS.get(mode, PERMISSION_STRICTNESS_UNKNOWN) for mode in session.get('modes', [])),
            default=1.0)
        for session in window
    )
    law = statistics.mean((rules / (rules + LAW_RULES_MID), min(1.0, plan_share / LAW_PLAN_SHARE_FULL), strictness))
    law_key = 'lawful' if law >= LAW_LAWFUL_FROM else 'chaotic' if law <= LAW_CHAOTIC_UPTO else 'neutral'
    good_share = share(lambda session: session['counts'].get('verifications', 0) > 0
                       or session['tools'].get('AskUserQuestion', 0) > 0)
    evil_share = share(lambda session: session['counts'].get('destructive', 0) > 0)
    moral = good_share - MORAL_EVIL_WEIGHT * evil_share
    moral_key = 'good' if moral >= MORAL_GOOD_FROM else 'evil' if moral < MORAL_EVIL_BELOW else 'neutral'
    name, desc = TEXTS[lang]['alignments'][(law_key, moral_key)]
    # Each session is judged by its loosest permission mode.
    loosest = Counter(loosest_mode(session) for session in window)
    return {
        'law': law_key,
        'moral': moral_key,
        'name': name,
        'desc': desc,
        'details': {
            'rules_lines': rules, 'plan_share': round(plan_share, 3), 'strictness': round(strictness, 3),
            'law_score': round(law, 3), 'good_share': round(good_share, 3), 'evil_share': round(evil_share, 3),
            'moral_score': round(moral, 3), 'sessions': len(window), 'modes': dict(loosest.most_common()),
            'verifications': sum(session['counts'].get('verifications', 0) for session in window),
            'questions': sum(session['tools'].get('AskUserQuestion', 0) for session in window),
            'destructive': sum(session['counts'].get('destructive', 0) for session in window),
        },
    }
