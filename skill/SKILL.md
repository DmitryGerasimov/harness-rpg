---
name: harness-rpg
description: Builds an RPG hero from the person's Claude Code history — level, class, attributes, talents (skills), gear (MCP servers), auras (hooks) and achievements — and opens the hero's pixel-art page, with an insights mode of real names, numbers and findings about the actual work (where the time and the money go, where the friction is, what holds the work together). Use when asked to show the hero, the character or the character sheet of the harness — «show my hero», «my character sheet», «what level am I», «what class am I», «update my hero», «hero insights», «my harness RPG», «harness-rpg», or in Russian «мой персонаж», «покажи моего героя», «какой у меня уровень», «какой у меня класс», «прокачка харнесса», «обнови героя», «инсайты героя». Not for token usage reports or usage statistics.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py *)
---

# harness-RPG

The hero is the Claude Code harness on this machine. Use counts, not presence: a skill or an MCP server that is
installed but never called gives nothing. The script computes every number; don't recompute anything and don't
round it your own way. The data never leaves the machine.

The page has two modes. Game mode is open by default: only aliases, ranks, rarity, attributes, the level and the
period — no real names of skills, MCP servers or hooks, no tools, no paths, no statistics. A screenshot of it is
safe to show anyone. The «Insights» toggle in the archive bar adds the real names, numbers, thresholds and
findings, and the «Screenshot» button captures what is on the screen now. What to share is the person's call.

Script: `${CLAUDE_SKILL_DIR}/scripts/rpg.py` (Python 3.9+, standard library only). Run it exactly the way the
commands below do, `python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py <command>`: this command is pre-approved.
Data folder: `~/.harness-rpg/` (or `HARNESS_RPG_HOME`) — `ledger.json` (the accumulating journal of sessions),
`catalog.json` (the classification), `history.json` (the archive of page snapshots with the insights layer and
the findings), `achievements.json` (the achievements earned — for good), `character.json` and `character.html`
(the result).

## Page language

The page speaks the person's language: Russian if they mostly write to Claude Code in Russian, English otherwise.
The script decides: `update` counts the language votes of the person's messages in the transcripts (code, pasted
text, paths and system tags don't vote) and prints `language: ru` or `language: en`. Once chosen, the language
changes only when the other one clearly outweighs it. Don't guess or change the language yourself.

- Everything you write for the page is in its language: the aliases (`lang` in the `update` output) and the
  findings (`lang` in the `digest` output). `classify` and `insights` reject an answer in the wrong language.
- Reply to the person in the language they write in this conversation.
- Only if the person asks for the page in another language: `--lang ru|en` after the subcommand
  (`rpg.py render --lang en`) works for one run — pass it to `update`, `classify` and `render` alike. A lasting
  choice is the environment variable `HARNESS_RPG_LANG=en` (for example, in the `env` block of the Claude Code
  settings).

## Scenario

The script writes to the data folder. In plan mode nothing may be written: right away, without running anything
or drafting a plan, ask in one sentence to leave plan mode (Shift+Tab in the terminal, the mode switcher in the
desktop app) and to repeat the request.

