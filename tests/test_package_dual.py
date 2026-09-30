"""
Tests for sc2/scripts/package_dual.py — Skillshaper (sc2) v1.4 | standard library only
tests/test_package_dual.py | Created: 2026-09-30 03:55 ET
Updated: 2026-09-30 14:08 ET — SeventhReview: a folder that takes no new file (spun for hours), --version, a folder at an
archive's name, a full disk, a held SKILL.md in the installed copy, a file dated before 1980, an
unlistable folder, a double failure while landing; each failed before its fix.
Updated: 2026-09-30 14:46 ET — EighthReview: a file dated outside what the zip format or localtime holds, named once for all
such files; a skills home that takes no new folder, refused before anything is built; a --version that would name
the .zip badly; each failed before its fix. The READONLY guard's docstring says it is a guard, not a failed-first test.
Updated: 2026-09-30 15:37 ET — NinthReview: a skills home under a folder that takes no new folder, the probe asked once and named
when it cannot be removed, a deploy failure's reason in words; the date lines' new form; each failed before its fix.

Run from the repository root:
    python -B -m unittest discover -s tests -v

Every fixture, archive and deploy target is built in a temporary folder;
nothing here touches a real skills home or the user's profile.
"""

import contextlib
import hashlib
import importlib.util
import io
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "sc2" / "scripts"


def _load(name):
    path = SCRIPTS / f"{name}.py"
    if not path.is_file():
        raise ImportError(f"{path} not found: the skill must live in {REPO / 'sc2'} (sc2/SKILL.md, sc2/scripts/)")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


package_dual = _load("package_dual")

GOOD_MD = "---\nname: {name}\ndescription: Does a thing. Use when asked for the thing.\n---\n\n# Body\n\n{body}\n"


def make_skill(root, name="good-skill", body="Nothing to see.", files=None, crlf=False):
    """A minimal valid skill folder under root; files maps relative path to text or bytes."""
    skill = Path(root) / name
    skill.mkdir(parents=True, exist_ok=True)
    nl = "\r\n" if crlf else "\n"
    (skill / "SKILL.md").write_text(GOOD_MD.format(name=name, body=body), encoding="utf-8", newline=nl)
    for rel, content in (files or {}).items():
        p = skill / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8", newline=nl)
    return skill


def package(skill, out):
    """Build good-skill.skill for a fixture; returns the archive path."""
    archive = Path(out) / f"{skill.name}.skill"
    archive.parent.mkdir(parents=True, exist_ok=True)
    package_dual.create_zip(skill, archive)
    return archive


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_junction(link, real):
    """Windows junction (no admin needed); None when the platform cannot make one."""
    if os.name != "nt":
        return None
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(real)], capture_output=True, text=True)
    return link if r.returncode == 0 and link.exists() else None


def make_symlink(link, real):
    """A folder symlink; None where this account may not make one (Windows without Developer Mode)."""
    try:
        os.symlink(real, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        return None
    return link


@contextlib.contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def entries(archive):
    with zipfile.ZipFile(archive) as zf:
        return sorted(zf.namelist())


def names_in(folder):
    """Every file under folder as relative posix paths; a link is listed by name, never entered."""
    found = []
    for p in sorted(Path(folder).iterdir()):
        if p.is_dir() and not package_dual._is_link(p):
            found.extend(p.name + "/" + n for n in names_in(p))
        else:
            found.append(p.name)
    return found


@contextlib.contextmanager
def unreadable(path):
    """Hold path so that nothing can read it: on Windows a handle with no share mode (what a zip
    tool or a preview handler holds), elsewhere no permission bits (which root ignores)."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        k.CreateFileW.restype = wintypes.HANDLE
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        handle = k.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x80, None)
        if handle in (None, 0, 0xFFFFFFFFFFFFFFFF):
            raise unittest.SkipTest("no exclusive handle on this file")
        try:
            yield
        finally:
            k.CloseHandle(handle)
    else:
        if os.geteuid() == 0:
            raise unittest.SkipTest("root reads everything")
        mode = os.stat(path).st_mode
        os.chmod(path, 0)
        try:
            yield
        finally:
            os.chmod(path, mode)


class Deploy(unittest.TestCase):
    """High: deploy replaces a target only when it is absent, empty, or the same skill."""

    def _packaged(self, tmp):
        skill = make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(1)\n"})
        return package(skill, Path(tmp) / "out")

    def test_absent_target_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(target, home / "good-skill")
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "scripts" / "run.py").is_file())

    def test_empty_target_is_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            (home / "good-skill").mkdir(parents=True)
            package_dual.deploy(archive, "good-skill", home)
            self.assertTrue((home / "good-skill" / "SKILL.md").is_file())

    def test_same_skill_is_replaced_and_stale_file_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            old = make_skill(home, files={"references/stale.md": "old\n"})
            package_dual.deploy(archive, "good-skill", home)
            self.assertFalse((old / "references" / "stale.md").exists())
            self.assertTrue((old / "scripts" / "run.py").is_file())

    def test_other_skill_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            other = make_skill(home, "other-skill")
            (home / "good-skill").mkdir()
            (home / "good-skill" / "SKILL.md").write_text((other / "SKILL.md").read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(RuntimeError) as cm:
                package_dual.deploy(archive, "good-skill", home)
            self.assertIn("other-skill", str(cm.exception))
            self.assertFalse((home / "good-skill" / "scripts").exists())

    def test_non_skill_folder_with_files_is_refused_and_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = home / "good-skill"
            (target / "photos").mkdir(parents=True)
            (target / "important.txt").write_text("keep me\n", encoding="utf-8")
            (target / "photos" / "a.jpg").write_bytes(b"\xff\xd8\xff")
            with self.assertRaises(RuntimeError) as cm:
                package_dual.deploy(archive, "good-skill", home)
            self.assertIn("nothing changed", str(cm.exception))
            self.assertEqual((target / "important.txt").read_text(encoding="utf-8"), "keep me\n")
            self.assertEqual((target / "photos" / "a.jpg").read_bytes(), b"\xff\xd8\xff")
            self.assertFalse((target / "SKILL.md").exists())

    def test_file_target_is_refused_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            home.mkdir()
            (home / "good-skill").write_text("a file\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as cm:
                package_dual.deploy(archive, "good-skill", home)
            self.assertIn("nothing changed", str(cm.exception))
            self.assertEqual((home / "good-skill").read_text(encoding="utf-8"), "a file\n")

    def test_junction_target_is_refused_without_path_is_junction(self):
        """Medium: junction detection on 3.10/3.11, which have no Path.is_junction (simulated here)."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            home.mkdir()
            real = Path(tmp) / "real"
            real.mkdir()
            link = make_junction(home / "good-skill", real)
            if link is None:
                self.skipTest("no junction on this platform")
            owner = next((c for c in type(Path()).__mro__ if "is_junction" in vars(c)), None)
            saved = vars(owner)["is_junction"] if owner else None
            if owner:
                delattr(owner, "is_junction")
            try:
                with self.assertRaises(RuntimeError) as cm:
                    package_dual.deploy(archive, "good-skill", home)
            finally:
                if owner:
                    setattr(owner, "is_junction", saved)
            self.assertIn("link", str(cm.exception))
            self.assertEqual(list(real.iterdir()), [])

    def test_junction_target_is_refused_natively(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            home.mkdir()
            real = Path(tmp) / "real"
            real.mkdir()
            if make_junction(home / "good-skill", real) is None:
                self.skipTest("no junction on this platform")
            with self.assertRaises(RuntimeError):
                package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(list(real.iterdir()), [])

    def test_deploy_onto_its_own_source_is_refused_and_source_untouched(self):
        """High (second review): a skill developed in place under its skills home is its own deploy target."""
        files = {".env": "KEY=1\n", "evals/e1.md": "eval\n", "tests/t.py": "pass\n",
                 "scratch-workspace/notes.md": "notes\n", "scripts/run.py": "print(1)\n"}
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            skill = make_skill(home, files=files)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(Path(tmp) / "out"),
                                        "--deploy", str(home)])
            self.assertEqual(rc, 1, out.getvalue())
            self.assertIn("being packaged", out.getvalue())
            for rel in files:
                self.assertTrue((skill / rel).is_file(), rel)

    def test_junction_inside_the_target_is_removed_as_a_link(self):
        """Medium (second review): a junction child is a link, never a folder to empty."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files={"aaa-first.txt": "first\n", "references/old.md": "old\n"})
            real = Path(tmp) / "realA"
            real.mkdir()
            (real / "precious.txt").write_text("keep\n", encoding="utf-8")
            if make_junction(target / "zz-linked", real) is None:
                self.skipTest("no junction on this platform")
            package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()),
                             ["SKILL.md", "scripts/run.py"])
            self.assertFalse(os.path.lexists(target / "zz-linked"))
            self.assertEqual((real / "precious.txt").read_text(encoding="utf-8"), "keep\n")

    def test_a_failed_unpack_puts_the_old_copy_back(self):
        """Medium (second review): a replacement either lands whole or nothing changes."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files={"references/stale.md": "old\n", "scripts/run.py": "print(0)\n"})
            before = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob("*") if p.is_file()}
            real_copy, calls = package_dual.shutil.copyfileobj, []

            def fail_second(src, dst, *a):
                calls.append(1)
                if len(calls) == 2:
                    raise OSError("disk full (simulated)")
                return real_copy(src, dst, *a)

            package_dual.shutil.copyfileobj = fail_second
            try:
                with self.assertRaises(RuntimeError) as cm:
                    package_dual.deploy(archive, "good-skill", home)
            finally:
                package_dual.shutil.copyfileobj = real_copy
            self.assertIn("nothing changed", str(cm.exception))
            after = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob("*") if p.is_file()}
            self.assertEqual(after, before)

    def test_a_skills_home_that_is_a_file_is_refused_before_packaging(self):
        """Low (second review): a refusal, not a traceback, and no archives built for nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            home.write_text("a file\n", encoding="utf-8")
            out_dir = Path(tmp) / "out"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out_dir), "--deploy", str(home)])
            self.assertEqual(rc, 1, out.getvalue())
            self.assertIn("not a folder", out.getvalue())
            self.assertFalse(out_dir.exists())

    @unittest.skipIf(os.name == "nt", "Windows keeps no executable bit")
    def test_deployed_script_keeps_its_executable_bit(self):
        """Low (second review): the mode the archive records reaches the deployed copy."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files={"scripts/run.py": "#!/usr/bin/env python3\nprint(1)\n"})
            target = package_dual.deploy(package(skill, Path(tmp) / "out"), "good-skill", Path(tmp) / "home")
            self.assertTrue(os.stat(target / "scripts" / "run.py").st_mode & 0o100)
            self.assertFalse(os.stat(target / "SKILL.md").st_mode & 0o100)


