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
Updated: 2026-09-30 06:03 ET — v1.5: archives written beside the skill cut only the archives, so a LICENSE
linked in from beside it ships; deploy replaces and names what an older install holds that
the package leaves out (a .gitignore), refuses a .venv, .hg or .svn working copy, counts a
folder of OS junk as empty and clears a read-only folder in the old copy; an --output that
is a file is refused before packaging; text is judged on the whole file, and a file that
starts with #! is always stored executable; desktop.ini and __MACOSX are left out.
Updated: 2026-09-30 06:34 ET — v1.6: beside also means beside the link a skill is reached through, so
a LICENSE linked from there ships; an --output inside the deploy target is refused
before packaging; an archive that cannot be written (left read-only, held open) stops
the run with a message instead of a traceback; .envrc marks a working copy; a stale
old copy is named as still in use, since a read-only one is now removed.
Updated: 2026-09-30 12:36 ET — v1.7: both archives land together or not at all (each built under a temporary
name beside its target, the pair moved into place once both are complete, the earlier pair put
back if either move fails); a source file that cannot be read, an archive that cannot be
replaced and an --output that cannot be made are each one message naming the file and the
reason, the earlier archives untouched; run inside the skill through a link that loops back
into it, the archives go beside its real folder, so an archive never packs itself.
Updated: 2026-09-30 14:08 ET — v1.8: an --output folder, or an installed copy, that exists but takes no new file from
this user is one message at once (temporary names are made with O_EXCL, never tempfile's 2^31 retries
behind a Windows ACL); --version takes digits, letters, dots and dashes only; a folder at an archive's
name, a full disk and an unreachable path each get their own advice, naming the archive and never a
temporary; a folder that cannot be listed and an installed copy whose SKILL.md is held are one message;
a file dated before 1980 is packaged dated 1980-01-01 and named; a double failure while landing names
every file left where it does not belong.
Updated: 2026-09-30 14:46 ET — v1.9: a file dated before 1970 or past about 3000, which Windows' localtime refuses, is
packaged at the zip format's nearest edge instead of failing as unreadable; a date past 2107 is stored 2107-12-31;
each edge is one line for all its files, not one per file; a skills home that exists but takes no new folder
from this user is refused before anything is built, in the voice of every other message; --version must start
and end with a digit or letter and is at most 64 characters, so the .zip's name is one every file system takes.
Updated: 2026-09-30 15:37 ET — v1.10: a skills home not made yet is probed at the nearest folder above it, so one under a
folder that takes no new folder is refused before anything is built; the probe runs once (main, not deploy
again) and one that cannot be removed is named; every deploy message says the reason in words, never as an
[Errno] repr; each file past a date edge is listed as "name dated YYYY-MM-DD" (or "before 1970", "past about
3000" where localtime refuses), with no parentheses inside parentheses.
Updated: 2026-09-30 16:43 ET — v1.11: a skills home with no folder above it at all (a drive or share that is not there) is
refused before anything is built, never after with "nothing changed"; a first deploy's empty aside folder that
cannot be removed is named as that, not as an old copy; the help and closing lines name no host and assume no
skills folder (the Agent Skills format is for any agent).

  {name}.skill       for a host that installs a skill from an uploaded archive: upload
                      it in its skill settings, or open the file card an agent presents
  {name}-v{X.Y}.zip   the same archive, versioned, for keeping and for local agents:
                      extract it into your agent's skills folder so it lands as
                      <skills-folder>/{name}/ (--deploy <skills-home> does this for you)

Both hold {name}/SKILL.md at the root. validate_skill.py (beside this file) runs
first; any error stops packaging. Left out: evals/ and tests/ at the skill root,
*-workspace folders, __pycache__, node_modules, .git, .pytest_cache, *.pyc, dotfiles
(.gitignore, .env, .github/), OS junk (.DS_Store, Thumbs.db, desktop.ini, __MACOSX).
Links of every kind are followed alike; a link back to a folder already on the way (a
loop) or out to the archives is cut, and when the archives go beside the skill (or
beside the link it is reached through) only they are cut, so a LICENSE linked in from
there ships. A file that is UTF-8 text
throughout, with no NUL byte, and is a TEXT_SUFFIXES type, has no suffix, or starts
with #! is written with LF line endings whatever the checkout uses; every other file
stays byte-for-byte; a file that starts with #! is stored executable. The archives are
written outside the skill folder: beside it when run inside it (beside its real folder
when the path given reaches it through a link that loops back into it), and an --output
inside it or inside the deploy target, or one that is a file, is refused. Both archives
land together or not at all: each is built under a temporary name beside its target and
the pair is moved into place only when both are complete, the earlier pair put back if
either move fails. A source file or folder that cannot be read, an archive that cannot be
replaced (left read-only, held open, a folder standing at its name), an --output that cannot
be made or that takes no new file from this user, and a full disk each stop the run with one
message naming the file and the reason; the earlier archives are untouched. --version takes
digits, letters, dots and dashes (1.0, 2.1-rc1), so the .zip always lands in --output. A
file dated before 1980, which the zip format cannot hold, is stored dated 1980-01-01 and named.

--deploy HOME also replaces the contents of HOME/{name}/ with exactly what was
packaged, only when that folder is absent, empty, or an installed copy of this same
skill; anything else (another skill, a folder of other files, a file, a symlink or
junction, the very folder being packaged, a working copy marked by .git, .env, .envrc,
.venv, .hg, .svn, a *-workspace folder, or tests/ or evals/ at its root) is refused
before anything is built, and nothing changes; anything else the package leaves out
(a .gitignore that packagers before 1.4 shipped) is replaced and named, and OS junk
and caches pass unmentioned. The replacement lands whole or the old copy is put back.
The folder itself stays, so a junction or symlink an agent uses to reach it keeps
working; a link inside it is removed as a
link, never followed.

Usage:
    python package_dual.py <skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>] [--strict]
