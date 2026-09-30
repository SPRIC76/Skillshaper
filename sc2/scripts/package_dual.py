#!/usr/bin/env python3
"""
Dual Skill Packager — one validated skill folder in, a .skill and a versioned .zip out.
package_dual.py v1.1 | 2026-09-15 (v1.0 2026-02-10)
Updated: 2026-09-30 04:02 ET — v1.2: deploy replaces only an absent or empty folder or its own skill
(a file, a folder of other files or another skill is refused; junctions detected on
Python 3.10/3.11 too); dotfiles left out; text files written with LF; a script with a
shebang stored executable.
Updated: 2026-09-30 04:44 ET — v1.3: deploy refuses the folder being packaged, removes a link inside
the target as a link, and lands whole or puts the old copy back; a skill reached through a
link keeps the link's name; archives are never written inside the skill; only known text
is rewritten with LF (a PDF or calendar file stays byte-for-byte); deployed scripts keep
their executable bit.

  {name}.skill        what claude.ai and the Claude desktop app install: upload it
                      in the skill settings, or open the file card an agent presents
  {name}-v{X.Y}.zip   the same archive, versioned, for keeping and for local agents:
                      extract so the folder lands at ~/.agents/skills/{name}/

Both hold {name}/SKILL.md at the root. validate_skill.py (beside this file) runs
first; any error stops packaging. Left out: evals/ and tests/ at the skill root,
*-workspace folders, __pycache__, node_modules, .git, .pytest_cache, *.pyc, dotfiles
(.gitignore, .env, .github/), OS junk. Text files (TEXT_SUFFIXES, or a script that
starts with #!) are written with LF line endings whatever the checkout uses; every
other file stays byte-for-byte; a script with a shebang is stored executable. The
archives are written outside the skill folder (--output inside it is refused).

--deploy HOME also replaces the contents of HOME/{name}/ with exactly what was
packaged, only when that folder is absent, empty, or holds a SKILL.md naming this
same skill; anything else (another skill, a folder of other files, a file, a symlink
or junction, the very folder being packaged) is refused with a message and nothing
changes. The replacement lands whole or the old copy is put back. The folder itself
stays, so a junction or symlink an agent uses to reach it keeps working; a link
inside it is removed as a link, never followed.

Usage:
    python package_dual.py <skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>] [--strict]
"""

import argparse
import fnmatch
import importlib.util
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", ".pytest_cache"}
ROOT_EXCLUDE_DIRS = {"evals", "tests"}
EXCLUDE_GLOBS = {"*.pyc"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}
# Written with LF line endings whatever the checkout uses; so is a script that starts
# with #!. Everything else is stored byte-for-byte: a binary need not hold a NUL byte
# (a PDF's xref offsets count its CRLFs), and some text must keep CRLF (.ics, .bat).
TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".sh", ".ps1",
                 ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".css", ".html",
                 ".xml", ".svg", ".csv", ".toml", ".ini", ".cfg", ".sql", ".rb", ".pl"}


def _say(text=""):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(enc, "replace").decode(enc))


def _validator():
    here = Path(__file__).resolve().parent / "validate_skill.py"
    spec = importlib.util.spec_from_file_location("validate_skill", here)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def should_exclude(rel_path: Path) -> bool:
    """rel_path is relative to the skill folder's parent, so parts[0] is the skill name."""
    parts = rel_path.parts
    if any(p in EXCLUDE_DIRS or p.endswith("-workspace") for p in parts[:-1]):
        return True
    if len(parts) > 2 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    # Dotfiles and dot-folders (.gitignore, .env, .github/) belong to the checkout, not the skill.
    if any(p.startswith(".") for p in parts[1:]):
        return True
    return any(fnmatch.fnmatch(rel_path.name, pat) for pat in EXCLUDE_GLOBS)


def _is_text(path: Path, head: bytes) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or (head.startswith(b"#!") and b"\0" not in head)