class ThirdReview(unittest.TestCase):
    """The third review (f6ebd36): links inside the skill, a read-only old copy, a development copy as target."""

    def _packaged(self, tmp):
        return package(make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(1)\n"}), Path(tmp) / "out")

    def test_a_folder_symlink_inside_the_skill_is_packaged_like_a_junction(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared"
            (shared / "guide.md").parent.mkdir(parents=True)
            (shared / "guide.md").write_text("# Guide\n", encoding="utf-8")
            skill = make_skill(Path(tmp) / "src", body="Read references/guide.md.")
            if make_symlink(skill / "references", shared) is None:
                self.skipTest("no folder symlink on this account")
            self.assertIn("good-skill/references/guide.md", entries(package(skill, Path(tmp) / "out")))

    def test_a_link_back_into_the_skill_or_to_the_output_is_not_packed(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            out = Path(tmp) / "out"
            out.mkdir()
            if make_junction(skill / "loop", skill) is None or make_junction(skill / "shared", out) is None:
                self.skipTest("no junction on this platform")
            with contextlib.redirect_stdout(io.StringIO()):
                for _ in range(2):
                    self.assertEqual(package_dual.main([str(skill), "--version", "1.0", "--output", str(out)]), 0)
            self.assertEqual(entries(out / "good-skill.skill"), ["good-skill/SKILL.md"])

    def test_a_read_only_file_in_the_old_copy_is_replaced_with_nothing_left_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files={"references/locked.md": "old\n"})
            os.chmod(target / "references" / "locked.md", stat.S_IREAD)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()),
                             ["SKILL.md", "scripts/run.py"], out.getvalue())

    def test_an_old_copy_left_by_a_lock_is_not_nested_by_the_next_deploy(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home)
            make_skill(target / ".old-abc123", "good-skill")  # what a lock left behind, now free
            package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()),
                             ["SKILL.md", "scripts/run.py"])

    @unittest.skipUnless(os.name == "nt", "an open file blocks removal only on Windows")
    def test_an_old_copy_still_locked_stays_put_and_the_deploy_goes_ahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home)
            (target / ".old-abc123").mkdir()
            busy = open(target / ".old-abc123" / "busy.txt", "w", encoding="utf-8")
            try:
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    package_dual.deploy(archive, "good-skill", home)
                files = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
            finally:
                busy.close()
            self.assertEqual(files, [".old-abc123/busy.txt", "SKILL.md", "scripts/run.py"], out.getvalue())
            self.assertIn(".old-abc123", out.getvalue())

    def test_a_same_skill_target_holding_development_material_is_refused(self):
        dev = {".git/HEAD": "ref\n", ".env": "K=1\n", "evals/e1.md": "e\n", "tests/t.py": "pass\n",
               "scratch-workspace/notes.md": "n\n"}
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files=dev)
            with self.assertRaises(RuntimeError) as cm:
                package_dual.deploy(archive, "good-skill", home)
            for name in (".git", ".env", "evals", "tests", "scratch-workspace"):
                self.assertIn(name, str(cm.exception))
            for rel in dev:
                self.assertTrue((target / rel).is_file(), rel)

    def test_caches_in_an_installed_copy_do_not_block_its_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files={"scripts/__pycache__/run.cpython-312.pyc": b"\x00\x01"})
            package_dual.deploy(archive, "good-skill", home)
            self.assertFalse((target / "scripts" / "__pycache__").exists())

    def test_a_deploy_path_through_a_file_is_refused_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            (Path(tmp) / "h9").write_text("a file\n", encoding="utf-8")
            out_dir = Path(tmp) / "out"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out_dir),
                                        "--deploy", str(Path(tmp) / "h9" / "home")])
            self.assertEqual(rc, 1, out.getvalue())
            self.assertIn("is a file", out.getvalue())
            self.assertFalse(out_dir.exists())

    def test_packaging_from_inside_the_skill_writes_beside_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            out = io.StringIO()
            with chdir(skill), contextlib.redirect_stdout(out):
                rc = package_dual.main([".", "--version", "1.0"])
            self.assertEqual(rc, 0, out.getvalue())
            self.assertTrue((skill.parent / "good-skill.skill").is_file())
            self.assertEqual([p.name for p in skill.iterdir()], ["SKILL.md"])

    def test_text_without_a_listed_suffix_lands_with_lf(self):
        files = {"LICENSE": "Freeware\nline\n", "Makefile": "all:\n\techo\n", "references/notes": "a\nb\n",
                 "references/guide.rst": "Title\n=====\n", "scripts/tool.go": "package main\n"}
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files=files, crlf=True)
            with zipfile.ZipFile(package(skill, Path(tmp) / "out")) as zf:
                for rel in files:
                    self.assertNotIn(b"\r\n", zf.read("good-skill/" + rel), rel)