"""

import argparse
import errno
import fnmatch
import importlib.util
import os
import re
import secrets
import shutil
import stat
import sys
import time
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", ".pytest_cache", "__MACOSX"}
ROOT_EXCLUDE_DIRS = {"evals", "tests"}
EXCLUDE_GLOBS = {"*.pyc"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
# What an operating system or a tool leaves in a folder: replaced without a word.
JUNK = EXCLUDE_FILES | {"__MACOSX", "__pycache__", ".pytest_cache", "node_modules",
                        ".mypy_cache", ".ruff_cache"}
# The marks of a working copy: a --deploy target holding one is refused, since replacing it
# would delete them. Anything else the package leaves out (.gitignore, which packagers before
# 1.4 shipped) is replaced and named.
MARKS = {".git", ".env", ".envrc", ".venv", ".hg", ".svn"}


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


_V = _validator()  # the validator also holds archive_cut, so both walk the skill alike
_inside = _V._inside
# Written with LF line endings whatever the checkout uses, when the whole file is UTF-8
# with no NUL byte and it is one of these types (the validator's list, so both read the
# same files as text), a script that starts with #!, or a file with no suffix (LICENSE,
# Makefile). Everything else is stored byte-for-byte: a binary need not hold a NUL byte
# (a PDF's xref offsets count its CRLFs), and some text must keep CRLF (.ics, .bat).
TEXT_SUFFIXES = _V.TEXT_SUFFIXES


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


def _is_text(path: Path, data: bytes) -> bool:
    """Read on the whole file: a script whose text head carries a binary payload stays whole."""
    if b"\0" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or data.startswith(b"#!") or not path.suffix


def _files(skill_path: Path, out=None):
    """Every file the package holds, links of every kind (junction, folder or file symlink)
    followed alike. Cut: a link back to a folder already on the way down (a loop), and a
    link that leaves the skill to reach the archives (validate_skill.archive_cut).
    Excluded folders (.git, node_modules, tests/ ...) are not entered."""
    root = os.path.realpath(skill_path)
    found = []

    def walk(folder: Path, chain):
        try:
            children = sorted(folder.iterdir())
        except OSError as e:  # a folder this run may not list: named as a read failure, not a traceback
            raise ReadFailed(e.errno, e.strerror or str(e), str(folder)) from e
        for child in children:
            rel = child.relative_to(skill_path.parent)
            real = os.path.realpath(child)
            if child.is_dir():
                key = os.path.normcase(real)
                if key not in chain and not should_exclude(rel / "_") \
                        and not _V.archive_cut(real, root, out, skill_path.name, True, skill_path):
                    walk(child, chain | {key})
            elif child.is_file() and not should_exclude(rel) \
                    and not _V.archive_cut(real, root, out, skill_path.name, False, skill_path):
                found.append(child)

    walk(skill_path, frozenset({os.path.normcase(root)}))
    return found


class ReadFailed(OSError):
    """A file the archive needs could not be read; filename names it, strerror says why."""


def create_zip(skill_path: Path, output_path: Path) -> int:
    """Write the archive of skill_path to output_path; raises ReadFailed for a source file the
    operating system would not let this run read (held open with no share mode, no permission)."""
    count, early, late = 0, [], []
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in _files(skill_path, output_path.parent):
            arcname = file_path.relative_to(skill_path.parent)
            try:
                data = file_path.read_bytes()
                mtime = file_path.stat().st_mtime
            except OSError as e:
                raise ReadFailed(e.errno, e.strerror or str(e), str(file_path)) from e
            # The zip format holds a date from 1980 to 2107: a file a tar or a container layer left dated
            # 1970 is stored dated 1980-01-01, one dated past 2107 is stored dated 2107-12-31, and each is
            # named once for all such files (not a traceback, and not one line per file). The entry is
            # built by hand: ZipInfo.from_file asks localtime, which on Windows refuses a time before 1970
            # or past about the year 3000 with EINVAL, and that is no read failure of the file.
            shown = arcname.relative_to(arcname.parts[0]).as_posix()
            try:
                modified = time.localtime(mtime)
            except (OSError, OverflowError, ValueError):
                modified = None
            # the side of a date localtime refuses: near 1970 (a zone west of UTC puts 0 in 1969) or past 3000
            before = mtime < 86400 * 366 * 500
            if modified is None:
                date_time, where = ((1980, 1, 1, 0, 0, 0), early) if before else ((2107, 12, 31, 23, 59, 58), late)
            elif modified.tm_year < 1980:
                date_time, where = (1980, 1, 1, 0, 0, 0), early
            elif modified.tm_year > 2107:
                date_time, where = (2107, 12, 31, 23, 59, 58), late
            else:
                date_time, where = tuple(modified)[:6], None
            if where is not None:
                # every file dated, none in nested parentheses; a date localtime refuses is named by its side
                when = (time.strftime("%Y-%m-%d", modified) if modified is not None
                        else "before 1970" if before else "past about 3000")
                where.append(f"{shown} dated {when}")
            info = zipfile.ZipInfo(arcname.as_posix(), date_time=date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if data.startswith(b"#!") else 0o644  # a script with a shebang is stored executable
            if _is_text(file_path, data):
                data = data.replace(b"\r\n", b"\n")
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, data)
            count += 1
    for names, edge, stored in ((early, "before the zip format's 1980 floor", "1980-01-01"),
                                (late, "past the zip format's 2107 ceiling", "2107-12-31")):
        if names:
            listed = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
            _say(f"ℹ️ {len(names)} file{'s are' if len(names) > 1 else ' is'} dated {edge}: {listed}; "
                 f"{'their entries are' if len(names) > 1 else 'its entry is'} dated {stored}")
    return count


def _unwritable(path: Path):
    """Why an archive already at path could not be replaced, as (reason, what to do), or None: a folder
    standing at its name, or a file left read-only or held open with no share mode. Asked before
    anything is built, so a run that would fail changes nothing."""
    if not path.exists():
        return None
    if path.is_dir():
        return "a folder stands at this name", "move it aside or choose another --output"
    try:
        open(path, "r+b").close()
    except OSError as e:
        return e.strerror or str(e), "unlock or close it and run again"
    return None


def _fresh(folder: Path, prefix: str, suffix: str, directory=False) -> Path:
    """A new empty file (or folder) in folder under a name nothing else holds, made at once with O_EXCL.
    Not tempfile.mkstemp or mkdtemp: on Windows those retry a PermissionError up to 2**31 times whenever
    os.access calls the folder writable, and os.access reads only the READONLY attribute, never an ACL
    (C:\\, C:\\Program Files, an icacls deny), so a folder that takes no new file spun for hours. Here it
    is the OSError it is, at once."""
    for _ in range(100):
        path = folder / f"{prefix}{secrets.token_hex(4)}{suffix}"
        try:
            if directory:
                path.mkdir()
            else:
                os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
        except FileExistsError:
            continue
        return path
    raise FileExistsError(errno.EEXIST, "no free name after 100 tries", str(folder / f"{prefix}*{suffix}"))


def _write_failure(e: OSError, out: Path) -> str:
    """One line for an archive that could not be written: the archive (never a temporary), the reason,
    and what to do, by the error: a full disk, a folder that takes no new file, an unreachable path, or
    a file held or left read-only."""
    path = Path(e.filename) if e.filename else out
    why = e.strerror or str(e)
    if e.errno == errno.ENOSPC:
        return f"{path} could not be written ({why}); free some space on that drive and run again."
    if path == out:
        return f"{out} takes no new file from this user ({why}); choose an --output you may write to."
    if e.errno in (errno.ENOENT, errno.EINVAL):
        return f"{path} could not be written ({why}); give --output a folder this system can reach."
    return f"{path} could not be written ({why}); unlock or close it and run again."


def _land(pairs):
    """Move each finished file onto its target, all or none: a target already there is set aside
    beside it first; if any move fails, every old file goes back and every new one is removed, and
    the OSError names the target. The pattern deploy() uses: the new pair lands whole, or nothing changes."""
    aside, landed = [], []
    try:
        for tmp, target in pairs:
            try:
                if target.exists():
                    old = _fresh(target.parent, target.name + ".", ".old")
                    try:
                        os.replace(target, old)
                    except OSError:
                        os.unlink(old)
                        raise
                    aside.append((old, target))
                os.replace(tmp, target)
                landed.append(target)
            except OSError as e:
                raise OSError(e.errno, e.strerror or str(e), str(target)) from e
    except OSError as e:
        # Put things back with every step tried, then judge by what is left on disk: an earlier
        # archive still under its aside name, and a new file that could not be removed (one whose
        # aside is still on disk stands at the earlier one's name), are each named with what to do.
        for new in landed:
            try:
                new.unlink()
            except OSError:
                pass
        for old, back in aside:
            try:
                os.replace(old, back)
            except OSError:
                pass
        left = [(old, back) for old, back in aside if old.exists()]
        held_backs = {back for _, back in left}
        stuck = [new for new in landed if new.exists() and (new in held_backs or new not in {b for _, b in aside})]
        if left or stuck:
            what = []
            for old, back in left:
                what.append(f"the earlier {back.name} is at {old}"
                            + (f" and the new one stands at {back}" if back in stuck else f" and {back} is empty"))
            what.extend(f"the new {new.name} stands at {new}" for new in stuck if new not in held_backs)
            raise RuntimeError(f"{e.filename} could not be written ({e.strerror or e}), and putting things back failed too: "
                               f"{'; '.join(what)}. The archives at their names no longer match: when they are free, "
                               f"delete each new file, rename each .old back to its name, and run again") from e
        raise
    for old, _ in aside:
        try:
            old.unlink()
        except OSError as e:  # a hold that arrived after the rename: nothing of the new pair is affected
            _say(f"⚠️ The earlier archive set aside as {old} could not be removed ({e.strerror or e}); delete it "
                 "when it is free")


def build_archives(skill_path: Path, skill_file: Path, zip_file: Path) -> int:
    """Both archives, whole or not at all: the .skill is built under a temporary name beside its
    target, copied to the .zip's temporary name, and the pair is moved into place only when both
    are complete. ReadFailed names a source file that could not be read; any other OSError names
    the archive that could not be written. Nothing but the temporaries changes until the move."""
    out = skill_file.parent
    temps = []
    try:
        for target in (skill_file, zip_file):
            try:
                temps.append(_fresh(out, target.name + ".", ".part"))
            except PermissionError as e:  # the folder takes no new file from this user: named as the folder
                raise OSError(e.errno, e.strerror or str(e), str(out)) from e
            except OSError as e:  # a full disk, a path gone: named by the archive it was for
                raise OSError(e.errno, e.strerror or str(e), str(target)) from e
        for target, tmp, step in ((skill_file, temps[0], "build"), (zip_file, temps[1], "copy")):
            try:
                if step == "build":
                    count = create_zip(skill_path, tmp)
                else:
                    shutil.copyfile(temps[0], tmp)
            except ReadFailed:
                raise
            except OSError as e:  # a full disk while writing: named by the archive, never the temporary
                raise OSError(e.errno, e.strerror or str(e), str(target)) from e
        _land(list(zip(temps, (skill_file, zip_file))))
    finally:
        for tmp in temps:  # gone once landed; left only by a failure
            tmp.unlink(missing_ok=True)
    return count


def _skill_name_in(folder: Path):
    """The name an installed copy's SKILL.md declares, or None; an OSError (the file held with no share
    mode, no permission) is the caller's to name."""
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
    try:
        path.rmdir()
    except PermissionError:
        if os.name != "nt":
            raise
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)  # a folder's READONLY attribute blocks rmdir on Windows
        path.rmdir()