1. **Update the ledger:**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py update
   ```
   The ledger accumulates sessions and keeps them after Claude Code deletes old transcripts
   (`cleanupPeriodDays`, 30 days by default), so running `update` regularly pays off.
   If it prints `NO SESSIONS FOUND`, stop and don't render an empty hero: tell the person which folder the
   script looked in and that `--projects-dir DIR` before the subcommand (or `CLAUDE_CONFIG_DIR`) points it at
   the folder where Claude Code keeps its transcripts.

2. **Classify what's new** if `update` printed `PENDING CLASSIFICATION`. The `need` field of each item says
   what is missing:
   - `school` of a skill — one of `schools`, by the skill's name and description: `smith` (code, refactoring,
     tests), `ranger` (investigations, debugging, incidents), `engineer` (builds, releases, deploys,
     infrastructure), `alchemist` (data, queries, analytics), `bard` (texts for people: documentation,
     articles, letters, posts, reports, translations, style editing), `summoner` (agents, orchestration,
     automation, setting up the harness, memory and notes for agents), `wanderer` (everything beyond
     development: home, hobbies, personal matters — cooking, finance, music, travel). The school follows the
     skill's main purpose, not the project. Don't stretch a household skill onto a work school — that's what
     `wanderer` is for.
     In Claude Code almost everything is done in text, so `bard` is only for when the text itself is the result
     for people. Text as a way to work with an agent — prompts, notes and memory for agents, plans, task
     descriptions, handing work over between sessions — is not bard: such a skill goes to the school of the work
     it serves, and a general tool for agents (a prompt library, memory, a notes store) goes to `summoner`.
     If `need` has `school` while the skill already has one, it is a recheck under a refined rule: keep the
     school or change it — after the answer the skill won't be asked again;
   - `name` of an MCP server (servers with a uuid instead of a name — that's how the Claude desktop app names
     claude.ai connectors) — the real name, by `sample_tools` and by what you know about the connected servers
     (`slack_*` → `Slack`, `notion-*` → `Notion`). It is only used for grouping and never reaches the page.
     A service server of the harness rather than a tool gets `null` and stays out of the inventory;
   - `alias` — a fantasy name for the page, 1–3 words in the page language (`lang`), after what the skill or the
     server does: in Russian «Свиток заметок», «Око дозора», «Перековка форпоста», in English «Scroll of Lore»,
     «Eye of the Watch», «Forge of the Outpost». No names of products, services, companies, projects or domains
     and no transliteration of the real name — the alias must not give away which tool it is. Skills get
     techniques and crafts, MCP servers get pieces of gear. Don't repeat aliases. `classify` rejects an alias
     with Latin letters on a Russian page or Cyrillic on an English one, longer than 40 characters, with harness
     words (сессия, токен, скил, агент… / session, token, skill, agent…) or with a piece of the real name of
     4 letters or more, even spelled apart («Lin Ear Ring») — such an item stays in `need`, come up with another
     one. The script can't catch transliteration («Линеар»): that is on you. Aliases are kept per language:
     after the page language changes, `update` asks once for aliases in the new one, and the old ones stay;
   - `slot` of an MCP server — where the item is worn, by the server's main purpose, one of `slots`: `helmet`
     (observability: logs, metrics, monitoring, infrastructure), `amulet` (databases), `horn` (communication:
     messengers, mail), `boots` (browser), `grimoire` (knowledge: documentation, notes, knowledge bases), `ring`
     (tasks: trackers, projects), `gloves` (code: repositories, builds, reviews), `cloak` (files and cloud
     storage), or `bag` if none fits. A slot holds one item — the strongest; the rest go to the inventory by
     themselves, so don't spread them out artificially;
   - `split` of an MCP server — a server with several tool families (`families`: the prefix before the first
     `_` → sample tools). Decide by the tools whether it is one thing or several:
     - all the families serve one purpose and fit one slot — it is one thing with sections, answer
       `"families": {}`;
     - the families serve different purposes and fit different slots — split the server into categories
       **entirely**: every family from `families` goes into exactly one category, and there is no «whole
       server» or «the rest» item. A category is one purpose and one slot: gather the families of one purpose
       into it with `prefixes` instead of making an item per prefix. A category's real name is the server's name
       plus its purpose (`<Server> Mail`, `<Server> Calendar`), not the bare server name: it must tell the
       category from its neighbours. Each category has its own alias and slot; the server's own `alias` and
       `slot` aren't needed.

     `classify` rejects a split that leaves any family without a category. The decision is cached; if a split
     server later gets a new family, it comes back with `split` and `current_families` — send all the categories
     again, with the new family added to a fitting category or to a new one.

   Write the answers as JSON into a temporary folder (the scratchpad, if there is one) and pass the file to
   `classify`. Write the file with the file-writing tool and run the script as a separate command — no `cd`,
   no `echo >`, no `&&` chains: that way every call matches the pre-approved `rpg.py` command and the person
   isn't asked to confirm anything extra. For MCP, answer under any one server from `servers`; fields missing
   from the answer keep their previous values:
   ```json
   {
    "skills": {"<name>": {"school": "bard", "alias": "Scroll of Lore"}},
    "mcp": {
     "<one of servers>": {"name": "Linear", "alias": "Book of Errands", "slot": "ring"},
     "<server with split>": {"families": {
      "mail": {"name": "<Server> Mail", "alias": "Herald's Horn", "slot": "horn", "prefixes": ["mail", "inbox"]},
      "calendar": {"name": "<Server> Calendar", "alias": "Hourglass", "slot": "bag", "prefixes": ["calendar"]}
     }}
    }
   }
   ```
   On a Russian page the same answer has Russian aliases: «Свиток заметок», «Книга поручений», «Рог гонца»,
   «Песочные часы».
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py classify <answers file>
   ```
   The classification is cached: the same skills won't be asked about again. To reclassify a skill or change an
   alias, pass it to `classify` with the new values. Don't edit `catalog.json` by hand. Without an alias the page
   shows «Unnamed talent N» / «Unnamed artifact N» (on a Russian page «Безымянный приём N» / «Безымянный
   артефакт N»).

