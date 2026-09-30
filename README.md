# Skillshaper

An agent skill for **creating, improving, validating, and packaging** agent skills with stricter quality and **mandatory dual output**.

**Voice:** Standards enforcer — quality and packaging, not creative writing.

The skill's id, and so its folder name, is `sc2`; Skillshaper is its name. Every install below lands this repository's `sc2/` folder under that name.

It follows the Agent Skills format (a folder with a `SKILL.md`), so any agent that reads that format and can run a Python script can use it, in any workflow: no host, skills folder or companion skill is assumed. The hosts named below are install examples, one of several.

## Install via skills.sh CLI

```bash
npx skills add SPRIC76/skillshaper
```

**Badge snippet:**

```markdown
[![skills.sh](https://skills.sh/b/SPRIC76/skillshaper)](https://skills.sh/SPRIC76/skillshaper)
```

## What Skillshaper adds

Skillshaper adds these to any skill-authoring workflow, or stands on its own:

| Requirement | Detail |
|-------------|--------|
| Validation | `sc2/scripts/validate_skill.py` — errors for the Agent Skills specification's rules (its length limits and required fields), a host's upload rules and a broken skill; warnings where a skill will trigger or age badly, or uses a form the specification does not give but hosts accept. In detail: the [Agent Skills specification](https://agentskills.io/specification)'s rules (frontmatter that is valid YAML, read by PyYAML when it is installed and otherwise by a built-in reader that takes a named subset and refuses the rest by name, see [Frontmatter without PyYAML](#frontmatter-without-pyyaml); allowed frontmatter keys, none that YAML types as a boolean, number or null, a kebab-case name equal to its folder, a description that is text, at most 1024 characters, `compatibility` at most 500 characters, a body under 500 lines (Skillshaper's own limit, stricter than the specification's recommendation); its shapes for `metadata` (a mapping of text to text), `license` and `allowed-tools` (text, `allowed-tools` one space-separated string) and a non-empty text `compatibility` are warnings, since some hosts accept the other forms (`--strict` treats each as an error)), the stricter rules some hosts apply on upload (no angle brackets in the description, one SKILL.md), plus stricter checks: a when-to-use cue in the description, every referenced file present (in SKILL.md and every other text file the package ships; a name with a space, or its `%20` form in a link, resolved) and none a dotfile the package leaves out, bundled Python that compiles (`.py` in any letter case), UTF-8 throughout with any BOM named in every text file the package ships, root-level ones included (an error where it breaks the file: before the `#!` line of a script that is run by name, at the start of a `.sh`, or in a `.json`; a non-UTF-8 file outside `references/`, `scripts/` and `assets/` is a warning), every bundled file readable and every folder listable, no orphan or junk files, no sandbox paths or hard-coded user folders |
| Dual packaging | Every skill ships as `{name}.skill` **and** `{name}-vX.Y.zip`, validated first; any error stops packaging |
| Local install | `--deploy <skills-home>` replaces an installed copy's contents in place, so links to that folder keep working; it touches only an absent or empty folder, or its own skill, and the skills home is always yours to name |
| Documentation | Progressive disclosure; references stay scannable |

## Install (any agent)

Copy the `sc2/` folder, keeping its name, into the folder your agent loads its skills from, or let the packager do it: `python sc2/scripts/package_dual.py sc2 --version 1.4 --output dist --deploy <skills-home>`. The scripts need Python 3.10 or later and only the standard library. Some examples of that folder, one of several:

| Agent | Skills folder (all projects, or one project) |
|-------|-----------------------------------------------|
| Any agent that reads the shared location | `~/.agents/skills/sc2/` or `.agents/skills/sc2/` |
| Claude Code | `~/.claude/skills/sc2/` or `.claude/skills/sc2/` |
| Cursor | `~/.cursor/skills/sc2/` or `.cursor/skills/sc2/` |
| Codex | `~/.agents/skills/sc2/` or `.agents/skills/sc2/` (the shared location) |

Any other runtime that loads folder-based skill instructions takes the same `sc2/` folder as a skill package. Where an IDE or agent has no skill system, run the validator and the packager from a terminal (see [Usage](#usage)).

### Install by upload

For a host that installs a skill from an archive (claude.ai and the Claude desktop app, for example), from the repository root:

1. Package the skill: `python sc2/scripts/package_dual.py sc2 --version 1.4 --output dist`
2. Upload `dist/sc2.skill` in the host's skill settings.
3. Confirm `sc2` (Skillshaper) appears in your skills.

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
| `dist/sc2.skill` | Upload to a host that installs skills from an archive (see [Install by upload](#install-by-upload)) |
| `dist/sc2-v1.4.zip` | Versioned archive for keeping and for manual installs |

Both are zip archives with `sc2/SKILL.md` as the root entry.

- **Left out:** `evals/` and `tests/` at the skill root, `*-workspace` folders, `__pycache__`, `node_modules`, `.git`, `.pytest_cache`, `.pyc` files, dotfiles such as `.gitignore` and `.env`, and OS junk (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX`).
- **Links:** a folder or file reached through a junction or symlink is packaged like any other; a link loop, or a link out to the archives, is not followed.
- **Line endings:** a file is written with LF whatever the checkout uses when all of it is UTF-8 text with no NUL byte and it is a text type (`.md`, `.txt`, `.py`, `.json`, `.yaml`, `.sh`, `.js`, `.html`, `.rst`, `.go` and the others listed in `TEXT_SUFFIXES`), a file with no suffix such as `LICENSE`, or a script that starts with `#!`; every other file stays byte-for-byte, a PDF, a calendar file or a script carrying a binary payload included.
- **Where the archives go:** outside the skill folder. Run from inside it, they land beside it (beside its real folder when the path given reaches the skill through a link that loops back into it), and a file linked in from beside it, or from beside the link the skill is reached through (the repository's `LICENSE`), is still packaged; an `--output` inside the skill or inside the deploy target, or one that is a file, is refused. Run from inside `sc2/` with no `--output`, the archives land in the repository root, which `.gitignore` covers (`sc2.skill`, `sc2-v*.zip`, `dist/`).
- **Whole or not at all:** each archive is built under a temporary name beside its target and the pair is moved into place only when both are complete.
- **One message per failure:** a file or folder that cannot be read, an archive that cannot be replaced (left read-only or held open, or a folder standing at its name), an `--output` that cannot be made or that takes no new file from this user (`C:\`, a folder an ACL denies), a skills home that takes no new folder from this user (or cannot be made, because the folder above it takes none, or because no folder above it exists at all, as on a drive or share that is not there), and a full disk each stop the run at once with one message naming the file and the reason; the earlier archives are untouched.
- **`--version`** takes digits, letters, dots and dashes, starting and ending with a digit or letter, at most 64 characters (`1.0`, `2.1-rc1`), so the `.zip` always lands in `--output` under a name every file system takes.
- **Dates:** the zip format holds dates from 1980 to 2107. A file dated before 1980 is stored dated 1980-01-01, one dated after 2107 is stored dated 2107-12-31, and each edge is named once for all its files; a file whose date Windows cannot express at all (before 1970, or past about the year 3000) is packaged the same way, never refused as unreadable.

`--deploy <skills-home>` (for example `--deploy ~/.agents/skills`, or any agent's skills folder) also installs the packaged skill into `<skills-home>/sc2/`, replacing that folder's contents in place — only when the folder is absent, empty, or an installed copy of the same skill. Anything else (another skill, a folder of other files, a file, a symlink or junction, the very folder being packaged, or a working copy, marked by `.git`, `.env`, `.envrc`, `.venv`, `.hg`, `.svn`, a `*-workspace` folder, or `tests/` or `evals/` at its root) is refused before anything is built, and nothing changes; so is a skills home that exists but takes no new folder from this user, or one with no folder above it at all. Anything else an older install holds that the package leaves out, such as a `.gitignore` earlier versions shipped, is replaced and named; OS junk and caches pass unmentioned. The replacement lands whole or the old copy is put back; read-only files and folders in the old copy are replaced too.

## Frontmatter without PyYAML

With PyYAML installed, the validator reads the frontmatter with PyYAML. Without it, the built-in reader reads this subset of YAML and refuses the rest by name:

- `key: value` lines, a key of letters, digits, `_` and `-` (or quoted without escapes), up to 128 characters; values plain, single- or double-quoted (YAML's own escapes), on one line or continued on lines indented past the key, typed as PyYAML types them (null, booleans such as `yes`, numbers, dates);
- `>` and `|` blocks with their chomping (`-`, `+`) and indent (`>2`) indicators, and a comment after the header, the header on the key's line;
- flow lists of such values, `[a, b]`, also closed on a later line, and flow mappings of `key: value` pairs, `{a: 1}`;
- block lists of `- items`, one line each, at the key's indent or indented;
- one level of nested mapping holding those values, and a mapping indented as a whole;
- comments, empty values and null forms;
- no tab anywhere, not even inside quotes, a block or a comment, and no line break other than LF or CRLF, no BOM inside the frontmatter.

Anything else (a key such as `x.y:`, `allowed tools:` or `~:`, a tab, an anchor, alias or tag, a collection inside a list or a flow collection, a list of mappings, a list item over more than one line, a mapping nested deeper, a flow key without a value such as `{a}`, a quote continued at column 0 (on a line not indented past its key), a block header on the line below its key, a complex `? ` key, a date with a time, a comment inside `[ ]`, frontmatter over 100,000 characters) is refused by name with the way to write it, or read after `pip install pyyaml`. For any input the built-in reader returns exactly what PyYAML 6 returns, or refuses; it never guesses, and neither script stops on a traceback (a number too long to print, past Python's 4,300 digits, is shown by its size).

## Tests

From the repository root:

```bash
python -B -m unittest discover -s tests -v
```

Standard library only; every fixture is built in a temporary folder. The tests live in `tests/` beside `sc2/`, not inside it, so packaged and deployed copies stay identical to the development copy. The frontmatter parity tests run the same table of shapes through the built-in reader and, where PyYAML is installed, through PyYAML; each shape's verdict was recorded from PyYAML 6.0.3, so the parity is checked without PyYAML too. A seeded differential test builds several thousand frontmatters from a grammar of fragments and mutations (the same list on every run) and, with PyYAML installed, holds the built-in reader to its promise on each: PyYAML's value and type, or a refusal by name; without PyYAML it checks that none crashes or hangs. On Windows, several tests set an ACL deny on a temporary folder with `icacls` and lift it afterwards; if a run is killed inside one, `icacls <folder> /remove:d %USERNAME%` frees the folder.

## Pre-package checklist

The validator checks each of these; `--strict` treats warnings as errors.

- [ ] `SKILL.md` frontmatter: `name` (kebab-case, equal to the folder) + `description` (what it does and when to use it)
- [ ] Body under 500 lines; depth in `references/`
- [ ] `SKILL.md` frontmatter is valid YAML (an unquoted `: ` in a value is not), and, without PyYAML, inside the built-in reader's subset; the description is text (quote a value YAML would read as a number, a boolean or a date)
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
