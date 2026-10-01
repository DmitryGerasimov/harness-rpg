# harness-rpg

[![test](https://github.com/DmitryGerasimov/harness-rpg/actions/workflows/test.yml/badge.svg)](https://github.com/DmitryGerasimov/harness-rpg/actions/workflows/test.yml)
[![release](https://img.shields.io/github/v/release/DmitryGerasimov/harness-rpg)](https://github.com/DmitryGerasimov/harness-rpg/releases/latest)
[![python](https://img.shields.io/badge/python-3.9%2B-blue)](#install)
[![license](https://img.shields.io/github/license/DmitryGerasimov/harness-rpg)](LICENSE)

A [Claude Code](https://claude.com/claude-code) skill that turns your Claude Code history into an RPG hero.
It reads the transcripts on your machine and builds a character — level, class, attributes, talents (your
skills), gear (your MCP servers), auras (your hooks), achievements and a treasury (your tokens) — then draws
the hero's page in pixel art, with an archive of past snapshots and an insights mode about your real work.

**[See the live demo →](https://dmitrygerasimov.github.io/harness-rpg/)** It is the page of a made-up developer
after two months of work, [in insights mode](https://dmitrygerasimov.github.io/harness-rpg/#insights) too, and
[in Russian](https://dmitrygerasimov.github.io/harness-rpg/ru/).

**Don't skip your insights.** The hero is the fun part; the insights are the useful one — what your last
30 days of work actually look like, and what to change:

[![The findings of the demo hero in insights mode](https://dmitrygerasimov.github.io/harness-rpg/insights.png)](https://dmitrygerasimov.github.io/harness-rpg/#insights)

What counts is use, not installation: a skill or an MCP server that is installed but never called gives
the hero nothing.

## What the hero is made of

| On the page | Where it comes from |
|---|---|
| **Level and XP** | sessions with your turns, the turns themselves (capped per session) and active days |
| **Class** | the schools of your strongest talents: Smith (code), Ranger (investigations, debugging), Engineer (builds, releases, infrastructure), Alchemist (data), Bard (texts for people), Summoner (agents, orchestration, automation), Wanderer (everything beyond development); a hybrid when two schools are close |
| **Attributes** | STR, DEX, CON, INT, WIS and CHA on a 1–20 scale, from the quality of the work over the last 30 days |
| **Talents** | the skills you invoke; the score halves every 30 days without use, ranks go from Novice to Grandmaster, and the peak is kept |
| **Gear** | MCP servers, each worn in a slot — helmet (observability), amulet (databases), horn (messaging), boots (browser), grimoire (knowledge), ring (tasks), gloves (code), cloak (files) — or carried in the bag; rarity goes from common to legendary |
| **Auras** | hooks grouped by event; the strength is the share of last month's sessions in which an aura showed up |
| **Alignment** | law ↔ chaos (rules, planning, strict permissions) and good ↔ evil (checks and questions against destructive commands) |
| **Achievements** | 11 rare patterns, each with bronze, silver and gold medals; the best one becomes your title, and medals never go away |
| **Treasury and campfire rests** | gold from tokens weighted like their price, and rests from context compactions, both in tiers over the last month |

Every run adds a snapshot of the hero to the archive; ◀ ▶ (arrow keys, a swipe on a phone) flip through
the past ones.

## Two modes

**Game mode** is on whenever the page opens. It shows only aliases — Claude makes up fantasy names like
“Scroll of Lore” or “Eye of the Watch” — ranks, rarities, attributes and the level: no real names of skills,
MCP servers, hooks or projects and no usage numbers. A screenshot of it is safe to show anyone.

**Insights** — the toggle in the archive bar — adds the real names, the numbers, the rules behind every
value and 4–7 findings Claude writes about your actual work over the last 30 days: where the time and the
money go, where the friction is, what holds the work together. Every finding ends with a concrete change in
settings, permissions, skills, MCP servers, hooks, `CLAUDE.md` or session habits.
[See the findings in the demo.](https://dmitrygerasimov.github.io/harness-rpg/#insights)

**Screenshot** saves a PNG of what the page shows now, in the current mode, without the archive bar.

> The insights layer lives in the same `character.html` and `history.json`: whoever gets the file sees
> everything. Share the game-mode screenshot, not the file.

## Language

The page speaks your language. **If you mostly talk to Claude Code in Russian, the hero page is generated in
Russian; otherwise it is in English.** The script counts the language of your own messages in the
transcripts — code, pasted text, paths and system tags don't vote — and once the page has a language, it
switches only when the other one gets at least 60% of the votes.

To choose the language yourself, pass `--lang ru` or `--lang en` after a subcommand for one run, or set
`HARNESS_RPG_LANG=en` for good (for example, in the `env` block of your Claude Code settings).

## Install

You need Claude Code and Python 3.9 or newer (the standard library only), on macOS or Linux.

**As a plugin.** In Claude Code, run:

```
/plugin install harness-rpg --marketplace DmitryGerasimov/harness-rpg
```

On Claude Code older than 2.1.275, add the marketplace first:

```
/plugin marketplace add DmitryGerasimov/harness-rpg
/plugin install harness-rpg@harness-rpg
```

The plugin updates through `/plugin`, and its skill is `/harness-rpg:harness-rpg`.

**As a skill folder.** Get the latest release:

```bash
curl -fsSL https://github.com/DmitryGerasimov/harness-rpg/releases/latest/download/harness-rpg.zip -o /tmp/harness-rpg.zip
rm -rf ~/.claude/skills/harness-rpg && unzip -q /tmp/harness-rpg.zip -d ~/.claude/skills/
```

Run the same commands to update. The skill is `/harness-rpg`.

Choose one way: with both, Claude Code sees two copies of the same skill. Either way the hero's data lives in
`~/.harness-rpg/`, so it survives updates and a switch from one way to the other.

## Usage

Ask Claude Code “show my hero”, “what level am I” or “my character sheet”, or run the skill's command. Claude
then:

1. reads new and changed transcripts into the ledger (`update`);
2. sorts out what is new (`classify`): a school for every skill, a slot for every MCP server and a fantasy
   alias for both;
3. computes the hero, adds a snapshot to the archive and writes the page (`render`);
4. reads a summary of your real work and attaches its findings to the snapshot (`digest`, `insights`);
5. shows a compact hero card right in the chat where inline widgets are available, as in the Claude desktop
   app (`card`);
6. answers with a short summary of the hero and the command that opens the page:

   ```bash
   open ~/.harness-rpg/character.html
   ```

   On Linux, use `xdg-open` instead of `open`.

The skill pre-approves its own script, so these steps don't ask for permission. It writes to `~/.harness-rpg/`,
so it does not run in plan mode.

Claude Code deletes transcripts older than about 30 days (`cleanupPeriodDays`). The ledger keeps every
session it has read, so run the skill every few weeks and the hero remembers your whole history.

## Privacy

Everything stays on your machine. The script reads the transcripts in `~/.claude/projects` and writes to
`~/.harness-rpg/`; the page is a single self-contained HTML file with no network requests, and there is no
telemetry or update check. The ledger keeps counters and names — projects, skills, tools, file names of hook
scripts — not the text of your conversations. Of a hook's command line it keeps only the script's file name or
the program, never the arguments or the variables set before it.

## Troubleshooting

- **“NO SESSIONS FOUND”.** The script looks for transcripts in `$CLAUDE_CONFIG_DIR/projects`, that is
  `~/.claude/projects` by default. If yours live elsewhere, pass `--projects-dir DIR` before the subcommand.
- **Claude asks you to leave plan mode.** The skill writes files, so it doesn't run in plan mode: switch the mode
  (Shift+Tab in the terminal) and ask again.
- **The hero forgot old work.** The ledger knows only the sessions it has read, and Claude Code deletes
  transcripts after about 30 days. Run the skill every few weeks.
- **Python.** `python3 --version` must say 3.9 or newer. On a Mac without the Xcode Command Line Tools,
  `/usr/bin/python3` asks to install them first.
- **Windows** isn't supported yet.

## Command line

Claude runs the script for you, but you can run it too: `~/.claude/skills/harness-rpg/scripts/rpg.py` for the
skill folder, or the same `scripts/rpg.py` inside the plugin's folder under `~/.claude/plugins/`.

| Command | What it does |
|---|---|
| `rpg.py update` | transcripts → ledger; prints the page language and what needs classifying |
| `rpg.py classify FILE` | merges Claude's classification answers into the catalog |
| `rpg.py render` | hero → snapshot in the archive → page |
| `rpg.py digest` | prints a summary of the real work for the findings |
| `rpg.py insights FILE` | attaches the findings to the latest snapshot |
| `rpg.py card` | prints the chat card as an HTML fragment |
| `rpg.py --version` | prints the version, for bug reports |

`--home DIR` (or `HARNESS_RPG_HOME`, `~/.harness-rpg` by default) and `--projects-dir DIR`
(`$CLAUDE_CONFIG_DIR/projects`, that is `~/.claude/projects`, by default) go before the subcommand;
`--lang ru|en` goes after `update`, `classify` or `render`. Every `render` adds a snapshot to your archive,
so to experiment, point `--home` at a copy of the folder or at the example in `data/`.

## Data

| File in `~/.harness-rpg/` | What it is |
|---|---|
| `ledger.json` | the journal of sessions; it grows over time and outlives deleted transcripts |
| `catalog.json` | the schools, aliases and slots Claude assigned |
| `history.json` | the archive of page snapshots — the only copy of past heroes |
| `achievements.json` | the medals earned; they never go away |
| `character.json` | the full computation of the latest hero |
| `character.html` | the page |

Don't edit `history.json` or `catalog.json` by hand: the catalog changes only through `classify`.

The scenario Claude follows is in [`skill/SKILL.md`](skill/SKILL.md). All formulas, thresholds and constants
are in [`skill/reference.md`](skill/reference.md), which is written in Russian.

## Uninstall

- The plugin: `/plugin uninstall harness-rpg@harness-rpg`.
- The skill folder: `rm -rf ~/.claude/skills/harness-rpg`.
- The hero itself: `rm -rf ~/.harness-rpg`. This deletes the ledger and the archive of past heroes for good.

## Example

[`data/`](data) holds a synthetic example: two months of work of a made-up developer with popular skills and
MCP servers, run through the real pipeline. [`data/en/`](data/en) is the same hero of someone who writes in
English. Both pages are the [live demo](https://dmitrygerasimov.github.io/harness-rpg/), and
`python3 data/generate.py` rebuilds them.

## Development

```
.claude-plugin/           the marketplace manifest for the plugin install
skill/                    the skill, installed into ~/.claude/skills/harness-rpg or as the plugin
  .claude-plugin/         the plugin manifest
  SKILL.md                the scenario Claude follows
  reference.md            formulas, thresholds and page rules
  scripts/rpg.py          the CLI (Python 3, standard library only)
  scripts/harness_rpg/    the logic, one module per part of the hero: transcripts, catalog, skills, gear, …
  assets/template.html    the page: HTML, CSS and JS in one file
tests/                    tests, one file per area
data/                     the synthetic example and its generator; the live demo is built from it
```

Run the tests from the repository root:

```bash
python3 -m unittest discover -s tests -t .
```

Copy your working tree over the installed skill to try it in Claude Code:

```bash
rsync -a --delete --exclude __pycache__ --exclude .DS_Store --exclude .claude-plugin skill/ ~/.claude/skills/harness-rpg/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the rules a change has to keep.

A release is a pushed `vX.Y.Z` tag that matches the version in `skill/scripts/harness_rpg/__init__.py` and
`skill/.claude-plugin/plugin.json`: the workflow runs the tests, builds `harness-rpg.zip`, checks `render` from
the unpacked archive on the example and publishes the release. Every push to `main` runs the tests on Python
3.9–3.14 and macOS's own Python, checks that the example is rebuilt, and redeploys the demo when it changes.

## License

[MIT](LICENSE)
