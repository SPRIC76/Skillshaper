# Skillshaper

Enhanced agent skill for **creating, improving, validating, and packaging** agent skills with stricter quality and **mandatory dual output**.

**Voice:** Standards enforcer — quality and packaging, not creative writing.

## Install via skills.sh CLI

```bash
npx skills add SPRIC76/skillshaper
```

**Badge snippet:**

```markdown
[![skills.sh](https://skills.sh/b/SPRIC76/skillshaper)](https://skills.sh/SPRIC76/skillshaper)
```

## What skillshaper adds

Skillshaper supplements Anthropic's skill-creator workflow with:

| Requirement | Detail |
|-------------|--------|
| Validation | `scripts/validate_skill.py` — the upload rules (allowed frontmatter keys, a kebab-case name equal to its folder, a description of at most 1024 characters with no angle brackets, a body under 500 lines) plus stricter checks: a when-to-use cue in the description, every referenced file present, bundled Python that compiles, no orphan or junk files, no sandbox paths or hard-coded user folders |
| Dual packaging | Every skill ships as `{name}.skill` **and** `{name}-vX.Y.zip`, validated first; any error stops packaging |
| Local install | `--deploy` replaces an installed copy's contents in place, so links to that folder keep working |
| Documentation | Progressive disclosure; references stay scannable |

## Install (Cursor)

```text
~/.cursor/skills/skillshaper/
# or
.cursor/skills/skillshaper/
```

Copy this entire folder. Pair with Cursor's built-in **create-skill** guidance for the full authoring workflow; skillshaper is the stricter **packaging overlay**.

## Install (Claude)

### claude.ai and Claude Desktop

1. Package the folder: `python scripts/package_dual.py ./skillshaper --version 1.1 --output ./dist`
2. Upload `skillshaper.skill` in your skill settings, or drag it into Claude Desktop.
3. Confirm skillshaper appears in your skills.

### Claude Code

Copy the folder to `~/.claude/skills/skillshaper/` (all projects) or `.claude/skills/skillshaper/` (one project).

## Usage

Validate one or more skills:

```bash
python scripts/validate_skill.py <path/to/skill-folder> [--strict]
```

Package (validation runs first):

```bash
python scripts/package_dual.py <path/to/skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-folder>] [--strict]
```

**Example:**

```bash
python scripts/package_dual.py ./my-skill --version 1.0 --output ./dist
```

Produces:

| File | Purpose |
|------|---------|
| `my-skill.skill` | Upload to claude.ai or drag into Claude Desktop |
| `my-skill-v1.0.zip` | Versioned archive for keeping and for manual installs |

Both are zip archives with `my-skill/SKILL.md` as the root entry. `evals/` and `tests/` at the skill root, `*-workspace` folders, `__pycache__`, `node_modules`, `.git` and OS junk are left out.

`--deploy ~/.agents/skills` also installs the packaged skill into that folder, replacing the existing copy's contents in place. It refuses to write through a link, or over a folder whose `SKILL.md` names a different skill.

## Platform notes

| Platform | Install path |
|----------|--------------|
| **Cursor** | `~/.cursor/skills/<name>/` or `.cursor/skills/<name>/` |
| **claude.ai / Claude Desktop** | Upload or drag in `<name>.skill` |
| **Claude Code** | `~/.claude/skills/<name>/` or `.claude/skills/<name>/` |
| **Other agents** | Extract the `.zip` into the agent's skills directory |

## Other IDEs and agents

Skillshaper can be used anywhere an agent runtime supports folder-based skill instructions:

- Import/copy the `skillshaper/` folder as a skill package.
- Ensure the runtime can execute the scripts (Python 3.10+ recommended; standard library only).
- If the IDE has no skill system, you can still run the validator and packager manually from a terminal.

## Pre-package checklist

The validator checks each of these; `--strict` treats warnings as errors.

- [ ] `SKILL.md` frontmatter: `name` (kebab-case, equal to the folder) + `description` (what it does and when to use it)
- [ ] Body under 500 lines; depth in `references/`
- [ ] All referenced files exist; bundled scripts compile
- [ ] No `__pycache__`, `.pyc`, `node_modules`, junk files
- [ ] No sandbox-only paths or personal user folders

## Repository layout

```text
SKILL.md
scripts/package_dual.py
scripts/validate_skill.py
```

## License

Freeware — see [LICENSE](LICENSE). Copyright (c) 2026 MK1 Enterprise. Free to download and use; please link to this repository rather than rehosting it. Versions up to commit 5d20f49 were released under MIT and keep it.

---

Skillshaper · [Freeware](LICENSE)

[MK1 Made](https://mk1made.us) • *deliberately designed, intelligently refined*
<p align="right">Artificer Intelligence</p>