class FourthReview(unittest.TestCase):
    """The fourth review (1da47e9): archives beside the skill, upgrading older installs, and five edges."""

    def _packaged(self, tmp):
        return package(make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(1)\n"}), Path(tmp) / "out")

    def test_a_licence_linked_from_the_repo_root_survives_archives_written_beside_the_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill = make_skill(repo)
            (repo / "LICENSE").write_text("Freeware\n", encoding="utf-8")
            try:
                os.symlink(repo / "LICENSE", skill / "LICENSE")
                os.symlink(repo / "good-skill.skill", skill / "old.skill")  # a link to the archive itself
            except (OSError, NotImplementedError):
                self.skipTest("no file symlink on this account")
            (repo / "good-skill.skill").write_bytes(b"PK old archive")
            out = io.StringIO()
            with chdir(skill), contextlib.redirect_stdout(out):
                rc = package_dual.main([".", "--version", "1.0"])
            self.assertEqual(rc, 0, out.getvalue())
            self.assertEqual(entries(repo / "good-skill.skill"), ["good-skill/LICENSE", "good-skill/SKILL.md"])

    def test_an_install_holding_a_dotfile_an_older_packager_shipped_is_upgraded_and_named(self):
        leftovers = {".gitignore": "*.pyc\n", "._SKILL.md": b"\x00\x05\x16\x07", "__MACOSX/._SKILL.md": b"\x00",
                     ".mypy_cache/x.json": "{}\n", ".ruff_cache/x": "r\n"}
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files=leftovers)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()),
                             ["SKILL.md", "scripts/run.py"])
            self.assertIn(".gitignore", out.getvalue())

    def test_a_virtual_environment_marks_a_working_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files={".venv/pyvenv.cfg": "home = x\n"})
            with self.assertRaises(RuntimeError) as cm:
                package_dual.deploy(archive, "good-skill", home)
            self.assertIn(".venv", str(cm.exception))
            self.assertTrue((target / ".venv" / "pyvenv.cfg").is_file())

    def test_a_folder_holding_only_junk_counts_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            (home / "good-skill").mkdir(parents=True)
            (home / "good-skill" / "Thumbs.db").write_bytes(b"\x00junk")
            package_dual.deploy(archive, "good-skill", home)
            self.assertTrue((home / "good-skill" / "SKILL.md").is_file())

    @unittest.skipUnless(os.name == "nt", "the READONLY attribute on a folder is a Windows matter")
    def test_a_read_only_folder_in_the_old_copy_leaves_nothing_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = self._packaged(tmp)
            home = Path(tmp) / "home"
            target = make_skill(home, files={"references/ro/x.md": "x\n"})
            subprocess.run(["attrib", "+R", str(target / "references")], check=True, capture_output=True)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                package_dual.deploy(archive, "good-skill", home)
            self.assertEqual(sorted(c.name for c in target.iterdir()), ["SKILL.md", "scripts"], out.getvalue())
            self.assertNotIn("⚠️", out.getvalue())

    def test_an_output_that_is_a_file_is_refused_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            afile = Path(tmp) / "afile"
            afile.write_text("x\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(afile)])
            self.assertEqual(rc, 1, out.getvalue())
            self.assertIn("is a file", out.getvalue())
            self.assertNotIn("Valid", out.getvalue())

    def test_a_script_with_a_binary_payload_is_stored_byte_for_byte_and_executable(self):
        shar = b"#!/bin/sh\nsed '1,/^exit$/d' \"$0\" | tar xz\nexit\n\x1f\x8b\x08\x00\r\n\x00\xff\r\n"
        long_head = b"#!/usr/bin/env python3\n" + b"# text\n" * 1300 + b"\x00\x01\x02\r\n"
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files={"scripts/shar.sh": shar, "scripts/tool": long_head})
            with zipfile.ZipFile(package(skill, Path(tmp) / "out")) as zf:
                self.assertEqual(zf.read("good-skill/scripts/shar.sh"), shar)
                self.assertEqual(zf.read("good-skill/scripts/tool"), long_head)
                self.assertEqual(zf.getinfo("good-skill/scripts/shar.sh").external_attr >> 16 & 0o777, 0o755)

    def test_what_a_mac_or_windows_leaves_in_a_folder_is_not_packaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(1)\n",
                                                         "scripts/desktop.ini": "[.ShellClassInfo]\n",
                                                         "scripts/__MACOSX/notes.txt": "x\n"})
            self.assertEqual(entries(package(skill, Path(tmp) / "out")),
                             ["good-skill/SKILL.md", "good-skill/scripts/run.py"])