def _is_junk(name: str) -> bool:
    return name in JUNK or name.endswith(".pyc") or name.startswith("._")  # ._x: macOS's AppleDouble


def _left_out(target: Path, skill_name: str):
    """What an existing copy holds that the package leaves out, junk aside, as (marks, others):
    marks of a working copy (.git, .env, .venv, tests/ and evals/ at the root, a *-workspace)
    and everything else, such as the .gitignore packagers before 1.4 shipped."""
    marks, others = [], []

    def walk(folder: Path):
        for child in sorted(folder.iterdir()):
            name = child.name
            if _is_junk(name) or (folder == target and name.startswith(".old-")):
                continue
            rel = Path(skill_name) / child.relative_to(target)
            is_dir = child.is_dir() and not _is_link(child)
            shown = child.relative_to(target).as_posix() + ("/" if is_dir else "")
            if name in MARKS or name.startswith(".env.") or (is_dir and name.endswith("-workspace")) \
                    or (is_dir and folder == target and name in ROOT_EXCLUDE_DIRS):
                marks.append(shown)
            elif should_exclude(rel / "_" if is_dir else rel):
                others.append(shown)
            elif is_dir:
                walk(child)

    walk(target)
    return marks, others


def _file_in_way(path: Path):
    """The file standing where path or one of the folders above it should be, or None."""
    for p in (path, *path.parents):
        if p.exists():
            return None if p.is_dir() else p
    return None


