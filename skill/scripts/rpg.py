#!/usr/bin/env python3
"""harness-rpg: build an RPG character sheet from Claude Code transcripts.

Subcommands:
  update           parse new or changed transcripts into the ledger, print pending classification
  classify FILE    merge agent answers (skill schools, MCP names) into the catalog
  render           compute the character and write character.json + character.html
  digest           print the compact stats of the latest snapshot for the agent to find insights in
  insights FILE    attach the agent's findings to the latest snapshot and rewrite the page
  card             print a compact chat card of the latest hero, game view only, for an inline widget

The logic lives in the harness_rpg package next to this file.
"""

import sys

# The installed skill folder stays free of __pycache__.
sys.dont_write_bytecode = True

from harness_rpg.constants import MIN_PYTHON  # noqa: E402

if sys.version_info < MIN_PYTHON:
    sys.exit('harness-rpg needs Python %d.%d or newer, this is %s' % (MIN_PYTHON + (sys.version.split()[0],)))

from harness_rpg.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