class FifthReview(unittest.TestCase):
    """The fifth review (3814807): an archive that cannot be written, an output inside the deploy target,
    .envrc, and a skill reached through a link whose archives land beside the link."""

    def test_a_read_only_archive_in_the_output_is_refused_with_a_message(self):
        for stale in ("good-skill.skill", "good-skill-v1.0.zip"):
            with self.subTest(stale), tempfile.TemporaryDirectory() as tmp:
                skill = make_skill(Path(tmp) / "src")
                dist = Path(tmp) / "dist"
                dist.mkdir()
                (dist / stale).write_bytes(b"PK old")
                os.chmod(dist / stale, stat.S_IREAD)
                out = io.StringIO()
                try:
                    with contextlib.redirect_stdout(out):
                        rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(dist)])
                finally:
                    os.chmod(dist / stale, stat.S_IWRITE | stat.S_IREAD)
                self.assertEqual(rc, 1, out.getvalue())
                self.assertIn("could not be written", out.getvalue())

    def test_an_output_inside_the_deploy_target_is_refused_before_anything_is_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(home / "good-skill" / "dist"),
                                        "--deploy", str(home)])
            self.assertEqual(rc, 1, out.getvalue())
            self.assertIn("inside the deploy target", out.getvalue())
            self.assertFalse(home.exists())

    def test_envrc_marks_a_working_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = package(make_skill(Path(tmp) / "src"), Path(tmp) / "out")
            home = Path(tmp) / "home"
            target = make_skill(home, files={".envrc": "export KEY=1\n"})
            with self.assertRaises(RuntimeError) as cm:
                package_dual.deploy(archive, "good-skill", home)
            self.assertIn(".envrc", str(cm.exception))
            self.assertTrue((target / ".envrc").is_file())

    def test_a_licence_beside_a_skill_reached_through_a_link_ships(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, work = Path(tmp) / "repo", Path(tmp) / "work"
            real = make_skill(repo)
            work.mkdir()
            (work / "LICENSE").write_text("Freeware\n", encoding="utf-8")
            if not (make_junction(work / "good-skill", real) or make_symlink(work / "good-skill", real)):
                self.skipTest("no folder link on this platform")
            try:
                os.symlink(work / "LICENSE", real / "LICENSE")
            except (OSError, NotImplementedError):
                self.skipTest("no file symlink on this account")
            out = io.StringIO()
            with chdir(work), contextlib.redirect_stdout(out):
                rc = package_dual.main(["good-skill", "--version", "1.0"])
            self.assertEqual(rc, 0, out.getvalue())
            self.assertEqual(entries(work / "good-skill.skill"), ["good-skill/LICENSE", "good-skill/SKILL.md"])


class SixthReview(unittest.TestCase):
    """The sixth review (42503ab): a failed run changes neither archive, a message for every failure
    the run can meet (a file that cannot be read, an archive that cannot be replaced, an --output that
    cannot be made), and a skill reached through a link that loops back into it never packs itself."""

    def _first_run(self, tmp):
        """A packaged skill with a root-level file the validator never reads; returns (skill, out, archives before)."""
        skill = make_skill(Path(tmp) / "src", body="Run scripts/a.py.", files={"scripts/a.py": "print(1)\n", "zz.bin": b"\x00\x01"})
        out = Path(tmp) / "out"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(package_dual.main([str(skill), "--version", "1.0", "--output", str(out)]), 0)
        (skill / "scripts" / "b.py").write_text("print(2)\n", encoding="utf-8")
        (skill / "SKILL.md").write_text(GOOD_MD.format(name="good-skill", body="Run scripts/a.py and scripts/b.py."),
                                        encoding="utf-8", newline="\n")
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        self.assertEqual(sorted(before), ["good-skill-v1.0.zip", "good-skill.skill"])
        return skill, out, before

    def test_a_source_file_that_cannot_be_read_is_named_and_neither_archive_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill, out, before = self._first_run(tmp)
            printed = io.StringIO()
            with unreadable(skill / "zz.bin"), contextlib.redirect_stdout(printed):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out), "--deploy", str(Path(tmp) / "home")])
            self.assertEqual(rc, 1, printed.getvalue())
            self.assertRegex(printed.getvalue(), r"zz\.bin could not be read \(.+\); ")
            self.assertNotIn("could not be written", printed.getvalue())
            self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)
            self.assertFalse((Path(tmp) / "home").exists())

    def test_a_bundled_file_that_cannot_be_read_stops_the_run_before_the_output_is_made(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", body="See references/z.md.", files={"references/z.md": "z\n"})
            out = Path(tmp) / "out"
            printed = io.StringIO()
            with unreadable(skill / "references" / "z.md"), contextlib.redirect_stdout(printed):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
            self.assertEqual(rc, 1, printed.getvalue())
            self.assertRegex(printed.getvalue(), r"references/z\.md could not be read \(.+\); ")
            self.assertFalse(out.exists())

    def test_an_output_that_cannot_be_made_is_a_message(self):
        bad = [Path("x" * 300)]  # a component longer than any file system allows
        if os.name == "nt":
            bad.append(Path("out<x"))
            missing = next((f"{d}:\\" for d in "ZYXWVUTSRQ" if not os.path.exists(f"{d}:\\")), None)
            if missing:
                bad.append(Path(missing, "nowhere", "out"))
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            for output in bad:
                with self.subTest(str(output)):
                    output = output if output.is_absolute() else Path(tmp) / output
                    printed = io.StringIO()
                    with contextlib.redirect_stdout(printed):
                        rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(output)])
                    self.assertEqual(rc, 1, printed.getvalue())
                    self.assertRegex(printed.getvalue(), r"could not be made \(.+\); ")

    def test_a_skill_reached_through_a_link_that_loops_back_into_it_never_packs_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/run.py.", files={"scripts/run.py": "print(1)\n"})
            (skill / "dev").mkdir()
            loop = skill / "dev" / "good-skill"
            if not (make_junction(loop, skill) or make_symlink(loop, skill)):
                self.skipTest("no folder link on this platform")
            for cwd, given in ((skill / "dev", "good-skill"), (loop, ".")):
                with self.subTest(given):
                    printed = io.StringIO()
                    with chdir(cwd), contextlib.redirect_stdout(printed):
                        rc = package_dual.main([given, "--version", "1.0"])
                    self.assertEqual(rc, 0, printed.getvalue())
                    self.assertEqual(sorted(names_in(skill)), ["SKILL.md", "dev/good-skill", "scripts/run.py"])
                    self.assertEqual(entries(Path(tmp) / "good-skill.skill"), ["good-skill/SKILL.md", "good-skill/scripts/run.py"])

    def test_an_archive_that_cannot_be_replaced_leaves_the_earlier_pair_in_place(self):
        """Either archive held while the pair lands (a hold blocks every move of the held file and every
        move onto it, on any platform here by simulation): the first is put back, nothing is left beside them."""
        for held in ("good-skill.skill", "good-skill-v1.0.zip"):
            with self.subTest(held), tempfile.TemporaryDirectory() as tmp:
                skill, out, before = self._first_run(tmp)
                real_replace, calls = package_dual.os.replace, []

                def fail_on_target(src, dst, *a, _held=held):
                    calls.append((Path(src).name, Path(dst).name))
                    if Path(src).name == _held or (Path(dst).name == _held and Path(dst).exists()):
                        raise PermissionError(13, "Permission denied (simulated)", str(src), None, str(dst))
                    return real_replace(src, dst, *a)

                package_dual.os.replace = fail_on_target
                printed = io.StringIO()
                try:
                    with contextlib.redirect_stdout(printed):
                        rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
                finally:
                    package_dual.os.replace = real_replace
                self.assertEqual(rc, 1, printed.getvalue())
                self.assertRegex(printed.getvalue(), rf"{held.replace('.', chr(92) + '.')} could not be written \(.+\); ")
                self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before, calls)

    @unittest.skipUnless(os.name == "nt", "a shared-read handle blocks a rename only on Windows")
    def test_an_archive_held_open_for_reading_is_refused_and_neither_archive_changes(self):
        for held in ("good-skill.skill", "good-skill-v1.0.zip"):
            with self.subTest(held), tempfile.TemporaryDirectory() as tmp:
                skill, out, before = self._first_run(tmp)
                printed = io.StringIO()
                with open(out / held, "rb"), contextlib.redirect_stdout(printed):
                    rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
                self.assertEqual(rc, 1, printed.getvalue())
                self.assertIn("could not be written", printed.getvalue())
                self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)