def _refusal(skill_name: str, home: Path, source=None, probe=True):
    """Why deploying skill_name into home would harm something, or None when it is safe. probe: also try
    one empty folder where the skill's folder would be made (asked once, before anything is built)."""
    blocked = _file_in_way(home)
    if blocked:
        return f"{home} is not a folder" if blocked == home else f"{blocked} is a file, so {home} cannot be made"
    target = home / skill_name
    if _is_link(target):
        return f"{target} is a link; deploy to the folder it points at instead"
    if target.exists() and not target.is_dir():
        return f"{target} is a file, not a skill folder"
    if probe and not target.exists():
        # The skill's folder is new here: a home, or the nearest folder above a home not made yet, that takes
        # no new folder from this user (C:\Program Files, an ACL deny) is a refusal now, before anything is
        # built, not after both archives are written. One empty probe folder, made with O_EXCL and removed at
        # once; one that cannot be removed is named, never left unmentioned in the user's skills home.
        where = home
        while not where.exists() and where.parent != where:
            where = where.parent
        if not where.is_dir():  # the walk reached a root that is not there: a missing drive, an absent share
            return f"{home} could not be made: no folder above it exists ({where} is not there)"
        try:
            made = _fresh(where, ".probe-", "", directory=True)
        except OSError as e:
            if where == home:
                return (f"{home} takes no new folder from this user ({e.strerror or e}); choose a skills home "
                        "you may write to")
            return (f"{home} could not be made: {where} takes no new folder from this user ({e.strerror or e}); "
                    "choose a skills home you may write to")
        try:
            made.rmdir()
        except OSError as e:
            _say(f"⚠️ {made} is an empty folder this run made to test the skills home and could not remove "
                 f"({e.strerror or e}); delete it")
    # A skill developed in place under its skills home is the very folder being
    # packaged: replacing it would delete everything the archive leaves out.
    if source is not None and (_inside(target, source) or _inside(source, target)):
        return f"{target} is the folder being packaged; deploy to another skills home"
    # Replace only what is absent, empty, or an installed copy of this same skill:
    # one wrong --deploy argument must never empty somebody's other files.
    try:
        if target.is_dir() and any(not (c.name.startswith(".old-") or _is_junk(c.name)) for c in target.iterdir()):
            existing = _skill_name_in(target)
            if existing != skill_name:
                held = f"holds the skill '{existing}'" if existing else "holds files that are not a skill (no SKILL.md)"
                return f"{target} {held}, not '{skill_name}'"
            kept = _left_out(target, skill_name)[0]
            if kept:
                shown = ", ".join(kept[:8]) + (f" and {len(kept) - 8} more" if len(kept) > 8 else "")
                return (f"{target} holds {shown}, which the package leaves out: it is a working copy, and "
                        "replacing it would delete them; deploy to a skills home of installed copies")
    except OSError as e:  # its SKILL.md held with no share mode, a folder in it that cannot be listed
        return (f"{e.filename or target} could not be read ({e.strerror or e}); close the program holding it open, "
                "or check its permissions")
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
    why = _refusal(skill_name, home, source, probe=False)  # main() probed before building; mkdir below says the rest
    if why:
        raise RuntimeError(f"{why}; nothing changed")
    target = home / skill_name
    created = not target.exists()
    others = _left_out(target, skill_name)[1] if target.is_dir() else []
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"{target} could not be made ({e.strerror or e}); nothing changed") from e
    # An old copy an earlier deploy could not remove goes now (a read-only flag is cleared), or, still
    # in use, stays where it is: it is never moved inside the next one.
    stale = []
    for child in sorted(target.iterdir()):
        if child.name.startswith(".old-") and child.is_dir() and not _is_link(child):
            try:
                _remove(child)
            except OSError:
                stale.append(child)
    # Move the old copy aside inside the folder, unpack, then drop it: the
    # replacement lands whole, or every old file goes back where it was.
    try:
        aside = _fresh(target, ".old-", "", directory=True)
    except OSError as e:  # the installed copy takes no new file from this user: at once, not 2**31 retries
        raise RuntimeError(f"{target} could not be replaced ({e.strerror or e}: this user may not add files to it); "
                           "nothing changed") from e
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
            raise RuntimeError(f"{target} could not be replaced ({e.strerror or e}), and putting the old copy back "
                               f"failed ({e2.strerror or e2}); the old files are in {aside}") from e2
        raise RuntimeError(f"{target} could not be replaced ({e.strerror or e}); the old copy is back, nothing "
                           "changed") from e
    try:
        _remove(aside)
    except OSError as e:
        if moved:
            _say(f"⚠️ Deployed, but the old copy could not be removed ({e.strerror or e}); delete {aside}")
        else:  # a first deploy moved nothing aside: the folder is empty, and the reason is not a file in use
            _say(f"⚠️ Deployed, but the empty folder {aside} could not be removed ({e.strerror or e}); delete it")
    for s in stale:
        _say(f"⚠️ {s} is an old copy from an earlier deploy that could not be removed (still in use); "
             "delete it when it is free")
    if others:
        _say(f"ℹ️ Replaced, not carried over (the package leaves them out): {', '.join(others)}")
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
    # It names the .zip: no separator, nothing odd, no trailing dot or dash (good-skill-v1.0..zip), and short
    # enough for any file system (a 240-character version failed as "Invalid argument" on the output folder).
    if not re.fullmatch(r"[0-9A-Za-z](?:[0-9A-Za-z.\-]*[0-9A-Za-z])?", args.version) or len(args.version) > 64:
        _say(f"❌ --version takes digits, letters, dots and dashes, starting and ending with a digit or letter, at most "
             f"64 characters (1.0, 2.1-rc1); got {args.version[:70]!r}"
             f"{f' ({len(args.version)} characters)' if len(args.version) > 64 else ''}. Nothing packaged.")
        return 1

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
            if _inside(out, skill_path):  # the path given loops back into the skill through a link: beside its real folder
                out = skill_path.resolve().parent
    else:
        out = Path(args.output).resolve()
        if _inside(out, skill_path):
            _say(f"❌ --output {out} is inside the skill folder, so the archives would pack themselves; "
                 f"write them outside it, e.g. --output {skill_path.parent / 'dist'}. Nothing packaged.")
            return 1
        blocked = _file_in_way(out)
        if blocked:
            _say(f"❌ --output {out}: {blocked} is a file, not a folder. Nothing packaged.")
            return 1
    home = Path(args.deploy).expanduser().resolve() if args.deploy else None
    if home is not None and _inside(out, home / skill_path.name):
        _say(f"❌ --output {out} is inside the deploy target {home / skill_path.name}, which the deploy "
             f"replaces; write the archives elsewhere. Nothing packaged.")
        return 1
    if home is not None:  # asked before anything is built; deploy() asks again at the moment it acts
        why = _refusal(skill_path.name, home, source=skill_path)
        if why:
            _say(f"❌ Deploy refused: {why}. Nothing packaged.")
            return 1

    errors, warnings = _V.check(skill_path, out=out)
    for e in errors:
        _say(f"❌ {e}")
    for w in warnings:
        _say(f"⚠️ {w}")
    if errors or (args.strict and warnings):
        _say("❌ Validation failed; nothing packaged.")
        return 1
    _say(f"✅ Valid ({len(warnings)} warning(s))")

    name = skill_path.name
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as e:  # a name this system rejects, a drive that does not exist
        _say(f"❌ --output {out} could not be made ({e.strerror or e}); give --output a folder this system can "
             f"create. Nothing packaged.")
        return 1
    skill_file = out / f"{name}.skill"
    zip_file = out / f"{name}-v{args.version}.zip"
    for target in (skill_file, zip_file):  # an earlier archive left read-only or held open, or a folder at its name
        why = _unwritable(target)
        if why:
            _say(f"❌ {target} could not be written ({why[0]}); {why[1]}. Nothing changed.")
            return 1
    try:
        count = build_archives(skill_path, skill_file, zip_file)
    except ReadFailed as e:
        _say(f"❌ {e.filename} could not be read ({e.strerror}); close the program holding it open, or check its "
             f"permissions, and run again. Nothing changed.")
        return 1
    except RuntimeError as e:  # the earlier pair could not be put back: the message says where it is
        _say(f"❌ {e}")
        return 1
    except OSError as e:  # a hold the probe could not see, a folder that takes no new file, a full disk
        _say(f"❌ {_write_failure(e, out)} Nothing changed.")
        return 1
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
    _say("   .skill → upload where a host installs skills from an archive (or open the presented file card)")
    _say(f"   .zip   → keep; extract it into your agent's skills folder so it lands as <skills-folder>/{name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
