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

Errors are what claude.ai or the Skills API would reject, or what leaves the
skill broken: frontmatter keys and limits, a name that differs from its folder,
angle brackets in the description, a body over 500 lines, a referenced file that
does not exist (bare or ./-prefixed; test files - *_selftest.py, test_*.py,
*_test.py, anything under tests/ - name throwaway fixtures and are exempt),
a bundled Python script that does not compile, a file that is not UTF-8.

Warnings are what makes a skill trigger badly or age badly: no "when to use" cue
in the description (the description is all a model sees when it picks a skill),
trigger phrases kept in the body instead, files nothing points to, long
references without a contents list, a UTF-8 BOM, and paths from sandboxes that
no longer exist (/mnt/skills, /home/claude), one person's user folder in any
letter case, or tool names only one surface has.

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
JUNK_DIRS = {"__pycache__", "node_modules", ".pytest_cache"}
JUNK_FILES = {".DS_Store", "Thumbs.db"}
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


def _read_utf8(path, rel, errors):
    """Text of path, or None after an ERROR line naming the file and the bad byte."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(f"{rel} is not UTF-8 ({e.reason} at byte {e.start}); save it as UTF-8")
        return None


def _is_this_validator(path):
    """This file names the markers it hunts; a copy of it, of any version or edited, opens with the same
    first docstring line and is exempt; another skill's file of the same name does not and is checked."""
    signature = __doc__.strip().splitlines()[0]
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = [f.readline().strip() for _ in range(4)]
    except OSError:
        return False
    return signature in head


def _tree(skill):
    """Every path under the skill as the packager reads it: links of every kind followed
    alike, a link back to a folder already on the way down (a loop) cut, and folders that
    never ship (__pycache__ and the like, dot-folders such as .git or the .old-* a locked
    deploy leaves, evals/ and tests/ at the root) listed but not entered."""
    found = []

    def walk(folder, chain, top):
        for child in sorted(folder.iterdir()):
            found.append(child)
            if child.is_dir():
                real = os.path.normcase(os.path.realpath(child))
                if real in chain or child.name in JUNK_DIRS or child.name.startswith(".") \
                        or (top and child.name in ROOT_SKIP_DIRS):
                    continue
                walk(child, chain | {real}, False)

    walk(skill, frozenset({os.path.normcase(os.path.realpath(skill))}), True)
    return found


def _is_test_file(rel):
    """Test code names fixtures that need not exist, so it skips the missing-reference check."""
    return "tests" in rel.parts[:-1] or any(fnmatch.fnmatchcase(rel.name, pat)
                                            for pat in ("*_selftest.py", "test_*.py", "*_test.py"))


def check(skill_dir):
    """Return (errors, warnings) for one skill folder."""
    # abspath, not resolve(): '.' and '..' become the folder's own name, and a
    # junction or symlink an agent reaches the skill through keeps its name.
    skill = Path(os.path.abspath(skill_dir))
    errors, warnings = [], []
    md = skill / "SKILL.md"
    if not md.is_file():
        return [f"{skill}: SKILL.md not found"], []

    tree = _tree(skill)
    nested = [p for p in tree if p.name == "SKILL.md" and p != md and p.is_file()]
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

    texts = {md: text}
    for d in BUNDLE_DIRS:
        for p in (p for p in tree if p.relative_to(skill).parts[0] == d):
            if p.is_file() and p.suffix.lower() in {".md", ".txt", ".py", ".json", ".sh", ".ps1", ".yaml", ".yml"}:
                t = _read_utf8(p, p.relative_to(skill).as_posix(), errors)
                if t is not None:
                    texts[p] = t

    for src, t in texts.items():
        if src != md and _is_test_file(src.relative_to(skill)):
            continue
        for ref in sorted(set(REF_PATTERN.findall(t))):
            if not (skill / ref).exists() and not (src.parent / ref).exists():
                errors.append(f"{src.relative_to(skill).as_posix()} references {ref}, which does not exist")

    # Dotfiles (.keep, .gitignore) never reach the archive, so they cannot be orphans in it.
    bundled = [p for d in BUNDLE_DIRS for p in tree if p.relative_to(skill).parts[0] == d
               and p.is_file() and not any(part.startswith(".") for part in p.relative_to(skill).parts)]
    everything = "\n".join(texts.values())
    for p in bundled:
        rel = p.relative_to(skill).as_posix()
        if rel not in everything and p.name not in everything:
            warnings.append(f"{rel} is not mentioned by SKILL.md or any other file (orphan)")
        if p.suffix == ".md" and p in texts and texts[p].count("\n") > 300:
            if "contents" not in texts[p][:1500].lower():
                warnings.append(f"{rel} is over 300 lines with no contents list")
        if p.suffix == ".py" and p in texts:
            try:
                compile(texts[p], str(p), "exec")
            except SyntaxError as e:
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