@contextlib.contextmanager
def no_new_files(folder):
    """A folder that exists but takes no new file from this user: on Windows an ACL deny of WD and AD (what
    C:\\ or C:\\Program Files gives a non-elevated user; os.access still says writable, since it reads only
    the READONLY attribute), elsewhere no write bit (which root ignores). The deny is lifted afterwards."""
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        r = subprocess.run(["icacls", str(folder), "/deny", f"{user}:(WD,AD)"], capture_output=True, text=True)
        if r.returncode != 0:
            raise unittest.SkipTest("icacls could not deny this folder")
        try:
            yield
        finally:
            subprocess.run(["icacls", str(folder), "/remove:d", user], capture_output=True, text=True)
    else:
        if os.geteuid() == 0:
            raise unittest.SkipTest("root writes everywhere")
        mode = os.stat(folder).st_mode
        os.chmod(folder, 0o555)
        try:
            yield
        finally:
            os.chmod(folder, mode)


@contextlib.contextmanager
def unlistable(folder):
    """A folder this user may not list: on Windows an ACL deny of RD, elsewhere no permission bits."""
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        r = subprocess.run(["icacls", str(folder), "/deny", f"{user}:(RD)"], capture_output=True, text=True)
        if r.returncode != 0:
            raise unittest.SkipTest("icacls could not deny this folder")
        try:
            yield
        finally:
            subprocess.run(["icacls", str(folder), "/remove:d", user], capture_output=True, text=True)
    else:
        if os.geteuid() == 0:
            raise unittest.SkipTest("root lists everything")
        mode = os.stat(folder).st_mode
        os.chmod(folder, 0)
        try:
            yield
        finally:
            os.chmod(folder, mode)


