---
name: sc2
description: >
  Skillshaper (id sc2, formerly Skill Creator 2): the packaging and quality
  standard for Agent Skills, for any agent that reads a SKILL.md and alongside
  any skill-authoring workflow. Use when asked for Skillshaper or sc2, and
  whenever a skill is created, edited, recalibrated, validated, packaged,
  uploaded to a host, or deployed to a local skills folder - including "shape
  this skill", "package this skill", "make a .skill file", "check my skill",
  "why isn't my skill triggering", "upgrade my skills", or before handing any
  skill to someone. Validates against the upload rules plus stricter checks
  (name equals folder, triggers in the description, every referenced file
  exists, no stale sandbox paths), then always produces both a .skill and a
  versioned .zip.
metadata:
  version: "1.4"
  updated: "2026-09-30"
---

# Skillshaper (sc2) — Packaging & Quality Standards

This skill is plain files: this SKILL.md and two Python 3 scripts that need only the standard library. Any agent that reads the Agent Skills format (a folder with a SKILL.md) and can run a script can use it, in any workflow and on any host. It works on its own, or on top of any skill-authoring workflow (capture intent, draft, test prompts, evals, description tuning): use that workflow for the writing and apply these standards on top.

## 1. Validate before anything ships

```bash
python scripts/validate_skill.py <skill-folder> [--strict]
```

| Level | Means |
|-------|-------|
| **Error** | Upload would be rejected, or the skill is broken; packaging stops. |
| **Warning** | The skill will trigger badly or age badly; `--strict` treats each as an error. |

**Errors:**

