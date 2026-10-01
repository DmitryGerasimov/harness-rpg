"""Names of skills and MCP servers as transcripts write them, resolved through the catalog; alias rules."""

from .constants import (
    ALIAS_MAX_LENGTH, ALIAS_NAME_TOKEN_MIN, CYRILLIC_RE, EXCLUDED_MCP_PREFIXES, EXCLUDED_MCP_SERVERS, LATIN_RE,
    NAME_SPLIT_RE, PLUGIN_SERVER_RE, UUID_RE,
)
from .texts import TEXTS


def normalize_skill(name):
    """Return (canonical key, display name): no slash, no plugin prefix, lowercase, dashes."""
    if not isinstance(name, str):
        return '', ''
    display = name.strip().lstrip('/').split(':')[-1].strip()
    return display.lower().replace('_', '-'), display


def split_mcp(tool_name):
    """Split 'mcp__server__tool' into (server, tool), or None for non-MCP tools."""
    parts = tool_name.split('__')
    if len(parts) < 3 or parts[0] != 'mcp' or not parts[1]:
        return None
    return parts[1], '__'.join(parts[2:])


def is_plumbing(server):
    """True for MCP servers of the host itself: they are neither gear nor something to classify."""
    return server.startswith(EXCLUDED_MCP_PREFIXES) or server in EXCLUDED_MCP_SERVERS


def auto_mcp_name(server):
    """Readable MCP name derived from the server id, or None when the agent has to name it."""
    if is_plumbing(server) or UUID_RE.match(server):
        return None
    if server.startswith('claude_ai_'):
        return server[len('claude_ai_'):].replace('_', ' ')
    plugin_match = PLUGIN_SERVER_RE.match(server)
    if plugin_match:
        return plugin_match.group(1).replace('_', ' ')
    return server.replace('_', ' ')


def alias_field(lang):
    """Catalog field of the alias in a page language: 'alias' is the Russian one, 'alias_en' the English."""
    return 'alias' if lang == 'ru' else f'alias_{lang}'


def alias_problem(alias, real_names, lang='ru'):
    """Why an alias would reveal the real tool or break the page language, or None when it is safe to share."""
    alias = (alias or '').strip()
    if not alias:
        return 'empty'
    if len(alias) > ALIAS_MAX_LENGTH:
        return f'longer than {ALIAS_MAX_LENGTH} characters'
    if lang == 'ru' and LATIN_RE.search(alias):
        return 'contains Latin letters'
    if lang != 'ru' and CYRILLIC_RE.search(alias):
        return 'contains Cyrillic letters: write it in English (the page language)'
    lowered = alias.lower()
    for word in TEXTS[lang]['tooling']:
        if word in lowered:
            return f'contains the tooling word {word!r}: the page speaks about the hero'
    # Without spaces and dashes too: "Lin Ear Ring" spells the real name all the same.
    squashed = NAME_SPLIT_RE.sub('', lowered)
    for name in real_names:
        if not name:
            continue
        name = name.lower()
        parts = {name} | set(NAME_SPLIT_RE.split(name))
        for part in sorted(part for part in parts if len(part) >= ALIAS_NAME_TOKEN_MIN):
            if part in lowered or part in squashed:
                return f'contains part of the real name {part!r}'
    return None


def mcp_field(servers, catalog, field):
    """First value of a catalog field for any server of one MCP item."""
    for server in sorted(servers):
        value = (catalog['mcp'].get(server) or {}).get(field)
        if value:
            return value
    return None


def mcp_alias(servers, catalog, lang='ru'):
    """First alias in the page language the catalog has for any server of one MCP item."""
    return mcp_field(servers, catalog, alias_field(lang))


def resolve_mcp(server, catalog):
    """Return (display name, known) for a server, or (None, True) when it is not gear."""
    entry = catalog['mcp'].get(server) or {}
    if entry.get('ignore') or is_plumbing(server):
        return None, True
    name = entry.get('name') or auto_mcp_name(server)
    return (name, True) if name else (server, False)


def tool_family(tool):
    """Family of an MCP tool: its name up to the first underscore (mail_send -> mail)."""
    return tool.split('_', 1)[0]


def mcp_families(name, catalog):
    """Categories a server is split into, shared by every server id that goes by this name."""
    for server, entry in sorted(catalog['mcp'].items()):
        if entry.get('families') and (resolve_mcp(server, catalog)[0] or '').lower() == name.lower():
            return entry['families']
    return {}


def family_of(families, tool):
    """Category of a split server that owns this tool, or None when no category took its family yet."""
    prefix = tool_family(tool)
    for key, family in families.items():
        if prefix in (family.get('prefixes') or [key]):
            return family
    return None


def server_prefixes(ledger, name, catalog):
    """Tool families the ledger has seen for every server id that goes by this name."""
    prefixes = set()
    for session in (ledger.get('sessions') or {}).values():
        for server, entry in session['mcp'].items():
            if (resolve_mcp(server, catalog)[0] or '').lower() == name.lower():
                prefixes.update(tool_family(tool) for tool in entry['tools'])
    return prefixes


def gear_parts(server, entry, catalog):
    """One server's usage in a session, split into gear items by the categories the catalog carves out.

    A server can bundle tools of different purposes (notes and a database, code and logs). A split server
    is nothing but its categories, each an item with its own name, alias and slot: there is no catch-all
    item for the rest, and a tool of a family no category took yet waits for classification.
    Returns {group key: {'name', 'known', 'family' (dict or None), 'tools': {tool: calls}}}.
    """
    name, known = resolve_mcp(server, catalog)
    if name is None:
        return {}
    families = mcp_families(name, catalog)
    parts = {}
    for tool, calls in entry['tools'].items():
        family = family_of(families, tool) if families else None
        if families and family is None:
            continue
        part_name = family['name'] if family else name
        part = parts.setdefault(part_name.lower(), {
            'name': part_name, 'known': True if family else known, 'family': family, 'tools': {},
        })
        part['tools'][tool] = calls
    return parts