class SeventhReview(unittest.TestCase):
    """The seventh review (eff4bb1): an output or an installed copy that takes no new file, the --version
    value, a folder at an archive's name, a full disk, a held SKILL.md in the installed copy, a file dated
    before 1980, a folder that cannot be listed, and what a double failure while landing names."""

    def _first_run(self, tmp):
        """A packaged skill, then a change to it; returns (skill, out, archives before)."""
        skill = make_skill(Path(tmp) / "src", body="Run scripts/a.py.", files={"scripts/a.py": "print(1)\n"})
        out = Path(tmp) / "out"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(package_dual.main([str(skill), "--version", "1.0", "--output", str(out)]), 0)
        (skill / "scripts" / "b.py").write_text("print(2)\n", encoding="utf-8")
        (skill / "SKILL.md").write_text(GOOD_MD.format(name="good-skill", body="Run scripts/a.py and scripts/b.py."),
                                        encoding="utf-8", newline="\n")
        return skill, out, {p.name: p.read_bytes() for p in out.iterdir()}

    def _run(self, *args, timeout=20):
        """The packager from the command line, killed after timeout seconds: a run that spins is a failure, not a hang."""
        cmd = [sys.executable, "-B", str(SCRIPTS / "package_dual.py"), *map(str, args)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail(f"still running after {timeout} s: {' '.join(cmd)}")
        return r.returncode, r.stdout + r.stderr

    def test_an_output_this_user_may_not_add_files_to_is_one_message_at_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            out = Path(tmp) / "out"
            out.mkdir()
            with no_new_files(out):
                started = time.monotonic()
                rc, printed = self._run(skill, "--version", "1.0", "--output", out)
                took = time.monotonic() - started
            self.assertEqual(rc, 1, printed)
            self.assertLess(took, 10, printed)
            self.assertNotIn("Traceback", printed)
            self.assertIn(str(out), printed)
            self.assertRegex(printed, r"takes no new file from this user \(.+\); choose an --output")
            self.assertEqual(list(out.iterdir()), [])

    def test_an_installed_copy_this_user_may_not_add_files_to_is_one_message_at_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(2)\n"})
            home = Path(tmp) / "home"
            target = make_skill(home, files={"scripts/run.py": "print(1)\n"})
            before = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob("*") if p.is_file()}
            with no_new_files(target):
                started = time.monotonic()
                rc, printed = self._run(skill, "--version", "1.0", "--output", Path(tmp) / "out", "--deploy", home)
                took = time.monotonic() - started
            self.assertEqual(rc, 1, printed)
            self.assertLess(took, 10, printed)
            self.assertNotIn("Traceback", printed)
            self.assertRegex(printed, r"Deploy refused: .+good-skill could not be replaced \(.+\)")
            self.assertEqual({p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob("*") if p.is_file()}, before)

    @unittest.skipUnless(os.name == "nt", "the READONLY attribute on a folder is a Windows matter")
    def test_a_read_only_output_folder_neither_spins_nor_tracebacks(self):
        """A guard, not a test that failed first: Windows lets a file be made in a folder carrying the READONLY
        attribute, though os.access says no, and the O_EXCL change must keep taking such a folder. It passed
        against eff4bb1's packager too (the eighth review, finding 11)."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            out = Path(tmp) / "out"
            out.mkdir()
            subprocess.run(["attrib", "+R", str(out)], check=True, capture_output=True)
            try:
                started = time.monotonic()
                rc, printed = self._run(skill, "--version", "1.0", "--output", out)
                took = time.monotonic() - started
            finally:
                subprocess.run(["attrib", "-R", str(out)], capture_output=True)
            self.assertLess(took, 10, printed)
            self.assertNotIn("Traceback", printed)
            self.assertEqual(rc, 0, printed)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["good-skill-v1.0.zip", "good-skill.skill"])

    def test_a_version_that_is_not_digits_letters_dots_and_dashes_is_refused_before_anything_is_built(self):
        bad = ["1.0/x", "", "a*b", " 1.0", "1.0 ", "1 0", "..\\..\\evil", "/../../pwn", "1.0\\x", ".hidden", "-1"]
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            out = Path(tmp) / "out"
            for version in bad:
                with self.subTest(repr(version)):
                    printed = io.StringIO()
                    with contextlib.redirect_stdout(printed):
                        rc = package_dual.main([str(skill), "--version", version, "--output", str(out)])
                    self.assertEqual(rc, 1, printed.getvalue())
                    self.assertIn("--version takes digits, letters, dots and dashes", printed.getvalue())
                    self.assertNotIn("Valid", printed.getvalue())
                    self.assertFalse(out.exists())
                    self.assertEqual([p.name for p in Path(tmp).iterdir()], ["src"])  # nothing written anywhere else
            for version in ("1.0", "2026.09.30", "1.0-rc1", "v2"):
                with self.subTest(version):
                    with contextlib.redirect_stdout(io.StringIO()):
                        rc = package_dual.main([str(skill), "--version", version, "--output", str(out)])
                    self.assertEqual(rc, 0)
                    self.assertTrue((out / f"good-skill-v{version}.zip").is_file())

    def test_a_folder_at_an_archives_name_is_named_as_a_folder(self):
        for which in ("good-skill.skill", "good-skill-v1.0.zip"):
            with self.subTest(which), tempfile.TemporaryDirectory() as tmp:
                skill = make_skill(Path(tmp) / "src")
                out = Path(tmp) / "out"
                (out / which).mkdir(parents=True)
                (out / which / "keep.txt").write_text("mine\n", encoding="utf-8")
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
                self.assertEqual(rc, 1, printed.getvalue())
                self.assertIn(f"{out / which} could not be written (a folder stands at this name)", printed.getvalue())
                self.assertNotIn("unlock or close", printed.getvalue())
                self.assertEqual([p.name for p in out.iterdir()], [which])
                self.assertEqual((out / which / "keep.txt").read_text(encoding="utf-8"), "mine\n")

    def test_a_full_disk_names_the_archive_and_says_to_free_space(self):
        import errno
        full = OSError(errno.ENOSPC, "No space left on device")

        def at_write(*a, **k):
            raise full

        def at_copy(src, dst, *a, **k):
            raise OSError(errno.ENOSPC, "No space left on device", str(dst))

        points = (("good-skill.skill", "zipfile.ZipFile.writestr", at_write), ("good-skill-v1.0.zip", "shutil.copyfile", at_copy),
                  ("good-skill.skill", "os.open", at_write))
        for named, dotted, fake in points:
            with self.subTest(dotted), tempfile.TemporaryDirectory() as tmp:
                skill, out, before = self._first_run(tmp)
                owner, attr = dotted.rsplit(".", 1)
                holder = package_dual
                for part in owner.split("."):
                    holder = getattr(holder, part)
                real = getattr(holder, attr)
                setattr(holder, attr, fake)
                printed = io.StringIO()
                try:
                    with contextlib.redirect_stdout(printed):
                        rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
                finally:
                    setattr(holder, attr, real)
                self.assertEqual(rc, 1, printed.getvalue())
                self.assertIn(f"{out / named} could not be written (No space left on device); free some space", printed.getvalue())
                self.assertNotIn(".part", printed.getvalue())
                self.assertNotIn("unlock or close", printed.getvalue())
                self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)

    def test_a_held_skill_md_in_the_installed_copy_is_a_refusal_before_anything_is_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            target = make_skill(home)
            out = Path(tmp) / "out"
            printed = io.StringIO()
            with unreadable(target / "SKILL.md"), contextlib.redirect_stdout(printed):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out), "--deploy", str(home)])
            self.assertEqual(rc, 1, printed.getvalue())
            self.assertRegex(printed.getvalue(), r"Deploy refused: .+SKILL\.md could not be read \(.+\)")
            self.assertFalse(out.exists())
            self.assertTrue((target / "SKILL.md").is_file())

    def test_a_file_dated_before_1980_is_packaged_dated_1980_and_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", body="See references/old.md.", files={"references/old.md": "old\n"})
            os.utime(skill / "references" / "old.md", (0, 0))
            out = Path(tmp) / "out"
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
            self.assertEqual(rc, 0, printed.getvalue())
            self.assertRegex(printed.getvalue(), r"1 file is dated before the zip format's 1980 floor: references/old\.md "
                                                 r"dated (19(69|70)-\d\d-\d\d|before 1970); its entry is dated 1980-01-01")
            with zipfile.ZipFile(out / "good-skill.skill") as zf:
                self.assertEqual(zf.getinfo("good-skill/references/old.md").date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(zf.read("good-skill/references/old.md"), b"old\n")

    def test_a_folder_that_cannot_be_listed_is_a_read_failure_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", body="See references/guide.md.",
                               files={"references/guide.md": "g\n", "references/secret/x.md": "x\n"})
            out = Path(tmp) / "out"
            with unlistable(skill / "references" / "secret"):
                with self.assertRaises(package_dual.ReadFailed) as cm:
                    package(skill, out)
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(Path(tmp) / "out2")])
            self.assertEqual(Path(cm.exception.filename), skill / "references" / "secret")
            self.assertEqual(rc, 1, printed.getvalue())
            self.assertRegex(printed.getvalue(), r"references/secret/ could not be listed \(.+\)")
            self.assertFalse((Path(tmp) / "out2").exists())

    def test_a_double_failure_while_landing_names_every_file_that_no_longer_matches(self):
        """The .zip cannot be set aside, and by then a hold has arrived on the .skill's aside and on the new
        .skill at its name: the message names both, the old .zip beside them, and what to do."""
        with tempfile.TemporaryDirectory() as tmp:
            skill, out, before = self._first_run(tmp)
            real_replace, real_unlink = package_dual.os.replace, Path.unlink

            def replace(src, dst, *a):
                s, d = Path(src), Path(dst)
                if (s.name == "good-skill-v1.0.zip" and d.suffix == ".old") or (s.suffix == ".old" and d.name == "good-skill.skill"):
                    raise PermissionError(13, "Permission denied (simulated)", str(src), None, str(dst))
                return real_replace(src, dst, *a)

            def unlink(self, missing_ok=False):
                if self.name == "good-skill.skill":
                    raise PermissionError(13, "Permission denied (simulated)", str(self))
                return real_unlink(self, missing_ok=missing_ok)

            package_dual.os.replace, Path.unlink = replace, unlink
            printed = io.StringIO()
            try:
                with contextlib.redirect_stdout(printed):
                    rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
            finally:
                package_dual.os.replace, Path.unlink = real_replace, real_unlink
            self.assertEqual(rc, 1, printed.getvalue())
            left = sorted(p.name for p in out.iterdir())
            aside = [n for n in left if n.endswith(".old")]
            self.assertEqual(len(aside), 1, left)
            self.assertEqual(left, ["good-skill-v1.0.zip", "good-skill.skill", aside[0]])
            self.assertEqual((out / "good-skill-v1.0.zip").read_bytes(), before["good-skill-v1.0.zip"])
            self.assertEqual((out / aside[0]).read_bytes(), before["good-skill.skill"])
            self.assertNotEqual((out / "good-skill.skill").read_bytes(), before["good-skill.skill"])
            message = printed.getvalue()
            self.assertIn(str(out / aside[0]), message)
            self.assertRegex(message, r"the earlier good-skill\.skill is at .+\.old and the new one stands at ")
            self.assertIn(str(out / "good-skill.skill"), message)
            self.assertRegex(message, r"(?i)delete .*rename .*\.old")


@contextlib.contextmanager
def no_new_folders(folder):
    """A folder that exists but takes no new folder from this user: on Windows an ACL deny of AD (what
    C:\\Program Files gives a non-elevated user), elsewhere no write bit. The deny is lifted afterwards."""
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        r = subprocess.run(["icacls", str(folder), "/deny", f"{user}:(AD)"], capture_output=True, text=True)
        if r.returncode != 0:
            raise unittest.SkipTest("icacls could not deny this folder")
        try:
            yield
        finally:
            subprocess.run(["icacls", str(folder), "/remove:d", user], capture_output=True, text=True)
    else:
        if os.geteuid() == 0:
            raise unittest.SkipTest("root writes everywhere")
        mode = os.stat(folder).st_mode
        os.chmod(folder, 0o555)
        try:
            yield
        finally:
            os.chmod(folder, mode)


class EighthReview(unittest.TestCase):
    """The eighth review (0bb76bf): a file whose date the zip format or Windows' localtime cannot hold, named
    once for all such files; a skills home that takes no new folder, refused before anything is built; a
    --version that would name the .zip badly."""

    def test_a_file_dated_outside_what_the_zip_format_or_localtime_holds_is_packaged_and_named_once(self):
        """mtime -1 and year 1950 (before 1970: Windows' localtime raises EINVAL), year 2200 (past the zip
        format's 2107) and year 5000 (past localtime's reach): each is stored at the nearest edge, its bytes
        intact, and each edge is one line for all its files, not one line per file and never a read failure."""
        files = {f"references/f{i}.md": f"f{i}\n" for i in range(5)}
        files.update({"references/neg.md": "neg\n", "references/y1950.md": "1950\n", "references/y2200.md": "2200\n",
                      "references/y5000.md": "5000\n"})
        stamps = {"references/neg.md": -1, "references/y1950.md": -631152000, "references/y2200.md": 7258118400,
                  "references/y5000.md": 95617584000}
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", body="See " + ", ".join(files) + ".", files=files)
            for rel in files:
                stamp = stamps.get(rel, 0)
                os.utime(skill / rel, (stamp, stamp))
            out = Path(tmp) / "out"
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out)])
            text = printed.getvalue()
            self.assertEqual(rc, 0, text)
            self.assertNotIn("could not be read", text)
            self.assertEqual(text.count("1980 floor"), 1, text)
            self.assertEqual(text.count("2107 ceiling"), 1, text)
            early = r"dated (19(69|70)-\d\d-\d\d|before 1970)"
            self.assertRegex(text, rf"7 files are dated before the zip format's 1980 floor: references/f0\.md {early}, "
                                   rf"references/f1\.md {early}, references/f2\.md {early} and 4 more; "
                                   r"their entries are dated 1980-01-01")
            self.assertRegex(text, r"2 files are dated past the zip format's 2107 ceiling: references/y2200\.md dated 2(199|200)-\d\d-\d\d, "
                                   r"references/y5000\.md dated (5000-\d\d-\d\d|past about 3000); their entries are dated 2107-12-31")
            for line in (line for line in text.splitlines() if " dated " in line):
                self.assertNotIn("(", line)  # N10: no parentheses inside parentheses
            with zipfile.ZipFile(out / "good-skill.skill") as zf:
                for rel in ("references/neg.md", "references/y1950.md", "references/f0.md"):
                    self.assertEqual(zf.getinfo(f"good-skill/{rel}").date_time, (1980, 1, 1, 0, 0, 0), rel)
                for rel in ("references/y2200.md", "references/y5000.md"):
                    self.assertEqual(zf.getinfo(f"good-skill/{rel}").date_time, (2107, 12, 31, 23, 59, 58), rel)
                self.assertEqual(zf.getinfo("good-skill/SKILL.md").date_time[0], time.localtime().tm_year)
                for rel, content in files.items():
                    self.assertEqual(zf.read(f"good-skill/{rel}"), content.encode("utf-8"), rel)

    def test_a_skills_home_that_takes_no_new_folder_is_refused_before_anything_is_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            home.mkdir()
            out = Path(tmp) / "out"
            with no_new_folders(home):
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out), "--deploy", str(home)])
                left = sorted(p.name for p in home.iterdir())
            text = printed.getvalue()
            self.assertEqual(rc, 1, text)
            self.assertRegex(text, rf"Deploy refused: {re.escape(str(home))} takes no new folder from this user \([^()]+\); ")
            self.assertNotIn("[WinError", text)
            self.assertNotIn("Valid", text)
            self.assertFalse(out.exists())
            self.assertEqual(left, [], left)  # no probe folder left behind

    def test_a_version_that_would_name_the_zip_badly_is_refused_before_anything_is_built(self):
        """1.0. would land good-skill-v1.0..zip; 240 characters failed as "Invalid argument" blamed on --output."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            out = Path(tmp) / "out"
            for version in ("1.0.", "1.0-", "1" * 65):
                with self.subTest(version[:10]):
                    printed = io.StringIO()
                    with contextlib.redirect_stdout(printed):
                        rc = package_dual.main([str(skill), "--version", version, "--output", str(out)])
                    self.assertEqual(rc, 1, printed.getvalue())
                    self.assertIn("--version takes digits, letters, dots and dashes", printed.getvalue())
                    self.assertNotIn("--output", printed.getvalue())
                    self.assertNotIn("Valid", printed.getvalue())
                    self.assertFalse(out.exists())
            self.assertIn("65 characters", printed.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(package_dual.main([str(skill), "--version", "1" * 64, "--output", str(out)]), 0)
            self.assertTrue((out / f"good-skill-v{'1' * 64}.zip").is_file())


class Source(unittest.TestCase):
    """Medium (second review): where the skill is read from and where the archives go."""

    def test_skill_reached_through_a_link_keeps_the_links_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = make_skill(Path(tmp) / "dp", "sc2")
            dev = real.with_name("sc2-dev")
            real.rename(dev)
            link = make_junction(Path(tmp) / "dp" / "sc2", dev)
            if link is None:
                self.skipTest("no junction on this platform")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = package_dual.main([str(link), "--version", "1.0", "--output", str(Path(tmp) / "out")])
            self.assertEqual(rc, 0, out.getvalue())
            names = zipfile.ZipFile(Path(tmp) / "out" / "sc2.skill").namelist()
            self.assertEqual(names, ["sc2/SKILL.md"])

    def test_output_inside_the_skill_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            for output in (skill / "dist", skill):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(output)])
                self.assertEqual(rc, 1, out.getvalue())
                self.assertIn("inside the skill", out.getvalue())
                self.assertEqual(sorted(p.name for p in skill.rglob("*")), ["SKILL.md"], output)


