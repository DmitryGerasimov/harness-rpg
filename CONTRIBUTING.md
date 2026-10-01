# Contributing

Bug reports and pull requests are welcome. For a bug, open an issue with the version (`rpg.py --version`), how
you installed the skill and the output of the command that failed. **Don't attach `character.html`,
`history.json` or `ledger.json`:** they hold the real names of your projects, skills and servers.

## Before a pull request

- Run the tests from the repository root: `python3 -m unittest discover -s tests -t .`. They must pass on
  Python 3.9, the oldest one supported.
- Rebuild the example with `python3 data/generate.py` and commit `data/` along with the change: the example is
  the live demo, and CI fails when it is stale.
- If the page changed, open both example pages (`data/en/character.html` and `data/character.html`) in both
  modes, flip the archive with ◀ ▶, try a phone-width window and check that the console has no errors.

## Rules a change keeps

- **The standard library only.** No dependencies, no network, nothing to install besides Python.
- **The page is self-contained.** Everything is inlined in `skill/assets/template.html`; no CDN, no requests.
- **Two languages.** Every text on the page is written in Russian and in English at once: `TEXTS` in
  `texts.py`, `TEXTS` and `INSIGHT_TEXTS` in the template, with the same keys.
- **Game mode tells nothing.** Outside the insights layer the page shows no real names of skills, MCP servers,
  hooks or projects and no usage numbers, and it doesn't use tooling words (harness, agent, prompt, hook,
  skill, session, token, claude) — the hero has talents, not skills. `VocabularyCase` checks it.
- **The archive keeps working.** The page must render the snapshots of every older version. If you change the
  shape of a snapshot, bump `PUBLIC_SCHEMA_VERSION` and keep reading the old fields.
- **The ledger outlives transcripts.** Old sessions may lack a new field, because their transcripts are gone:
  read it with `.get`.
- **Formulas and thresholds** live in `constants.py` and are described in `skill/reference.md`; update it with
  them. A change in the scenario Claude follows goes into `skill/SKILL.md`.
- **Style.** Single quotes; new code goes into the module of its part of the hero, a new test into the test
  file of its area.

## Releases

A release is a pushed `vX.Y.Z` tag. Bump the version in `skill/scripts/harness_rpg/__init__.py` and
`skill/.claude-plugin/plugin.json` first: the release fails when the tag and the version differ, and plugin
users get the update only when the plugin version changes.
