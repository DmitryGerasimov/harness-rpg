"""Where the data lives: the Claude Code config directory, the hero's home and its JSON files."""

import json
import os


def claude_dir():
    """Claude Code config directory."""
    return os.path.expanduser(os.environ.get('CLAUDE_CONFIG_DIR') or '~/.claude')


def rpg_home():
    """Directory with the ledger, catalog and rendered pages."""
    return os.path.expanduser(os.environ.get('HARNESS_RPG_HOME') or '~/.harness-rpg')


def load_json(path, default):
    """Read JSON from path; a missing file yields default, a corrupt one raises."""
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default


def save_json(path, data):
    """Write JSON atomically."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    temporary = path + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write('\n')
    os.replace(temporary, path)


def ledger_path(home):
    """Path of the accumulating ledger."""
    return os.path.join(home, 'ledger.json')


def history_path(home):
    """Path of the archive of public snapshots shown on the page."""
    return os.path.join(home, 'history.json')


def catalog_path(home):
    """Path of the agent-made classification cache."""
    return os.path.join(home, 'catalog.json')


def load_catalog(home):
    """Catalog with 'skills' (key -> school) and 'mcp' (server -> name or ignore)."""
    catalog = load_json(catalog_path(home), {})
    catalog.setdefault('skills', {})
    catalog.setdefault('mcp', {})
    return catalog