3. **Render:**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py render
   ```
   The command prints the level, the class, the top talents and gear, the talents slowly being forgotten, the
   size of the archive and the path to `character.html` (the `html:` line). Every `render` puts a new snapshot of
   the hero into the `history.json` archive; the page shows the latest one, and the ◀ ▶ arrows (the ←/→ keys,
   a swipe on a phone) flip through the past ones. The «Insights» button there turns on the details, the
   findings and the progression across the archive; «Screenshot» saves a PNG of the open snapshot in the current
   mode, without the archive bar and the line with the dates. A snapshot whose game part doesn't differ from the
   latest one replaces it instead of piling up.
   Don't edit or delete `history.json`: it is the only copy of the past heroes.

4. **Find insights** if `render` printed `INSIGHTS PENDING`:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py digest
   ```
   The command prints compact facts about the real work over the last 30 days (`reality`): sessions and their
   length, background runs, the rhythm by hours, weekdays and weeks, projects (sessions, hours, calls, errors,
   gold), money (tokens by kind, the dearest sessions), autonomy and friction (actions per turn, interruptions,
   denials, permission modes, subagents, compactions), quality (tool and edit errors, edits without checks,
   tests and linters, commits, destructive commands), built-in tools, skills (the main ones, the new ones of the
   week, the ones abandoned for two weeks), MCP servers with their tools and hooks with their scripts. It also has
   `page_names` — what skills and MCP servers are called on the page — and `previous_findings`, the titles of the
   past findings.

   **Findings are about reality, not the game, and useful for working with Claude Code.** The page already shows
   ranks, medals, classes, levels, auras and tiers — don't write about them. A finding is not just a curious
   fact but a hint at what to change in how the person uses the harness: in settings, permissions, skills, MCP
   servers, hooks, `CLAUDE.md` or session habits. An observation that leads nowhere («Sunday nearly catches up
   with Wednesday») is not a finding — skip it. 4–7 findings; where to look:
   - money and context: how much goes to re-reading the context, which sessions and projects cost the most and
     why (hours, subagents, compactions) → a new session for a new task, `/compact` earlier, long investigations
     to subagents, no dragging one session for days;
   - friction: how many turns run into a denial or an interruption, which permission mode the work goes in →
     frequent safe commands into the permissions (allow), dangerous ones into deny;
   - quality: edits without tests and linters, the share of errors → a rule in `CLAUDE.md` or a hook that runs
     the checks after edits;
   - tools: which skills and MCP servers hold the work, what is abandoned, which MCP tools are barely needed, what
     the hooks do and how often they fire → repeated work into a skill, the abandoned removed or refreshed,
     a hook on every call checked for extra delay;
   - autonomy: how many actions per turn, plan mode, subagents → where it pays to plan ahead or to parallelize
     the work with helpers.

   The rules of a finding: `title` is a short headline (up to 70 characters), `text` is 1–3 sentences (up to
   400): a fact with numbers from the digest → what it means → what exactly to do in Claude Code. The advice must
   follow straight from the numbers; no generic advice like «write better prompts». You may add and divide the
   numbers, not invent new ones. `tone`: `rise` — what works and is worth keeping or extending, `fall` — what is
   worth changing, `note` — neutral, but still with a conclusion. Write in the page language (`lang` in the
   digest), with the real names of projects, skills, MCP servers, tools and hooks, and the numbers by its rules:
   in Russian a decimal comma and a space between thousands (421,8; 7 823), in English a decimal point and a
   comma (421.8; 7,823). Don't repeat `previous_findings` unless something new turned up behind them.
   Write the answer as JSON into a temporary folder and pass the file to `insights`:
   ```json
   {"findings": [{"title": "Long sessions pay for re-reading",
                  "text": "72% of the gold is cache reads; the dearest session ran for 6 days with 32 subagents. A new task deserves a new session, and long investigations are better handed to subagents.",
                  "tone": "fall"}]}
   ```
   On a Russian page the same finding: `"title": "Долгие сессии платят за перечитывание"`,
   `"text": "72% золота — чтение кэша; самая дорогая сессия тянулась 6 дней с 32 сабагентами. ..."`.
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py insights <findings file>
   ```
   The findings go into the latest snapshot and stay until the hero changes: a snapshot with the same game part
   takes them over.

5. **Show the hero card in the chat** if the environment has the inline widget tool `show_widget` (the Claude
   app and claude.ai have it; Claude Code in a terminal doesn't — then skip this step):
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/rpg.py card
   ```
   The command prints a ready HTML fragment — pass it to `show_widget` as it is, changing and adding nothing
   (before the first `show_widget` call in a conversation the tool requires reading its `read_me`). The card is
   game mode only: the avatar, the level and XP, the class, the title, the attributes, the strongest talents, the
   gear worn, the alignment, the aura and the medals; no real names and no numbers of the work. The «Open the hero
   page» button sends the message «Open the hero page» to the chat (on a Russian card «Открой страницу героя») —
   on it, open the page yourself: `open` on macOS, `xdg-open` on Linux, with the path from the `html:` line of
   `render`.