class Archive(unittest.TestCase):
    """Low: dotfiles stay out, text files land with LF, binaries byte-for-byte, .skill equals .zip."""

    def test_root_entry_and_dual_archives_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(1)\n"})
            out = Path(tmp) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = package_dual.main([str(skill), "--version", "9.9", "--output", str(out)])
            self.assertEqual(rc, 0)
            names = zipfile.ZipFile(out / "good-skill.skill").namelist()
            self.assertEqual(sorted(names), ["good-skill/SKILL.md", "good-skill/scripts/run.py"])
            self.assertEqual(sha256(out / "good-skill.skill"), sha256(out / "good-skill-v9.9.zip"))

    def test_dotfiles_are_excluded(self):
        files = {
            ".gitignore": "*.pyc\n",
            ".env": "SECRET=1\n",
            ".github/workflows/ci.yml": "on: push\n",
            "scripts/.keep": "",
            "scripts/run.py": "print(1)\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files=files)
            archive = package(skill, Path(tmp) / "out")
            names = zipfile.ZipFile(archive).namelist()
            self.assertEqual(sorted(names), ["good-skill/SKILL.md", "good-skill/scripts/run.py"], names)

    def test_text_files_land_with_lf_and_binaries_untouched(self):
        binary = b"PK\x00\x01\r\n\x00\xff\r\n"
        # Second review: a binary need not hold a NUL. A PDF's xref offsets count its CRLFs,
        # and a calendar file must keep CRLF (RFC 5545); only known text is rewritten.
        pdf = b"%PDF-1.4\r\n1 0 obj << /Type /Catalog >> endobj\r\nxref\r\n0 2\r\ntrailer << /Root 1 0 R >>\r\n%%EOF\r\n"
        ics = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
        files = {
            "scripts/run.py": "#!/usr/bin/env python3\nprint(1)\n",
            "scripts/tool": "#!/bin/sh\necho hi\n",
            "references/guide.md": "# Guide\n\nline\n",
            "assets/blob.bin": binary,
            "assets/form.pdf": pdf,
            "assets/event.ics": ics,
        }
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files=files, crlf=True)
            self.assertIn(b"\r\n", (skill / "SKILL.md").read_bytes())
            archive = package(skill, Path(tmp) / "out")
            with zipfile.ZipFile(archive) as zf:
                for text_name in ("SKILL.md", "scripts/run.py", "scripts/tool", "references/guide.md"):
                    data = zf.read(f"good-skill/{text_name}")
                    self.assertNotIn(b"\r\n", data, text_name)
                    self.assertIn(b"\n", data, text_name)
                self.assertEqual(zf.read("good-skill/assets/blob.bin"), binary)
                self.assertEqual(zf.read("good-skill/assets/form.pdf"), pdf)
                self.assertEqual(zf.read("good-skill/assets/event.ics"), ics)
                self.assertEqual(zf.getinfo("good-skill/scripts/run.py").external_attr >> 16 & 0o777, 0o755)
                self.assertEqual(zf.getinfo("good-skill/scripts/tool").external_attr >> 16 & 0o777, 0o755)
                self.assertEqual(zf.getinfo("good-skill/SKILL.md").external_attr >> 16 & 0o777, 0o644)

    def test_deploy_lands_lf_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files={"scripts/run.py": "print(1)\n"}, crlf=True)
            archive = package(skill, Path(tmp) / "out")
            target = package_dual.deploy(archive, "good-skill", Path(tmp) / "home")
            self.assertNotIn(b"\r\n", (target / "SKILL.md").read_bytes())
            self.assertNotIn(b"\r\n", (target / "scripts" / "run.py").read_bytes())



