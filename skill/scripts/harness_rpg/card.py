"""Chat card: a compact fragment of the latest hero for an inline widget, the game view only."""

import html
import json

from .constants import AVATAR_BEGIN, AVATAR_END, CARD_GEAR, CARD_SKILLS, RARITIES
from .texts import TEXTS
from .views import game_view


def avatar_script(template):
    """The template's portrait code, compacted for the chat card: no comment lines, no indentation."""
    block = template[template.index(AVATAR_BEGIN):template.index(AVATAR_END)]
    lines = (line.strip() for line in block.splitlines())
    return '\n'.join(line for line in lines if line and not line.startswith('//'))


def chat_card(snapshot, avatar_js):
    """A compact card of the hero for an inline chat widget: the game view only, never names or numbers of work.

    The host draws it in its own light or dark theme, so text takes the host's colors; only the pixel art and the
    rarity marks keep their own. The button asks Claude to open the full page.
    """
    game = game_view(snapshot)
    words = TEXTS[game.get('lang', 'ru')]['card']
    esc = html.escape
    level = game['level']
    hero_class = game['class']
    rarity_order = [key for _, key in RARITIES]
    rarity_hex = {'common': '#9d9d9d', 'uncommon': '#3ccf3c', 'rare': '#3a8fe8', 'epic': '#b35cf0',
                  'legendary': '#ff8c1a'}
    headline = words['headline'].format(level=level['level'], name=hero_class['name'])
    if game.get('title'):
        headline += ' · ' + words['title'].format(title=game['title'])
    xp_share = round(100 * level['into'] / level['need']) if level.get('need') else 0
    attributes = sorted(game.get('attributes') or [], key=lambda attr: -attr['value'])
    skills = sorted((skill for group in game.get('skill_groups') or [] for skill in group['skills']),
                    key=lambda skill: -skill['rank'])[:CARD_SKILLS]
    worn = sorted((item for item in game.get('gear') or [] if item.get('equipped')),
                  key=lambda item: -rarity_order.index(item['rarity']))[:CARD_GEAR]
    medals = [sum(1 for item in game.get('achievements') or [] if item.get('tier') == tier) for tier in (2, 1, 0)]
    aura = next((aura for aura in game.get('auras') or [] if aura['tier'] >= 0), None)
    muted = 'margin:0 0 6px;font-size:12px;color:var(--text-muted)'
    line = 'margin:0 0 4px;font-size:13px'
    chip = ('font-size:12px;padding:2px 8px;border-radius:var(--radius);background:var(--surface-2);'
            'border:0.5px solid var(--border)')

    def rows(items):
        return ''.join(items) or f'<p style="{line};color:var(--text-muted)">—</p>'

    skill_rows = rows(
        f'<p style="{line}">{esc(skill["alias"])} <span style="color:var(--text-secondary)">— '
        f'{esc(skill["rank_name"])}</span></p>'
        for skill in skills
    )
    gear_rows = rows(
        f'<p style="{line};display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;'
        f'border-radius:2px;flex:none;background:{rarity_hex[item["rarity"]]}"></span><span>{esc(item["alias"])} '
        f'<span style="color:var(--text-secondary)">— {esc(item["rarity_name"])}</span></span></p>'
        for item in worn
    )
    # The portrait wears everything worn, not only the items listed on the card.
    gear_for_avatar = [{'slot': item['slot'], 'rarity': item['rarity'], 'equipped': True}
                       for item in game.get('gear') or [] if item.get('equipped') and item.get('slot')]
    aura_line = (f'<p style="{line};color:var(--text-secondary)">{esc(aura["name"])} — {esc(aura["tier_name"])}</p>'
                 if aura else '')
    # A JS string literal, so a quote in the text can't break the call; the attribute escaping undoes itself.
    prompt = esc(json.dumps(words['prompt'], ensure_ascii=False))
    return (
        f'<h2 class="sr-only">{esc(words["heading"].format(headline=headline))}</h2>'
        '<div style="background:var(--surface-1);border-radius:12px;padding:1rem 1.25rem">'
        '<div style="display:grid;grid-template-columns:128px minmax(0,1fr);gap:20px;align-items:center">'
        f'<canvas id="hero" width="40" height="40" aria-label="{esc(words["avatar"])}" style="width:128px;'
        'height:128px;image-rendering:pixelated;background:var(--surface-2);border-radius:var(--radius)"></canvas><div>'
        '<p style="margin:0;font-size:18px;font-weight:500">Claude Code</p>'
        f'<p style="margin:2px 0 10px;font-size:14px;color:var(--text-secondary)">{esc(headline)}</p>'
        '<div style="height:6px;border-radius:3px;background:var(--border)">'
        f'<div style="width:{xp_share}%;height:6px;border-radius:3px;background:var(--fill-success)"></div></div>'
        f'<p style="margin:4px 0 12px;font-size:12px;color:var(--text-muted)">'
        f'{esc(words["xp"].format(into=level["into"], need=level["need"], next=level["level"] + 1))}</p>'
        '<div style="display:flex;flex-wrap:wrap;gap:6px">'
        + ''.join(f'<span style="{chip}">{esc(attr["abbr"])} {attr["value"]}</span>' for attr in attributes)
        + '</div></div></div>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-top:16px;'
        'padding-top:12px;border-top:0.5px solid var(--border)">'
        f'<div><p style="{muted}">{esc(words["skills"])}</p>{skill_rows}</div>'
        f'<div><p style="{muted}">{esc(words["gear"])}</p>{gear_rows}</div>'
        f'<div><p style="{muted}">{esc(words["alignment"])}</p><p style="{line}">{esc(game["alignment"]["name"])}</p>'
        f'{aura_line}<p style="{line};color:var(--text-secondary)">'
        f'{esc(words["medals"].format(gold=medals[0], silver=medals[1], bronze=medals[2]))}</p></div></div></div>'
        f'<div style="margin-top:12px"><button onclick="sendPrompt({prompt})">'
        f'{esc(words["button"])}</button></div>'
        f'<script>{avatar_js}\ndrawAvatar(document.getElementById(\'hero\'), {json.dumps(hero_class.get("primary"))}, '
        f'{json.dumps(hero_class.get("secondary"))}, {json.dumps(gear_for_avatar)});</script>'
    )
