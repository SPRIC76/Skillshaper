---
name: sc2
description: >
  Skillshaper (id sc2, formerly Skill Creator 2): the packaging and quality
  standard for Agent Skills, layered on Anthropic's skill-creator. Use when
  asked for Skillshaper or sc2, and whenever a skill is created, edited,
  recalibrated, validated, packaged, uploaded to claude.ai, or deployed to a
  local skills folder such as ~/.agents/skills - including "shape this skill",
  "package this skill", "make a .skill file", "check my skill", "why isn't my
  skill triggering", "upgrade my skills", or before handing any skill to someone.
  Validates against the upload rules plus stricter checks (name equals folder,
  triggers in the description, every referenced file exists, no stale sandbox
  paths), then always produces both a .skill and a versioned .zip.
metadata:
  version: "1.4"
  updated: "2026-09-30"
---

# Skillshaper (sc2) — Packaging & Quality Standards

This skill supplements Anthropic's `skill-creator` wherever it is installed (claude.ai, the Claude desktop app, a Claude Code plugin, or the `anthropics/skills` repository). Use skill-creator for the workflow — capture intent, draft, test prompts, evals, description optimization — and apply these standards on top. Without skill-creator, the standards below still stand on their own.

## 1. Validate before anything ships

```bash
python scripts/validate_skill.py <skill-folder> [--strict]
```

| Level | Means | Checks |
|-------|-------|--------|
| **Error** | Upload would be rejected, or the skill is broken | Frontmatter that is not valid YAML (an unquoted `: ` in a value, a tab after the key, an unclosed `[`, `{` or quote; read the same with and without PyYAML) · frontmatter keys other than name, description, license, allowed-tools, metadata, compatibility · name not kebab-case, over 64 characters, or different from its folder · description missing, over 1024 characters, or containing angle brackets · body over 500 lines · a referenced `references/`, `scripts/` or `assets/` path, bare or `./`-prefixed, that does not exist (a name holding a space, or its `%20` form in a link, is resolved; test files — `*_selftest.py`, `test_*.py`, `*_test.py`, anything under a `tests/` folder — are exempt, since they name throwaway fixtures) · a referenced dotfile, which the package leaves out · a bundled Python script, `.py` in any letter case, that does not compile (a byte-order mark at its start is only a warning, since Python runs it) · a SKILL.md or bundled text file that is not UTF-8 · a bundled file that cannot be read, or a folder that cannot be listed (held open by another program, or no permission) · a UTF-8 BOM where it breaks the file: before the `#!` line of a script that is run by name (`.sh`, `.bash`, `.zsh`, `.py`, or no suffix), at the start of a `.sh`, which a shell reads as part of the first command, or in a `.json`, which JSON forbids and `json.loads` rejects · more than one SKILL.md |
| **Warning** | The skill will trigger badly or age badly | No "when to use" cue in the description · trigger phrases kept in the body · files nothing points to · references over 300 lines without a contents list · junk files · a UTF-8 BOM in SKILL.md or any other text file the package ships, root-level ones included (a `.ps1` excepted: Windows PowerShell reads a UTF-8 script by its BOM; a `.md` or `.ps1` whose first line is `#!` is not run by it) · a text file outside `references/`, `scripts/` and `assets/` (`LICENSE`, `README.md`) that is not UTF-8 · sandbox paths from one surface, paths from a former user account (any letter case), tool names only one surface has |

**Why the description carries the most weight:** it is the only text a model sees when deciding whether to load a skill. Trigger phrases written in the body are invisible at that moment. Put every "when to use" in the description, and make it a little pushy, as skill-creator advises — models tend to under-trigger skills.

## 2. Package: always both formats

```bash
python scripts/package_dual.py <skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>]
```

| File | For | Name |
|------|-----|------|
| `.skill` | claude.ai and the Claude desktop app: upload in skill settings, or open the file card an agent presents | `{name}.skill` — no version, always current |
| `.zip` | Keeping, and local agents: extract so the folder lands at `~/.agents/skills/{name}/` | `{name}-v{X.Y}.zip` |

