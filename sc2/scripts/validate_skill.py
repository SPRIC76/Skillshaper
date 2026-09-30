#!/usr/bin/env python3
"""
Skill validator — the base skill-creator's upload rules plus Skillshaper's (sc2) standards.
validate_skill.py v1.0 | 2026-09-15
Updated: 2026-09-30 04:02 ET — v1.1: '.' validates under its own folder name; ./-prefixed paths are
checked; a file that is not UTF-8 is an ERROR line and a BOM a warning; test files are
exempt from the missing-reference check; unknown flags are a usage error; the user-folder
check ignores letter case.
Updated: 2026-09-30 04:44 ET — v1.2: "Triggers on ..." counts as a when-to-use cue; only an exact copy of
this validator skips the marker and user-folder checks, not any file of its name; paths in
messages use forward slashes; a dotfile the packager drops is not an orphan.
Updated: 2026-09-30 05:25 ET — v1.3: the skill is walked as the packager reads it (links followed alike,
a loop cut, dot-folders such as a deploy's .old-* not entered); any version of this
validator, edited or not, is exempt by its first docstring line; c:/users/... is no
one's user folder.
Updated: 2026-09-30 06:03 ET — v1.4: every released version is exempt by its first docstring line (1.1
named sc2's standards; a copy may open the docstring on the quotes' line); the walk leaves
*-workspace folders and __MACOSX unentered and, given the packager's output folder, cuts a
link into it as the packager does; a dotfile is not read, since it never ships;
desktop.ini is junk; a script that starts with #! and carries a binary payload is not
held to UTF-8.
Updated: 2026-09-30 06:34 ET — v1.5: a dotfile the skill names is an error, since the package leaves it
out; a bundled script's BOM is a warning, not a compile error (Python runs it); a NUL
byte in a script is an ERROR line on Python 3.10 too; junk is named once, not also as an
orphan; beside also means beside the link a skill is reached through.
Updated: 2026-09-30 12:36 ET — v1.6: a bundled file that cannot be read (held open, no permission) is an ERROR
line naming it and the reason, not a traceback; a UTF-8 BOM is named in every bundled text
file, an error where it breaks the file (before a #! line, or in a .json) and left alone in
a .ps1, which Windows PowerShell reads by its BOM.

Errors are what claude.ai or the Skills API would reject, or what leaves the
skill broken: frontmatter keys and limits, a name that differs from its folder,
angle brackets in the description, a body over 500 lines, a referenced file that
does not exist or is a dotfile the package leaves out (bare or ./-prefixed; test files - *_selftest.py, test_*.py,
*_test.py, anything under tests/ - name throwaway fixtures and are exempt),
a bundled Python script that does not compile, a file that is not UTF-8 (a script
that starts with #! and holds a NUL byte carries a binary payload, is stored
byte-for-byte, and is exempt), a bundled file that cannot be read (held open by
another program, or no permission), and a UTF-8 BOM where it breaks the file: before
a #! line, which no system then honours, or in a .json, which JSON forbids and
json.loads rejects.

Warnings are what makes a skill trigger badly or age badly: no "when to use" cue
in the description (the description is all a model sees when it picks a skill),
trigger phrases kept in the body instead, files nothing points to, long
references without a contents list, a UTF-8 BOM in SKILL.md or any other bundled
text file (a .ps1 excepted: Windows PowerShell reads a UTF-8 script by its BOM),
and paths from sandboxes that no longer exist (/mnt/skills, /home/claude), one
person's user folder in any letter case, or tool names only one surface has.

Usage:
    python validate_skill.py <skill-folder> [<skill-folder> ...] [--strict]

Exit 0 when no errors (and, with --strict, no warnings); 1 otherwise; 2 for an
unknown option. Needs only the standard library; uses PyYAML for the frontmatter
when present.
"""

