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
Updated: 2026-09-30 05:25 ET — v1.4: links of every kind are followed alike, a loop or a link out to
the archives cut; deploy clears a read-only file, never nests an old copy still in use,
and refuses a working copy (.git, .env, tests/ ...) before anything is built, as it does
a --deploy path through a file; run inside the skill, the archives go beside it; a file
with no suffix that holds UTF-8 text is written with LF.

  {name}.skill       what claude.ai and the Claude desktop app install: upload it
                      in the skill settings, or open the file card an agent presents
  {name}-v{X.Y}.zip   the same archive, versioned, for keeping and for local agents:
                      extract so the folder lands at ~/.agents/skills/{name}/

Both hold {name}/SKILL.md at the root. validate_skill.py (beside this file) runs
first; any error stops packaging. Left out: evals/ and tests/ at the skill root,
*-workspace folders, __pycache__, node_modules, .git, .pytest_cache, *.pyc, dotfiles
(.gitignore, .env, .github/), OS junk. Links of every kind are followed alike; a link
back to a folder already on the way (a loop) or out to the archives is cut. Text files
(TEXT_SUFFIXES, a file with no suffix holding UTF-8 text, or a script that starts with
#!) are written with LF line endings whatever the checkout uses; every other file
stays byte-for-byte; a script with a shebang is stored executable. The archives are
written outside the skill folder: beside it when run inside it, and an --output
inside it is refused.

--deploy HOME also replaces the contents of HOME/{name}/ with exactly what was
packaged, only when that folder is absent, empty, or an installed copy of this same
skill; anything else (another skill, a folder of other files, a file, a symlink or
junction, the very folder being packaged, a working copy holding what the package
leaves out) is refused before anything is built, and nothing changes. The replacement
lands whole or the old copy is put back. The folder itself stays, so a junction or
symlink an agent uses to reach it keeps working; a link inside it is removed as a
link, never followed.

Usage:
    python package_dual.py <skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>] [--strict]
