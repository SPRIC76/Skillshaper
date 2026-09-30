"""
Tests for sc2/scripts/package_dual.py — Skillshaper (sc2) v1.4 | standard library only
tests/test_package_dual.py | Created: 2026-09-30 03:55 ET

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
import stat
import subprocess
import tempfile
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


if __name__ == "__main__":
    unittest.main()
