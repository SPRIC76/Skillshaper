# Skillshaper

Enhanced agent skill for **creating, improving, validating, and packaging** agent skills with stricter quality and **mandatory dual output**.

**Voice:** Standards enforcer — quality and packaging, not creative writing.

The skill's id, and so its folder name, is `sc2`; Skillshaper is its name. Every install below lands this repository's `sc2/` folder under that name.

## Install via skills.sh CLI

```bash
npx skills add SPRIC76/skillshaper
```

**Badge snippet:**

```markdown
[![skills.sh](https://skills.sh/b/SPRIC76/skillshaper)](https://skills.sh/SPRIC76/skillshaper)
```

## What Skillshaper adds

Skillshaper supplements Anthropic's skill-creator workflow with:

| Requirement | Detail |
|-------------|--------|
| Validation | `sc2/scripts/validate_skill.py` — the upload rules (allowed frontmatter keys, a kebab-case name equal to its folder, a description of at most 1024 characters with no angle brackets, a body under 500 lines) plus stricter checks: a when-to-use cue in the description, every referenced file present, bundled Python that compiles, UTF-8 throughout, no orphan or junk files, no sandbox paths or hard-coded user folders |
| Dual packaging | Every skill ships as `{name}.skill` **and** `{name}-vX.Y.zip`, validated first; any error stops packaging |
| Local install | `--deploy` replaces an installed copy's contents in place, so links to that folder keep working; it touches only an absent or empty folder, or its own skill |
| Documentation | Progressive disclosure; references stay scannable |

## Install (Cursor)

```text
~/.cursor/skills/sc2/
# or
.cursor/skills/sc2/
```

Copy the `sc2/` folder there, keeping its name. Pair with Cursor's built-in **create-skill** guidance for the full authoring workflow; Skillshaper is the stricter **packaging overlay**.

## Install (Claude)

### claude.ai and Claude Desktop

From the repository root:

1. Package the skill: `python sc2/scripts/package_dual.py sc2 --version 1.4 --output dist`
2. Upload `dist/sc2.skill` in your skill settings, or drag it into Claude Desktop.
3. Confirm `sc2` (Skillshaper) appears in your skills.

### Claude Code

Copy the `sc2/` folder to `~/.claude/skills/sc2/` (all projects) or `.claude/skills/sc2/` (one project).

## Usage

From the repository root, or with the path to wherever `sc2/` is installed.

Validate one or more skills:

```bash
python sc2/scripts/validate_skill.py <path/to/skill-folder> [--strict]
```

Package (validation runs first):

```bash
python sc2/scripts/package_dual.py <path/to/skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>] [--strict]
```

**Example** — the skill packages itself:

```bash
python sc2/scripts/package_dual.py sc2 --version 1.4 --output dist
```

Produces:

| File | Purpose |
|------|---------|
| `dist/sc2.skill` | Upload to claude.ai or drag into Claude Desktop |
| `dist/sc2-v1.4.zip` | Versioned archive for keeping and for manual installs |

Both are zip archives with `sc2/SKILL.md` as the root entry. `evals/` and `tests/` at the skill root, `*-workspace` folders, `__pycache__`, `node_modules`, `.git`, dotfiles such as `.gitignore` and `.env`, and OS junk are left out. A folder or file reached through a junction or symlink is packaged like any other; a link loop, or a link out to the archives, is not followed. Text files are written with LF line endings whatever the checkout uses (`.md`, `.txt`, `.py`, `.json`, `.yaml`, `.sh`, `.js`, `.html`, `.rst`, `.go` and the other text types listed in `TEXT_SUFFIXES`, a file with no suffix that holds UTF-8 text such as `LICENSE`, and any script that starts with `#!`); every other file stays byte-for-byte, a PDF or a calendar file included. The archives go outside the skill folder: run from inside it, they land beside it; an `--output` inside it is refused.

`--deploy ~/.agents/skills` also installs the packaged skill into `~/.agents/skills/sc2/`, replacing that folder's contents in place — only when the folder is absent, empty, or an installed copy of the same skill. Anything else (another skill, a folder of other files, a file, a symlink or junction, the very folder being packaged, or a working copy holding `.git`, `.env`, `tests/` or anything else the package leaves out) is refused before anything is built, and nothing changes. The replacement lands whole or the old copy is put back; read-only files in the old copy are replaced too.

## Tests

From the repository root:

```bash
python -B -m unittest discover -s tests -v
```

Standard library only; every fixture is built in a temporary folder. The tests live in `tests/` beside `sc2/`, not inside it, so packaged and deployed copies stay identical to the development copy.

## Platform notes

| Platform | Install path |
|----------|--------------|
| **Cursor** | `~/.cursor/skills/sc2/` or `.cursor/skills/sc2/` |
| **claude.ai / Claude Desktop** | Upload or drag in `sc2.skill` |
| **Claude Code** | `~/.claude/skills/sc2/` or `.claude/skills/sc2/` |
| **Other agents** | Extract `sc2-v1.4.zip` into the agent's skills directory |

## Other IDEs and agents

Skillshaper can be used anywhere an agent runtime supports folder-based skill instructions:

- Import/copy the `sc2/` folder as a skill package.
- Ensure the runtime can run the scripts (Python 3.10+; standard library only).
- If the IDE has no skill system, you can still run the validator and packager manually from a terminal.

## Pre-package checklist

The validator checks each of these; `--strict` treats warnings as errors.

- [ ] `SKILL.md` frontmatter: `name` (kebab-case, equal to the folder) + `description` (what it does and when to use it)
- [ ] Body under 500 lines; depth in `references/`
- [ ] All referenced files exist; bundled scripts compile
- [ ] `SKILL.md` and bundled text files are UTF-8, without a BOM
- [ ] No `__pycache__`, `.pyc`, `node_modules`, junk files
- [ ] No sandbox-only paths or personal user folders

## Repository layout

```text
sc2/SKILL.md
sc2/scripts/package_dual.py
sc2/scripts/validate_skill.py
tests/test_package_dual.py
tests/test_validate_skill.py
LICENSE
README.md
```

## License

Freeware — see [LICENSE](LICENSE). Copyright (c) 2026 MK1 Enterprise. Free to download and use; please link to this repository rather than rehosting it. Versions up to commit 5d20f49 were released under MIT and keep it.

---

Skillshaper · [Freeware](LICENSE)

[MK1 Made](https://mk1made.us) • *deliberately designed, intelligently refined*
<p align="right">Artificer Intelligence</p>