"""

import argparse
import codecs
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
# Regenerated on the next run: an installed copy may hold them and still be replaced.
CACHES = {"__pycache__", ".pytest_cache", "node_modules"}
# Written with LF line endings whatever the checkout uses; so is a script that starts
# with #!, and a file with no suffix that holds UTF-8 text (LICENSE, Makefile).
# Everything else is stored byte-for-byte: a binary need not hold a NUL byte
# (a PDF's xref offsets count its CRLFs), and some text must keep CRLF (.ics, .bat).
TEXT_SUFFIXES = {".md", ".markdown", ".mdx", ".rst", ".adoc", ".tex", ".bib", ".txt",
                 ".json", ".jsonl", ".ndjson", ".ipynb", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                 ".conf", ".properties", ".csv", ".tsv", ".xml", ".svg", ".html", ".htm",
                 ".css", ".scss", ".sass", ".less", ".sql", ".graphql", ".gql", ".proto",
                 ".py", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1",
                 ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".jsx", ".tsx", ".vue", ".svelte",
                 ".rb", ".pl", ".pm", ".php", ".lua", ".r", ".jl", ".go", ".rs", ".java",
                 ".kt", ".kts", ".scala", ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs",
                 ".dart", ".ex", ".exs", ".erl", ".hs", ".ml", ".clj", ".tf", ".hcl", ".gradle"}


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
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    if b"\0" in head:
        return False
    if head.startswith(b"#!"):
        return True
    if path.suffix:
        return False  # a suffix not listed stays byte-for-byte
    try:
        codecs.getincrementaldecoder("utf-8")().decode(head)  # not final: head may cut a character
    except UnicodeDecodeError:
        return False
    return True


def _inside(path, folder) -> bool:
    """Is path the folder itself or somewhere inside it, links followed on both sides?"""
    p, f = (os.path.normcase(os.path.realpath(x)) for x in (path, folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def _files(skill_path: Path, out=None):
    """Every file the package holds, links of every kind (junction, folder or file symlink)
    followed alike. Cut: a link back to a folder already on the way down (a loop), and a
    link that leaves the skill to reach the archives: the output folder, a folder above
    it, or, when the archives are written beside the skill, a file in that folder.
    Excluded folders (.git, node_modules, tests/ ...) are not entered."""
    root = os.path.realpath(skill_path)
    beside = out is not None and _inside(root, out)
    found = []

    def cut(real, is_dir):
        if out is None or _inside(real, root):
            return False
        if _inside(out, real):
            return True
        if beside:  # a sibling folder is fair; a file lying next to the archives is not
            return not is_dir and os.path.normcase(os.path.dirname(real)) == os.path.normcase(os.path.realpath(out))
        return _inside(real, out)

    def walk(folder: Path, chain):
        for child in sorted(folder.iterdir()):
            rel = child.relative_to(skill_path.parent)
            real = os.path.realpath(child)
            if child.is_dir():
                key = os.path.normcase(real)
                if key not in chain and not should_exclude(rel / "_") and not cut(real, True):
                    walk(child, chain | {key})
            elif child.is_file() and not should_exclude(rel) and not cut(real, False):
                found.append(child)

    walk(skill_path, frozenset({os.path.normcase(root)}))
    return found


def create_zip(skill_path: Path, output_path: Path) -> int:
    count = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in _files(skill_path, output_path.parent):
            arcname = file_path.relative_to(skill_path.parent)
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
    """A file, a link (never what it points at) or a folder of them; nothing is followed.
    A read-only file, which Windows will not delete, has the flag cleared first."""
    if _is_link(path) or not path.is_dir():
        try:
            path.unlink()  # on Windows this removes a junction or folder symlink itself
        except PermissionError:
            if _is_link(path):
                raise  # chmod would follow the link to what it points at
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            path.unlink()
        return
    for child in path.iterdir():
        _remove(child)
    path.rmdir()


def _left_out(target: Path, skill_name: str):
    """What an existing copy holds that the package leaves out, caches and junk aside:
    the marks of a working copy (.git, .env, tests/, evals/, a *-workspace)."""
    found = []

    def walk(folder: Path):
        for child in sorted(folder.iterdir()):
            name = child.name
            if name in CACHES or name in EXCLUDE_FILES or name.endswith(".pyc") \
                    or (folder == target and name.startswith(".old-")):
                continue
            rel = Path(skill_name) / child.relative_to(target)
            is_dir = child.is_dir() and not _is_link(child)
            if should_exclude(rel / "_" if is_dir else rel):
                found.append(child.relative_to(target).as_posix() + ("/" if is_dir else ""))
            elif is_dir:
                walk(child)

    walk(target)
    return found


def _refusal(skill_name: str, home: Path, source=None):
    """Why deploying skill_name into home would harm something, or None when it is safe."""
    for p in (home, *home.parents):
        if p.exists():
            if not p.is_dir():
                return f"{home} is not a folder" if p == home else f"{p} is a file, so {home} cannot be made"
            break
    target = home / skill_name
    if _is_link(target):
        return f"{target} is a link; deploy to the folder it points at instead"
    if target.exists() and not target.is_dir():
        return f"{target} is a file, not a skill folder"
    # A skill developed in place under its skills home is the very folder being
    # packaged: replacing it would delete everything the archive leaves out.
    if source is not None and (_inside(target, source) or _inside(source, target)):
        return f"{target} is the folder being packaged; deploy to another skills home"
    # Replace only what is absent, empty, or an installed copy of this same skill:
    # one wrong --deploy argument must never empty somebody's other files.
    if target.is_dir() and any(not c.name.startswith(".old-") for c in target.iterdir()):
        existing = _skill_name_in(target)
        if existing != skill_name:
            held = f"holds the skill '{existing}'" if existing else "holds files that are not a skill (no SKILL.md)"
            return f"{target} {held}, not '{skill_name}'"
        kept = _left_out(target, skill_name)
        if kept:
            shown = ", ".join(kept[:8]) + (f" and {len(kept) - 8} more" if len(kept) > 8 else "")
            return (f"{target} holds {shown}, which the package leaves out: it is a working copy, and "
                    "replacing it would delete them; deploy to a skills home of installed copies")
    return None


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
    why = _refusal(skill_name, home, source)
    if why:
        raise RuntimeError(f"{why}; nothing changed")
    target = home / skill_name
    created = not target.exists()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"{target} could not be made ({e}); nothing changed") from e
    # An old copy an earlier deploy could not remove goes now, or, still in use,
    # stays where it is: it is never moved inside the next one.
    stale = []
    for child in sorted(target.iterdir()):
        if child.name.startswith(".old-") and child.is_dir() and not _is_link(child):
            try:
                _remove(child)
            except OSError:
                stale.append(child)
    # Move the old copy aside inside the folder, unpack, then drop it: the
    # replacement lands whole, or every old file goes back where it was.
    aside = Path(tempfile.mkdtemp(prefix=".old-", dir=target))
    moved, unpacking = [], False
    try:
        for child in sorted(target.iterdir()):
            if child != aside and child not in stale:
                child.rename(aside / child.name)
                moved.append(child.name)
        unpacking = True
        _unpack(archive, skill_name, target)
    except OSError as e:
        try:
            if unpacking:
                for child in list(target.iterdir()):
                    if child != aside and child not in stale:
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
    for s in stale:
        _say(f"⚠️ {s} is an old copy from an earlier deploy, still in use; delete it when it is free")
    return target


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dual skill packager (.skill + versioned .zip)")
    ap.add_argument("skill_folder")
    ap.add_argument("--version", "-v", required=True, help="e.g. 1.1")
    ap.add_argument("--output", "-o",
                    help="output directory (default: the current one, or beside the skill when run inside it)")
    ap.add_argument("--deploy", metavar="SKILLS_HOME", help="also install into SKILLS_HOME/<name>/")
    ap.add_argument("--strict", action="store_true", help="treat validator warnings as errors")
    args = ap.parse_args(argv)

    # abspath, not resolve(): a skill reached through a junction or symlink keeps
    # the link's name, as validate_skill.py reads it.
    skill_path = Path(os.path.abspath(args.skill_folder))
    if not skill_path.is_dir():
        _say(f"❌ Not a directory: {skill_path}")
        return 1
    if args.output is None:
        out = Path.cwd().resolve()
        if _inside(out, skill_path):
            out = skill_path.parent.resolve()  # run inside the skill: the archives go beside it
    else:
        out = Path(args.output).resolve()
        if _inside(out, skill_path):
            _say(f"❌ --output {out} is inside the skill folder, so the archives would pack themselves; "
                 f"write them outside it, e.g. --output {skill_path.parent / 'dist'}. Nothing packaged.")
            return 1
    home = Path(args.deploy).expanduser().resolve() if args.deploy else None
    if home is not None:  # asked before anything is built; deploy() asks again at the moment it acts
        why = _refusal(skill_path.name, home, source=skill_path)
        if why:
            _say(f"❌ Deploy refused: {why}. Nothing packaged.")
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