Both are zip archives with `{name}/SKILL.md` at the root. The packager validates first and stops on any error. It leaves out `evals/` and `tests/` at the skill root, `*-workspace` folders, `__pycache__`, `node_modules`, `.git`, `.pyc`, dotfiles such as `.gitignore` and `.env`, and OS junk (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX`). A folder or file reached through a link (a junction or a symlink) is packaged like any other; a link back to a folder already on the way (a loop) or out to the archives is not followed. A file is written with LF line endings whatever the checkout uses when all of it is UTF-8 text with no NUL byte and it is a text type (`.md`, `.txt`, `.py`, `.json`, `.yaml`, `.sh`, `.js`, `.html`, `.rst`, `.go` and the others listed in `TEXT_SUFFIXES`), a file with no suffix such as `LICENSE` or `Makefile`, or a script that starts with `#!`; every other file stays byte-for-byte, a PDF, a calendar file or a script carrying a binary payload included; a file that starts with `#!` is stored executable. The archives are written outside the skill folder: run from inside it, they go beside it (beside its real folder when the path given reaches the skill through a link that loops back into it), and a file linked in from beside it, or from beside the link the skill is reached through (a repository's `LICENSE`), is still packaged, since only the archives themselves are kept out; an `--output` inside the skill or inside the deploy target, or one that is a file, is refused, so an archive never packs itself or lands where the deploy replaces it. Both archives land together or not at all: each is built under a temporary name beside its target, and the pair is moved into place only when both are complete, the earlier pair put back if either move fails. A file or folder that cannot be read, an archive that cannot be replaced (an earlier one left read-only or held open, or a folder standing at its name), an `--output` that cannot be made or that takes no new file from this user, and a full disk each stop the run at once with one message naming the file and the reason, and the earlier archives are untouched. `--version` takes digits, letters, dots and dashes (`1.0`, `2.1-rc1`), so the `.zip` always lands in `--output`. A file dated before 1980, which the zip format cannot hold, is stored dated 1980-01-01 and named.

`--deploy <skills-home>` also replaces the contents of `<skills-home>/{name}/` with exactly what was packaged — only when that folder is absent, empty, or an installed copy of this same skill. Anything else (another skill, a folder of other files, a file, a symlink or junction, the very folder being packaged, or a working copy, marked by `.git`, `.env`, `.envrc`, `.venv`, `.hg`, `.svn`, a `*-workspace` folder, or `tests/` or `evals/` at its root) is refused before anything is built, and nothing changes. Anything else an older install holds that the package leaves out (a `.gitignore` that packagers before 1.4 shipped) is replaced and named; OS junk and caches pass unmentioned, and a folder holding only those counts as empty. The replacement lands whole or the old copy is put back; a read-only file or folder in the old copy is no obstacle, and an old copy an earlier deploy could not remove (still in use) is left where it is and named. The folder itself stays, so junctions or symlinks agents use to reach it keep working; a link inside it is removed as a link, never followed.

**Present both files** when a file-delivery tool exists (`present_files`, `SendUserFile`). Without one, say where both files are.

## 3. Documentation completeness

Every skill has:

1. **SKILL.md** — what it does and when (in the description), workflow, anti-patterns
2. **references/** (when SKILL.md needs depth) — supporting docs SKILL.md points to, each saying when to read it
   - Justifies its existence (does not repeat SKILL.md)
   - Scannable: tables over prose, imperative form
   - Version and date in its header
3. **scripts/** (if any) — executable (a shebang, and the executable bit set in git), with a docstring saying what it does, what it returns, and what it will never do

**User-friendly standard:** someone reading only SKILL.md understands what the skill does, when it triggers, and how to use it. References add depth, never prerequisites.

## 4. Version tracking

- `metadata.version` and `metadata.updated` in the frontmatter, and the version in the `.zip` name
- Former names and versions in a closing footnote when renamed or recalibrated

## 5. Updating an existing skill

- **Keep the name and folder** — agents and accounts know the skill by them.
- **Snapshot before editing.** The snapshot is the baseline every change is measured against.
- **Scripts get tests, and the test fails first.** Keep tests outside the skill folder (this repository keeps them in `tests/` beside `sc2/`) so packaged and deployed copies stay identical to the development copy.
- **Name every older copy.** A skill often lives in several places at once: the development folder, a local skills home, one or more claude.ai accounts, a public repository, project folders. After packaging, list each place still holding the old version and who can refresh it. claude.ai copies change only when someone uploads the new `.skill`.

## Integration with skill-creator

Replace skill-creator's single `.skill` in **Package and Present** with dual packaging, and run the validator wherever skill-creator validates. Every other step — interview, research, writing guide, test cases, evals, description optimization, blind comparison — is unchanged.

---

*⁰ Formerly: skill-creator-plus → skill-creator-2 → sc2 v1.0 (2026-02-10) → sc2 v1.1 (2026-09-15: validator, deploy, every surface named instead of one sandbox) → Skill-Shaper, sc2 v1.2 (2026-09-28: the name its maker gave it; the id and folder stay sc2, per section 5) → Skillshaper, sc2 v1.3 (2026-09-30: one word, as its author writes it) → sc2 v1.4 (2026-09-30: its own `sc2/` folder so every skill directory finds it; deploy that refuses anything but its own skill; LF archives without dotfiles; test files exempt from the missing-reference check; the rest of three independent reviews, each fix behind a test in `tests/`).*