import fnmatch
import os
import re
import sys
from pathlib import Path

ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
JUNK_DIRS = {"__pycache__", "node_modules", ".pytest_cache", "__MACOSX"}
JUNK_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
ROOT_SKIP_DIRS = {"evals", "tests"}
BUNDLE_DIRS = ("references", "scripts", "assets")
# A bundled path, written bare or with a ./ prefix; ../ and foo/scripts/ stay out.
REF_PATTERN = re.compile(r"(?<![\w/.-])(?:\./)?((?:references|scripts|assets)/[\w.\-/]*[\w])")
WHEN_CUE = re.compile(r"\b(use (this skill )?(when|whenever|for|to)|trigger(s|ed)?|apply when|invoke when)\b", re.I)
STALE_MARKERS = {
    "/mnt/skills": "a claude.ai sandbox path that other surfaces do not have",
    "/mnt/user-data": "a claude.ai sandbox path that other surfaces do not have",
    "/home/claude": "a claude.ai sandbox path that other surfaces do not have",
    "str_replace": "a tool name only some surfaces use; say 'edit in place'",
}
# One person's profile folder: breaks on every other machine and discloses the
# account name wherever the skill is shared. Placeholders such as <you> pass.
# Case-insensitive: Windows paths are, and shells often print c:/users/<name>.
# A name starts with a letter or digit, so an elided c:/users/... is no one's.
USER_PATH = re.compile(r"(?:[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}|/Users/|/home/)"
                       r"(?!(?:claude|Public|Default|All Users)\b)([A-Za-z0-9][A-Za-z0-9._-]*)", re.I)


def _parse_frontmatter(text):
    """Return (dict, body_text) or raise ValueError."""
    if not text.startswith("---"):
        raise ValueError("No YAML frontmatter found")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("Invalid frontmatter format")
    raw, body = m.group(1), m.group(2)
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError("Frontmatter must be a YAML mapping")
        return data, body
    except ImportError:
        return _mini_yaml(raw), body