class NinthReview(unittest.TestCase):
    """The ninth review (48c4bed): a skills home not made yet under a folder that takes no new folder, refused
    before anything is built; the probe asked once and, if it cannot be removed, named; the reason a deploy
    failed said in words, never as an [Errno] or [WinError] repr."""

    def _deploy(self, skill, out, home):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            rc = package_dual.main([str(skill), "--version", "1.0", "--output", str(out), "--deploy", str(home)])
        return rc, printed.getvalue()

    def test_a_skills_home_under_a_folder_that_takes_no_new_folder_is_refused_before_anything_is_built(self):
        """N9: the home is absent and its parent denies new folders; before the fix both archives were built
        and the deploy then failed on mkdir."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            parent = Path(tmp) / "locked"
            parent.mkdir()
            home = parent / "skills"
            out = Path(tmp) / "out"
            with no_new_folders(parent):
                rc, text = self._deploy(skill, out, home)
                left = sorted(p.name for p in parent.iterdir())
            self.assertEqual(rc, 1, text)
            self.assertRegex(text, rf"Deploy refused: {re.escape(str(home))} could not be made: {re.escape(str(parent))} "
                                   r"takes no new folder from this user \([^()]+\); ")
            self.assertNotIn("[WinError", text)
            self.assertNotIn("[Errno", text)
            self.assertFalse(out.exists())
            self.assertFalse(home.exists())
            self.assertEqual(left, [], left)  # no probe folder left behind

    def test_the_skills_home_is_probed_once(self):
        """N10: main() probes before building; deploy() does not probe again."""
        calls = []
        real = package_dual._fresh

        def counting(folder, prefix, suffix, directory=False):
            calls.append(prefix)
            return real(folder, prefix, suffix, directory=directory)
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            home.mkdir()
            package_dual._fresh = counting
            try:
                rc, text = self._deploy(skill, Path(tmp) / "out", home)
            finally:
                package_dual._fresh = real
            self.assertEqual(rc, 0, text)
            self.assertEqual(calls.count(".probe-"), 1, calls)
            self.assertEqual(sorted(p.name for p in home.iterdir()), ["good-skill"])

    def test_a_probe_folder_that_cannot_be_removed_is_named(self):
        """N10: the probe was removed with its failure swallowed, leaving an unnamed .probe-* folder."""
        real = Path.rmdir

        def stuck(self):
            if self.name.startswith(".probe-"):
                raise PermissionError(13, "Access is denied", str(self))
            return real(self)
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            home.mkdir()
            Path.rmdir = stuck
            try:
                rc, text = self._deploy(skill, Path(tmp) / "out", home)
            finally:
                Path.rmdir = real
            probes = [p for p in home.iterdir() if p.name.startswith(".probe-")]
            self.assertEqual(rc, 0, text)
            self.assertEqual(len(probes), 1, probes)
            self.assertIn(f"{probes[0]} is an empty folder this run made to test the skills home and could not "
                          "remove (Access is denied); delete it", text)

    def test_why_a_deploy_step_failed_is_said_in_words(self):
        """N10: three messages printed the exception itself, "[WinError 5] Access is denied: '...'"."""
        real = package_dual._remove

        def refusing(path):
            if Path(path).name.startswith(".old-"):
                raise PermissionError(13, "Access is denied", str(path))
            return real(path)
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            home = Path(tmp) / "home"
            home.mkdir()
            rc, text = self._deploy(skill, Path(tmp) / "out", home)
            self.assertEqual(rc, 0, text)
            package_dual._remove = refusing
            try:
                rc, text = self._deploy(skill, Path(tmp) / "out2", home)
            finally:
                package_dual._remove = real
            self.assertEqual(rc, 0, text)
            self.assertIn("Deployed, but the old copy could not be removed (Access is denied); delete ", text)
            self.assertNotIn("[Errno", text)
            self.assertNotIn("[WinError", text)


if __name__ == "__main__":
    unittest.main()
