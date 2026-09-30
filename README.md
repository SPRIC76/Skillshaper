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
| Validation | `sc2/scripts/validate_skill.py` — the upload rules (frontmatter that is valid YAML, read the same with and without PyYAML for the shapes a SKILL.md uses, a shape the built-in reader does not take refused by name; allowed frontmatter keys, a kebab-case name equal to its folder, a description that is text, at most 1024 characters, with no angle brackets, a body under 500 lines) plus stricter checks: a when-to-use cue in the description, every referenced file present (in SKILL.md and every other text file the package ships; a name with a space, or its `%20` form in a link, resolved) and none a dotfile the package leaves out, bundled Python that compiles (`.py` in any letter case), UTF-8 throughout with any BOM named in every text file the package ships, root-level ones included (an error where it breaks the file: before the `#!` line of a script that is run by name, at the start of a `.sh`, or in a `.json`; a non-UTF-8 file outside `references/`, `scripts/` and `assets/` is a warning), every bundled file readable and every folder listable, no orphan or junk files, no sandbox paths or hard-coded user folders |
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

Both are zip archives with `sc2/SKILL.md` as the root entry.

- **Left out:** `evals/` and `tests/` at the skill root, `*-workspace` folders, `__pycache__`, `node_modules`, `.git`, `.pytest_cache`, `.pyc` files, dotfiles such as `.gitignore` and `.env`, and OS junk (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX`).
- **Links:** a folder or file reached through a junction or symlink is packaged like any other; a link loop, or a link out to the archives, is not followed.
- **Line endings:** a file is written with LF whatever the checkout uses when all of it is UTF-8 text with no NUL byte and it is a text type (`.md`, `.txt`, `.py`, `.json`, `.yaml`, `.sh`, `.js`, `.html`, `.rst`, `.go` and the others listed in `TEXT_SUFFIXES`), a file with no suffix such as `LICENSE`, or a script that starts with `#!`; every other file stays byte-for-byte, a PDF, a calendar file or a script carrying a binary payload included.
- **Where the archives go:** outside the skill folder. Run from inside it, they land beside it (beside its real folder when the path given reaches the skill through a link that loops back into it), and a file linked in from beside it, or from beside the link the skill is reached through (the repository's `LICENSE`), is still packaged; an `--output` inside the skill or inside the deploy target, or one that is a file, is refused. Run from inside `sc2/` with no `--output`, the archives land in the repository root, which `.gitignore` covers (`sc2.skill`, `sc2-v*.zip`, `dist/`).
- **Whole or not at all:** each archive is built under a temporary name beside its target and the pair is moved into place only when both are complete.
- **One message per failure:** a file or folder that cannot be read, an archive that cannot be replaced (left read-only or held open, or a folder standing at its name), an `--output` that cannot be made or that takes no new file from this user (`C:\`, a folder an ACL denies), a skills home that takes no new folder from this user, and a full disk each stop the run at once with one message naming the file and the reason; the earlier archives are untouched.
- **`--version`** takes digits, letters, dots and dashes, starting and ending with a digit or letter, at most 64 characters (`1.0`, `2.1-rc1`), so the `.zip` always lands in `--output` under a name every file system takes.
- **Dates:** the zip format holds dates from 1980 to 2107. A file dated before 1980 is stored dated 1980-01-01, one dated after 2107 is stored dated 2107-12-31, and each edge is named once for all its files; a file whose date Windows cannot express at all (before 1970, or past about the year 3000) is packaged the same way, never refused as unreadable.

`--deploy ~/.agents/skills` also installs the packaged skill into `~/.agents/skills/sc2/`, replacing that folder's contents in place — only when the folder is absent, empty, or an installed copy of the same skill. Anything else (another skill, a folder of other files, a file, a symlink or junction, the very folder being packaged, or a working copy, marked by `.git`, `.env`, `.envrc`, `.venv`, `.hg`, `.svn`, a `*-workspace` folder, or `tests/` or `evals/` at its root) is refused before anything is built, and nothing changes; so is a skills home that exists but takes no new folder from this user. Anything else an older install holds that the package leaves out, such as a `.gitignore` earlier versions shipped, is replaced and named; OS junk and caches pass unmentioned. The replacement lands whole or the old copy is put back; read-only files and folders in the old copy are replaced too.

## Tests

From the repository root:

```bash
python -B -m unittest discover -s tests -v
```

Standard library only; every fixture is built in a temporary folder. The tests live in `tests/` beside `sc2/`, not inside it, so packaged and deployed copies stay identical to the development copy. The frontmatter parity tests run the same table of shapes through the built-in reader and, where PyYAML is installed, through PyYAML; each shape's verdict was recorded from PyYAML 6.0.3, so the parity is checked without PyYAML too. On Windows, three tests set an ACL deny on a temporary folder with `icacls` and lift it afterwards; if a run is killed inside one, `icacls <folder> /remove:d %USERNAME%` frees the folder.

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
- [ ] `SKILL.md` frontmatter is valid YAML (an unquoted `: ` in a value is not), read the same with and without PyYAML for the shapes a SKILL.md uses; the description is text (quote a value YAML would read as a number, a boolean or a date)
- [ ] All referenced files exist and can be read, every folder can be listed; bundled scripts compile
- [ ] `SKILL.md` and every text file the package ships are UTF-8, without a BOM (a `.ps1` may keep one; before the `#!` line of a script that is run by name — `.sh`, `.bash`, `.zsh`, `.py`, or no suffix — at the start of a `.sh`, `.bash` or `.zsh`, or in a `.json` it is an error)
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