def _inside(path, folder) -> bool:
    """Is path the folder itself or somewhere inside it, links followed on both sides?"""
    p, f = (os.path.normcase(os.path.realpath(x)) for x in (path, folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def create_zip(skill_path: Path, output_path: Path) -> int:
    count = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(skill_path.rglob("*")):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(skill_path.parent)
            if should_exclude(arcname):
                continue
            data = file_path.read_bytes()
            info = zipfile.ZipInfo.from_file(file_path, arcname.as_posix())
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o644
            if _is_text(file_path, data[:8192]):
                data = data.replace(b"\r\n", b"\n")
                if data.startswith(b"#!"):
                    mode = 0o755  # a script with a shebang is stored executable
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, data)
            count += 1
    return count


def _skill_name_in(folder: Path):
    md = folder / "SKILL.md"
    if not md.is_file():
        return None
    m = re.search(r"^name:\s*(.+?)\s*$", md.read_text(encoding="utf-8", errors="replace"), re.M)
    return m.group(1).strip("'\"") if m else None


def _is_link(path: Path) -> bool:
    """A symlink, or on Windows any reparse point (a junction included), on every
    Python from 3.10 up: Path.is_junction only exists from 3.12."""
    if path.is_symlink():
        return True
    try:
        attrs = os.lstat(path).st_file_attributes
    except (OSError, AttributeError):
        return False
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _remove(path: Path):
    """A file, a link (never what it points at) or a folder of them; nothing is followed."""
    if _is_link(path) or not path.is_dir():
        path.unlink()  # on Windows this removes a junction or folder symlink itself
        return
    for child in path.iterdir():
        _remove(child)
    path.rmdir()


def _unpack(archive: Path, skill_name: str, target: Path):
    with zipfile.ZipFile(archive) as zf:
        prefix = skill_name + "/"
        for info in zf.infolist():
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            out = target / info.filename[len(prefix):]
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            mode = info.external_attr >> 16 & 0o777
            if mode and os.name != "nt":
                os.chmod(out, mode)  # the executable bit the archive records


def deploy(archive: Path, skill_name: str, home: Path, source=None) -> Path:
    target = home / skill_name
    if home.exists() and not home.is_dir():
        raise RuntimeError(f"{home} is not a folder; nothing changed")
    if _is_link(target):
        raise RuntimeError(f"{target} is a link; deploy to the folder it points at instead")
    if target.exists() and not target.is_dir():
        raise RuntimeError(f"{target} is a file, not a skill folder; nothing changed")
    # A skill developed in place under its skills home is the very folder being
    # packaged: replacing it would delete everything the archive leaves out.
    if source is not None and (_inside(target, source) or _inside(source, target)):
        raise RuntimeError(f"{target} is the folder being packaged; deploy to another skills home "
                           "or package from a copy; nothing changed")
    # Replace only what is absent, empty, or this same skill: one wrong --deploy
    # argument must never empty a folder of somebody's other files.
    if target.is_dir() and any(target.iterdir()):
        existing = _skill_name_in(target)
        if existing != skill_name:
            held = f"holds the skill '{existing}'" if existing else "holds files that are not a skill (no SKILL.md)"
            raise RuntimeError(f"{target} {held}, not '{skill_name}'; nothing changed")
    created = not target.exists()
    target.mkdir(parents=True, exist_ok=True)
    # Move the old copy aside inside the folder, unpack, then drop it: the
    # replacement lands whole, or every old file goes back where it was.
    aside = Path(tempfile.mkdtemp(prefix=".old-", dir=target))
    moved, unpacking = [], False
    try:
        for child in sorted(target.iterdir()):
            if child != aside:
                child.rename(aside / child.name)
                moved.append(child.name)
        unpacking = True
        _unpack(archive, skill_name, target)
    except OSError as e:
        try:
            if unpacking:
                for child in list(target.iterdir()):
                    if child != aside:
                        _remove(child)
            for n in moved:
                (aside / n).rename(target / n)
            aside.rmdir()
            if created:
                target.rmdir()
        except OSError as e2:
            raise RuntimeError(f"{target} could not be replaced ({e}), and putting the old copy back "
                               f"failed ({e2}); the old files are in {aside}") from e2
        raise RuntimeError(f"{target} could not be replaced ({e}); the old copy is back, nothing changed") from e
    try:
        _remove(aside)
    except OSError as e:
        _say(f"⚠️ Deployed, but the old copy could not be removed ({e}); delete {aside} when it is free")
    return target


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dual skill packager (.skill + versioned .zip)")
    ap.add_argument("skill_folder")
    ap.add_argument("--version", "-v", required=True, help="e.g. 1.1")
    ap.add_argument("--output", "-o", default=".", help="output directory")
    ap.add_argument("--deploy", metavar="SKILLS_HOME", help="also install into SKILLS_HOME/<name>/")
    ap.add_argument("--strict", action="store_true", help="treat validator warnings as errors")
    args = ap.parse_args(argv)

    # abspath, not resolve(): a skill reached through a junction or symlink keeps
    # the link's name, as validate_skill.py reads it.
    skill_path = Path(os.path.abspath(args.skill_folder))
    if not skill_path.is_dir():
        _say(f"❌ Not a directory: {skill_path}")
        return 1
    out = Path(args.output).resolve()
    if _inside(out, skill_path):
        _say(f"❌ --output {out} is inside the skill folder, so the archives would pack themselves; "
             f"write them outside it, e.g. --output {skill_path.parent / 'dist'}. Nothing packaged.")
        return 1
    home = Path(args.deploy).expanduser().resolve() if args.deploy else None
    if home is not None and home.exists() and not home.is_dir():
        _say(f"❌ Deploy refused: {home} is not a folder. Nothing packaged.")
        return 1

    errors, warnings = _validator().check(skill_path)
    for e in errors:
        _say(f"❌ {e}")
    for w in warnings:
        _say(f"⚠️ {w}")
    if errors or (args.strict and warnings):
        _say("❌ Validation failed; nothing packaged.")
        return 1
    _say(f"✅ Valid ({len(warnings)} warning(s))")

    name = skill_path.name
    out.mkdir(parents=True, exist_ok=True)
    skill_file = out / f"{name}.skill"
    count = create_zip(skill_path, skill_file)
    zip_file = out / f"{name}-v{args.version}.zip"
    shutil.copyfile(skill_file, zip_file)
    _say(f"📦 {skill_file} ({count} files, {skill_file.stat().st_size / 1024:.1f} KB)")
    _say(f"📦 {zip_file}")

    if home is not None:
        try:
            target = deploy(skill_file, name, home, source=skill_path)
        except RuntimeError as e:
            _say(f"❌ Deploy refused: {e}")
            return 1
        _say(f"🚚 Deployed to {target}")

    _say(f"✅ Dual packaging complete: {name}")
    _say("   .skill → upload in claude.ai skill settings (or open the presented file card)")
    _say(f"   .zip   → keep; for local agents extract to ~/.agents/skills/{name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
