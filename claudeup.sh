# 1. From your machine, create the folder structure
mkdir -p docs/USER_STORIES docs/STRATEGIC_CONTEXT docs/ENGINES
mkdir -p src/pi_builder/adapters/rainfall src/pi_builder/adapters/dem
mkdir -p src/pi_builder/standards/irc

# 2. Move existing engine docs into ENGINES folder
mv docs/system-architecture.md docs/ENGINES/
mv docs/gis-engine.md docs/ENGINES/
mv docs/rainfall-engine.md docs/ENGINES/
mv docs/hydrology-engine.md docs/ENGINES/
mv docs/hydraulics-engine.md docs/ENGINES/
# (keep dem-processing-pipeline.md, epc-hydrology-workflow.md etc. in docs/ENGINES/ too)

# 3. Drop the new files in the right places
# CLAUDE.md → repo root
# GAMEPLAN.md → repo root
# CONVERSATION_DIGEST.md → docs/
# 06_authoritative_sources.md → docs/
# 00_strategic_refinement.md → docs/STRATEGIC_CONTEXT/
# 01_pros_cons_analysis.md → docs/STRATEGIC_CONTEXT/
# epic_1 through epic_5_8 → docs/USER_STORIES/
# README.md (the master index) → docs/

# 4. Add stub files for the adapter layer
touch src/pi_builder/adapters/__init__.py
touch src/pi_builder/adapters/rainfall/__init__.py
touch src/pi_builder/adapters/rainfall/base.py
touch src/pi_builder/adapters/rainfall/imd_adapter.py
touch src/pi_builder/standards/__init__.py
touch src/pi_builder/standards/irc/__init__.py

# 5. Commit
git add -A
git commit -m "docs: add comprehensive user stories, CLAUDE.md, conversation digest, authoritative sources

- Replace stub engine docs with full user story specs (Epics 1-8)
- Add CLAUDE.md at repo root for Claude Code persistent context
- Add CONVERSATION_DIGEST.md capturing all key architectural decisions
- Add 06_authoritative_sources.md (textbook/IRC/IS code references)
- Add GAMEPLAN.md (18-week implementation timeline)
- Update strategic_refinement.md: IRC SP-13:2022, Rain2Flood, AQUAH
- Add adapter layer stubs for global extensibility
- Restructure docs/ into ENGINES/, USER_STORIES/, STRATEGIC_CONTEXT/"