6. **Answer briefly:** the level, the class (and which schools it is made of), the title, the alignment, the 2–3
   strongest talents, the best item, the strongest aura, what is slowly being forgotten, which achievements are
   new, and one or two main findings. Call talents and items by their aliases, with the real name in brackets.
   Say that the details are under the «Insights» («Инсайты») button on the page. Don't retell the chat card in
   text. Answer in the language of the conversation, with the numbers by its rules. Only the hero goes into the
   answer: no connector status, no system reminders, no environment settings — even if they are visible in the
   context.

7. **Give the command that opens the page — always, at the very end of the answer.** The page is a
   self-contained file with no network. End the answer with a separate `bash` block with exactly one command,
   no `$` and no explanations inside the block: `open` with the path from the `html:` line of `render`
   (`xdg-open` on Linux). With the default data folder it is:
   ```bash
   open ~/.harness-rpg/character.html
   ```
   In the Claude desktop app such a block has a Run button: the person opens the page with one click. In a
   terminal the command is copied. Don't open the page yourself — only give the block (the exception is the card
   button from step 5).

## How it is computed

In short: the level comes from sessions, the person's turns and active days; talents and gear from the number of
sessions with a call, halving every 30 days (the current level and the peak); attributes from quality ratios of
the work over the last 30 days; the class from the schools of the strongest talents, a hybrid when two schools
are close; auras from hooks by event type, the strength being the share of last month's sessions in which the
aura showed up; the alignment from law (rules, planning, strict permissions) and good (checks and questions
against destructive commands); 11 achievements for rare patterns, each with bronze, silver and gold, the title
being the achievement with the best medal; the treasury is gold from tokens weighted like their price, and the
campfire rests are compactions, both in tiers over a month with an open top (II, III…). Insights mode shows all
these numbers and thresholds right on the page.
All the formulas and constants are in `reference.md` next to this file (in Russian).