- Frontmatter that is not valid YAML: an unquoted `: ` in a value, a tab after the key or inside a plain value, no space after the colon, an unclosed `[`, `{` or quote, text after a closing quote or bracket, an unknown escape such as `\q` in double quotes, a plain value that opens with a character YAML reserves (`` ` ``, `@`, `%`, `- `, `,`, `]`, `}`). With PyYAML installed, PyYAML reads the frontmatter. Without it, the built-in reader reads this subset of YAML and refuses the rest by name:
  - `key: value` lines, a key of letters, digits, `_` and `-` (or quoted without escapes), up to 128 characters; values plain, single- or double-quoted (`''` and `\"` are YAML's own escapes), on one line or continued on lines indented past the key, typed as PyYAML types them (null `~`; boolean `yes`, `Yes`, `YES`, while `yEs` is text; numbers; dates);
  - `>` and `|` blocks with their chomping (`-`, `+`) and indent (`>2`) indicators, and a comment after the header, the header on the key's line;
  - flow lists of such values, `[a, b]`, also closed on a later line, and flow mappings of `key: value` pairs, `{a: 1}`;
  - block lists of `- items`, one line each, at the key's indent or indented;
  - one level of nested mapping holding those values, and a mapping indented as a whole;
  - comments, empty values and null forms;
  - no tab anywhere, not even inside quotes, a block or a comment, and no line break other than LF or CRLF, no BOM inside the frontmatter.

  Anything else (a key such as `x.y:`, `allowed tools:` or `~:`, a tab, an anchor, alias or tag, a collection inside a list or a flow collection, a list of mappings, a list item over more than one line, a mapping nested deeper, a flow key without a value such as `{a}`, a quote continued at column 0 (on a line not indented past its key), a block header on the line below its key, a complex `? ` key, a date with a time, a comment inside `[ ]`, frontmatter over 100,000 characters) is refused by name with the way to write it, or read after `pip install pyyaml`. For any input the built-in reader returns exactly what PyYAML 6 returns, or refuses; it never guesses, and neither script stops on a traceback (a number too long to print, past Python's 4,300 digits, is shown by its size).
- frontmatter keys other than `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`
- `name` missing or null, not kebab-case, over 64 characters, or different from its folder
- a key YAML reads as a boolean, number or null (an unquoted `on:`, `yes:` or `1:`, and `~:` where PyYAML reads it), named as YAML types it
- `description` missing or null; not text (an unquoted `1.4`, `yes` or `2026-09-30`, which YAML reads as a number, a boolean or a date: quote it; a list or mapping, named so); over 1024 characters; or containing angle brackets
- body over 500 lines
- a referenced `references/`, `scripts/` or `assets/` path, bare or `./`-prefixed, that does not exist — checked in SKILL.md and in every other text file the package ships, a changelog at the root included (a name holding a space, or its `%20` form in a link, is resolved; test files — `*_selftest.py`, `test_*.py`, `*_test.py`, anything under a `tests/` folder — are exempt, since they name throwaway fixtures)
- a referenced dotfile, which the package leaves out
- a bundled Python script, `.py` in any letter case, that does not compile (a byte-order mark at its start is only a warning, since Python runs it)
- a SKILL.md or bundled text file that is not UTF-8
- a bundled file that cannot be read, or a folder that cannot be listed (held open by another program, or no permission)
- a UTF-8 BOM where it breaks the file: before the `#!` line of a script that is run by name (`.sh`, `.bash`, `.zsh`, `.py`, or no suffix), at the start of a `.sh`, `.bash` or `.zsh`, which a shell reads as part of the first command, or in a `.json`, which JSON forbids and `json.loads` rejects
- more than one SKILL.md

**Warnings:**

- no "when to use" cue in the description
- trigger phrases kept in the body
- files nothing points to (orphans)
- references over 300 lines without a contents list
- junk files (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `__pycache__`, `.pytest_cache`, `.pyc`)
- a UTF-8 BOM in SKILL.md or any other text file the package ships, root-level ones included (a `.ps1` excepted: Windows PowerShell reads a UTF-8 script by its BOM; a `.md` or `.ps1` whose first line is `#!` is not run by it)
- a text file outside `references/`, `scripts/` and `assets/` (`LICENSE`, `README.md`) that is not UTF-8
- in SKILL.md and every other text file the package ships: sandbox paths from one hosted surface (a `/mnt/…` path), paths from a former user account (any letter case), tool names only one surface has

**Why the description carries the most weight:** it is the only text a model sees when deciding whether to load a skill. Trigger phrases written in the body are invisible at that moment. Put every "when to use" in the description, and make it a little pushy — models tend to load a skill too rarely rather than too often.

## 2. Package: always both formats

```bash
python scripts/package_dual.py <skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>] [--strict]
```

| File | For | Name |
|------|-----|------|
| `.skill` | A host that installs a skill from an uploaded archive: upload it in its skill settings, or open the file card an agent presents | `{name}.skill` — no version, always current |
| `.zip` | Keeping, and local agents: extract it into the folder the agent loads its skills from, so it lands as `<skills-home>/{name}/` | `{name}-v{X.Y}.zip` |

Both are zip archives with `{name}/SKILL.md` at the root. The packager validates first and stops on any error.

- **Left out:** `evals/` and `tests/` at the skill root, `*-workspace` folders, `__pycache__`, `node_modules`, `.git`, `.pytest_cache`, `.pyc` files, dotfiles such as `.gitignore` and `.env`, and OS junk (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX`).
- **Links:** a folder or file reached through a link (a junction or a symlink) is packaged like any other; a link back to a folder already on the way (a loop) or out to the archives is not followed.
- **Line endings:** a file is written with LF whatever the checkout uses when all of it is UTF-8 text with no NUL byte and it is a text type (`.md`, `.txt`, `.py`, `.json`, `.yaml`, `.sh`, `.js`, `.html`, `.rst`, `.go` and the others listed in `TEXT_SUFFIXES`), a file with no suffix such as `LICENSE` or `Makefile`, or a script that starts with `#!`; every other file stays byte-for-byte, a PDF, a calendar file or a script carrying a binary payload included. A file that starts with `#!` is stored executable.
- **Where the archives go:** outside the skill folder. Run from inside it, they go beside it (beside its real folder when the path given reaches the skill through a link that loops back into it), and a file linked in from beside it, or from beside the link the skill is reached through (a repository's `LICENSE`), is still packaged, since only the archives themselves are kept out. An `--output` inside the skill or inside the deploy target, or one that is a file, is refused, so an archive never packs itself or lands where the deploy replaces it. Run from inside `sc2/` with no `--output`, this skill's own archives land in its repository root, which `.gitignore` covers (`sc2.skill`, `sc2-v*.zip`, `dist/`).
- **Whole or not at all:** each archive is built under a temporary name beside its target, and the pair is moved into place only when both are complete, the earlier pair put back if either move fails.
- **One message per failure:** a file or folder that cannot be read, an archive that cannot be replaced (an earlier one left read-only or held open, or a folder standing at its name), an `--output` that cannot be made or that takes no new file from this user, a skills home that takes no new folder from this user (or cannot be made, because the folder above it takes none, or because no folder above it exists at all, as on a drive or share that is not there), and a full disk each stop the run at once with one message naming the file and the reason, and the earlier archives are untouched.
- **`--version`** takes digits, letters, dots and dashes, starting and ending with a digit or letter, at most 64 characters (`1.0`, `2.1-rc1`), so the `.zip` always lands in `--output` under a name every file system takes.
- **Dates:** the zip format holds dates from 1980 to 2107. A file dated before 1980 is stored dated 1980-01-01, one dated after 2107 is stored dated 2107-12-31, and each edge is named once for all its files. A file whose date Windows cannot express at all (before 1970, or past about the year 3000) is packaged the same way, never refused as unreadable.

`--deploy <skills-home>` also replaces the contents of `<skills-home>/{name}/` with exactly what was packaged — only when that folder is absent, empty, or an installed copy of this same skill. The skills home is always an argument, never assumed: the folder your agent loads its skills from. Anything else (another skill, a folder of other files, a file, a symlink or junction, the very folder being packaged, or a working copy, marked by `.git`, `.env`, `.envrc`, `.venv`, `.hg`, `.svn`, a `*-workspace` folder, or `tests/` or `evals/` at its root) is refused before anything is built, and nothing changes; so is a skills home that exists but takes no new folder from this user (`C:\Program Files`, a folder an ACL denies), or one with no folder above it at all. Anything else an older install holds that the package leaves out (a `.gitignore` that packagers before 1.4 shipped) is replaced and named; OS junk and caches pass unmentioned, and a folder holding only those counts as empty. The replacement lands whole or the old copy is put back; a read-only file or folder in the old copy is no obstacle, and an old copy an earlier deploy could not remove (still in use) is left where it is and named. The folder itself stays, so junctions or symlinks agents use to reach it keep working; a link inside it is removed as a link, never followed.

**Present both files** when the agent has a tool that hands files to the user. Without one, say where both files are.

### Install examples

Where a skill goes depends on the host, so these are examples, one of several each; the README lists more:

- a skills folder the agent loads at start: `--deploy ~/.agents/skills`, `--deploy ~/.claude/skills`, or `--deploy ~/.cursor/skills` for every project, or a project's own `.agents/skills`;
- a host that installs by upload (claude.ai, for one): upload the `.skill`;
- anything else: extract the `.zip` wherever that agent reads its skills.

## 3. Documentation completeness

Every skill has:

1. **SKILL.md** — what it does and when (in the description), workflow, anti-patterns
2. **references/** (when SKILL.md needs depth) — supporting docs SKILL.md points to, each saying when to read it
   - Justifies its existence (does not repeat SKILL.md)
   - Scannable: tables over prose, imperative form
   - Version and date in its header
3. **scripts/** (if any) — executable (a shebang, and the executable bit set in git), with a docstring saying what it does, what it returns, and what it will never do

**User-friendly standard:** someone reading only SKILL.md understands what the skill does, when it triggers, and how to use it. References add depth, never prerequisites.

**Portable standard:** a skill meant for others names no host outside its install examples, assumes no skills folder (take it as an argument), carries no one's user data, and names no other skill: say what job it does ("a verification tool").

## 4. Version tracking

- `metadata.version` and `metadata.updated` in the frontmatter, and the version in the `.zip` name
- Former names and versions in a closing footnote when renamed or recalibrated

## 5. Updating an existing skill

- **Keep the name and folder** — agents and accounts know the skill by them.
- **Snapshot before editing.** The snapshot is the baseline every change is measured against.
- **Scripts get tests, and the test fails first.** Keep tests outside the skill folder (this repository keeps them in `tests/` beside `sc2/`) so packaged and deployed copies stay identical to the development copy.
- **Name every older copy.** A skill often lives in several places at once: the development folder, a local skills home, one or more hosted accounts, a public repository, project folders. After packaging, list each place still holding the old version and who can refresh it. An uploaded copy changes only when someone uploads the new `.skill`.

## With a skill-authoring workflow

Where the workflow packages a single archive, package both formats instead, and run the validator wherever it validates. Every other step — interview, research, writing, test cases, evals, description tuning, blind comparison — is unchanged.

---

*⁰ Formerly: skill-creator-plus → skill-creator-2 → sc2 v1.0 (2026-02-10) → sc2 v1.1 (2026-09-15: validator, deploy, every surface named instead of one sandbox) → Skill-Shaper, sc2 v1.2 (2026-09-28: the name its maker gave it; the id and folder stay sc2, per section 5) → Skillshaper, sc2 v1.3 (2026-09-30: one word, as its author writes it) → sc2 v1.4 (2026-09-30: its own `sc2/` folder so every skill directory finds it; deploy that refuses anything but its own skill; LF archives without dotfiles; test files exempt from the missing-reference check; written for any agent that reads SKILL.md, with no host assumed; the rest of ten independent reviews, each fix behind a test in `tests/`).*