def _mini_yaml(raw):
    """Enough YAML for skill frontmatter: scalars, > and | blocks, one nested map."""
    data, lines, i = {}, raw.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            raise ValueError(f"Unparseable frontmatter line: {line!r}")
        key, val = m.group(1), m.group(2).strip()
        i += 1
        if val in (">", ">-", "|", "|-", ""):
            block = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i])
                i += 1
            if val == "" and block and all(re.match(r"^\s+[A-Za-z0-9_-]+:", b) or not b.strip() for b in block):
                data[key] = {bm.group(1): bm.group(2).strip().strip("'\"")
                             for b in block if (bm := re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", b))}
            elif val.startswith("|"):
                data[key] = "\n".join(b.strip() for b in block).strip()
            else:
                data[key] = " ".join(b.strip() for b in block if b.strip())
        else:
            data[key] = val.strip("'\"")
    return data


def _carries_payload(path):
    """A script that starts with #! and holds a NUL byte carries a binary payload after its text
    (a self-extracting archive: tar and gzip bytes always hold a NUL), which the packager stores
    byte-for-byte; it is not held to UTF-8. Python must be UTF-8 to run, so .py never is."""
    if not path.is_file() or path.suffix.lower() == ".py":
        return False
    data = path.read_bytes()
    return data.startswith(b"#!") and b"\0" in data


def _unreadable(rel, e):
    """The ERROR line for a file the operating system would not let this run read."""
    return (f"{rel} could not be read ({e.strerror or e}); close the program holding it open, or check "
            "its permissions, and run again")


def _read_utf8(path, rel, errors):
    """Text of path, or None after an ERROR line naming the file and the bad byte, or why it
    could not be read (held open with no share mode, no permission)."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(f"{rel} is not UTF-8 ({e.reason} at byte {e.start}); save it as UTF-8")
    except OSError as e:
        errors.append(_unreadable(rel, e))
    return None


# Every released version opens its docstring with this line; only the owner's name in it has changed
# (1.1: "plus sc2's standards."), and a copy may start the docstring on the opening quotes' line.
_SIGNATURE = re.compile(r"^(?:\"\"\"|''')?\s*Skill validator — the base skill-creator's upload rules plus "
                        r".{1,40} standards\.$")


def _is_this_validator(path):
    """This file names the markers it hunts; a copy of it, of any released version or edited, opens
    with the signature line and is exempt; another skill's file of the same name does not and is checked."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = [f.readline().strip() for _ in range(4)]
    except OSError:
        return False
    return any(_SIGNATURE.match(line) for line in head)


def _inside(path, folder):
    """Is path the folder itself or somewhere inside it, links followed on both sides?"""
    p, f = (os.path.normcase(os.path.realpath(x)) for x in (path, folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def archive_cut(real, root, out, name, is_dir, skill=None):
    """Must a walk of the skill at root not take this link, because it reaches the archives
    package_dual.py writes to out? The output folder and any folder above it are cut; when out
    is a folder of its own, anything in it; when the archives go beside the skill, only the
    archives themselves ({name}.skill, {name}-v*.zip): a LICENSE linked from the repository
    root stays. Beside means out holds the skill's real folder, or the folder that holds
    skill, the path as given (a link to the skill keeps its archives beside the link).
    Shared by the packager and this validator, so both read the same skill."""
    if out is None or _inside(real, root):
        return False
    if _inside(out, real):
        return True
    beside = _inside(root, out) or (skill is not None and _inside(os.path.dirname(os.path.abspath(skill)), out))
    if not beside:
        return _inside(real, out)
    if is_dir or os.path.normcase(os.path.dirname(real)) != os.path.normcase(os.path.realpath(out)):
        return False
    base = os.path.basename(real)
    return os.path.normcase(base) == os.path.normcase(name + ".skill") or fnmatch.fnmatch(base, name + "-v*.zip")


def _tree(skill, out=None):
    """Every path under the skill as the packager reads it: links of every kind followed
    alike, a link back to a folder already on the way down (a loop) or out to the archives
    (archive_cut, when the packager names its output folder) cut, and folders that never
    ship (__pycache__ and the like, dot-folders such as .git or the .old-* a locked deploy
    leaves, *-workspace folders, evals/ and tests/ at the root) listed but not entered."""
    root = os.path.realpath(skill)
    found = []

    def walk(folder, chain, top):
        for child in sorted(folder.iterdir()):
            real = os.path.realpath(child)
            is_dir = child.is_dir()
            if archive_cut(real, root, out, skill.name, is_dir, skill):
                continue
            found.append(child)
            if is_dir:
                key = os.path.normcase(real)
                if key in chain or child.name in JUNK_DIRS or child.name.startswith(".") \
                        or child.name.endswith("-workspace") or (top and child.name in ROOT_SKIP_DIRS):
                    continue
                walk(child, chain | {key}, False)

    walk(skill, frozenset({os.path.normcase(root)}), True)
    return found


def _is_test_file(rel):
    """Test code names fixtures that need not exist, so it skips the missing-reference check."""
    return "tests" in rel.parts[:-1] or any(fnmatch.fnmatchcase(rel.name, pat)
                                            for pat in ("*_selftest.py", "test_*.py", "*_test.py"))


def check(skill_dir, out=None):
    """Return (errors, warnings) for one skill folder; out, when package_dual.py passes its
    output folder, cuts a link out to the archives as the packager does."""
    # abspath, not resolve(): '.' and '..' become the folder's own name, and a
    # junction or symlink an agent reaches the skill through keeps its name.
    skill = Path(os.path.abspath(skill_dir))
    errors, warnings = [], []
    md = skill / "SKILL.md"
    if not md.is_file():
        return [f"{skill}: SKILL.md not found"], []

    tree = _tree(skill, out)
    nested =[p for p in tree if p.name == "SKILL.md" and p != md and p.is_file()]
    if nested:
        errors.append("more than one SKILL.md (claude.ai accepts exactly one): "
                      + ", ".join(p.relative_to(skill).as_posix() for p in nested))

    text = _read_utf8(md, "SKILL.md", errors)
    if text is None:
        return errors, warnings
    if text.startswith("\ufeff"):
        text = text[1:]
        warnings.append("SKILL.md starts with a UTF-8 byte-order mark (BOM); save it as plain UTF-8, "
                        "which every surface reads")
    try:
        fm, body = _parse_frontmatter(text)
    except ValueError as e:
        return errors + [str(e)], warnings

    extra = set(fm) - ALLOWED_KEYS
    if extra:
        errors.append(f"frontmatter keys not allowed: {', '.join(sorted(extra))}")

    name = str(fm.get("name", "")).strip()
    if not name:
        errors.append("frontmatter has no name")
    else:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
            errors.append(f"name '{name}' must be kebab-case, at most 64 characters")
        if name != skill.name:
            errors.append(f"name '{name}' differs from its folder '{skill.name}'; agents load by name")

    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("frontmatter has no description")
        desc = ""
    desc = desc.strip()
    if "<" in desc or ">" in desc:
        errors.append("description contains angle brackets (< or >), which upload rejects")
    if len(desc) > 1024:
        errors.append(f"description is {len(desc)} characters; the limit is 1024")
    if desc and not WHEN_CUE.search(desc):
        warnings.append("description says what the skill is but not when to use it; "
                        "the description is the only text a model sees when choosing a skill")
    comp = fm.get("compatibility")
    if comp and len(str(comp)) > 500:
        errors.append("compatibility is over 500 characters")

    body_lines = body.count("\n") + 1
    if body_lines > 500:
        errors.append(f"SKILL.md body is {body_lines} lines; keep it under 500 and move depth to references/")
    if re.search(r"^\s*TRIGGER\b", body, re.M):
        warnings.append("trigger phrases sit in the body; move them into the description, "
                        "which is what decides whether the skill loads")

    # A dotfile (.notes.md, a Mac's ._run.py) never reaches the archive, so it is not read.
    texts = {md: text}
    for d in BUNDLE_DIRS:
        for p in (p for p in tree if p.relative_to(skill).parts[0] == d):
            rel = p.relative_to(skill)
            if any(part.startswith(".") for part in rel.parts):
                continue
            try:
                if _carries_payload(p):
                    continue
            except OSError as e:  # held open with no share mode, or no permission: named once, here
                errors.append(_unreadable(rel.as_posix(), e))
                continue
            if p.is_file() and p.suffix.lower() in {".md", ".txt", ".py", ".json", ".sh", ".ps1", ".yaml", ".yml"}:
                t = _read_utf8(p, rel.as_posix(), errors)
                if t is not None:
                    texts[p] = t

    for src, t in texts.items():
        if src != md and _is_test_file(src.relative_to(skill)):
            continue
        for ref in sorted(set(REF_PATTERN.findall(t))):
            if any(part.startswith(".") and part not in (".", "..") for part in ref.split("/")):
                # present here, but the package leaves every dotfile out, so the installed skill lacks it
                errors.append(f"{src.relative_to(skill).as_posix()} references {ref}, which the package leaves "
                              f"out (a dotfile); rename it without the leading dot")
            elif not (skill / ref).exists() and not (src.parent / ref).exists():
                errors.append(f"{src.relative_to(skill).as_posix()} references {ref}, which does not exist")

    # Dotfiles (.keep, .gitignore) and junk never reach the archive, so they cannot be orphans in it;
    # junk is named once, below.
    bundled = [p for d in BUNDLE_DIRS for p in tree if p.relative_to(skill).parts[0] == d
               and p.is_file() and not any(part.startswith(".") for part in p.relative_to(skill).parts)
               and p.name not in JUNK_FILES and p.suffix != ".pyc"
               and not set(p.relative_to(skill).parts[:-1]) & JUNK_DIRS]
    everything = "\n".join(texts.values())
    for p in bundled:
        rel = p.relative_to(skill).as_posix()
        if rel not in everything and p.name not in everything:
            warnings.append(f"{rel} is not mentioned by SKILL.md or any other file (orphan)")
        if p.suffix == ".md" and p in texts and texts[p].count("\n") > 300:
            if "contents" not in texts[p][:1500].lower():
                warnings.append(f"{rel} is over 300 lines with no contents list")
        source = texts.get(p)
        if source is not None and source.startswith("﻿"):
            # A BOM breaks a file where the first bytes carry meaning: no system honours a #! line
            # that does not open the file (and the packager stores it without the executable bit),
            # and JSON forbids a BOM (json.loads rejects it). Elsewhere it is a warning, except in
            # a .ps1: Windows PowerShell reads a UTF-8 script by its BOM and ANSI without one.
            if source.startswith("﻿#!"):
                errors.append(f"{rel} has a UTF-8 byte-order mark (BOM) before its #! line, so no system runs it as "
                              f"a script and it is not stored executable; save it as plain UTF-8")
            elif p.suffix.lower() == ".json":
                errors.append(f"{rel} starts with a UTF-8 byte-order mark (BOM), which JSON forbids and json.loads "
                              f"rejects; save it as plain UTF-8")
            elif p.suffix.lower() == ".py":  # Python skips a BOM when it runs the file
                warnings.append(f"{rel} starts with a UTF-8 byte-order mark (BOM); Python runs it, but save it "
                                f"as plain UTF-8")
            elif p.suffix.lower() != ".ps1":
                warnings.append(f"{rel} starts with a UTF-8 byte-order mark (BOM); save it as plain UTF-8, which "
                                f"every surface reads")
        if p.suffix == ".py" and source is not None:
            try:
                compile(source.lstrip("﻿"), str(p), "exec")
            except (SyntaxError, ValueError) as e:  # a NUL byte is a ValueError on Python 3.10
                errors.append(f"{rel} does not compile: {e}")

    for p in tree:
        rel_parts = p.relative_to(skill).parts
        if rel_parts and rel_parts[0] in ROOT_SKIP_DIRS:
            continue
        if (p.is_dir() and p.name in JUNK_DIRS) or (p.is_file() and (p.name in JUNK_FILES or p.suffix == ".pyc")):
            if not (set(rel_parts[:-1]) & JUNK_DIRS):
                warnings.append(f"junk in the skill folder: {p.relative_to(skill).as_posix()}")

    for src, t in texts.items():
        if src.name == "validate_skill.py" and _is_this_validator(src):
            continue
        for marker, why in STALE_MARKERS.items():
            if marker in t:
                warnings.append(f"{src.relative_to(skill).as_posix()} mentions {marker}: {why}")
        for user in sorted(set(USER_PATH.findall(t))):
            warnings.append(f"{src.relative_to(skill).as_posix()} names the user folder '{user}': a path from one "
                            "person's machine breaks on others and discloses the account name; use ~ or a placeholder")

    return errors, warnings


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    unknown = [a for a in argv if a.startswith("-") and a != "--strict"]
    if unknown:
        print(f"unknown option: {' '.join(unknown)}\n"
              "Usage: python validate_skill.py <skill-folder> [<skill-folder> ...] [--strict]")
        return 2
    strict = "--strict" in argv
    folders = [a for a in argv if a != "--strict"]
    if not folders:
        print(__doc__)
        return 1
    bad = False
    for f in folders:
        errors, warnings = check(f)
        print(f"{Path(os.path.abspath(f)).name}: {len(errors)} error(s), {len(warnings)} warning(s)")
        for e in errors:
            print(f"  ERROR  {e}")
        for w in warnings:
            print(f"  WARN   {w}")
        bad = bad or bool(errors) or (strict and bool(warnings))
    return 1 if bad else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
