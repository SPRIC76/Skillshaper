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
        files = {
            "scripts/run.py": "#!/usr/bin/env python3\nprint(1)\n",
            "references/guide.md": "# Guide\n\nline\n",
            "assets/notes.unknownext": "plain text\nno nul\n",
            "assets/blob.bin": binary,
        }
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src", files=files, crlf=True)
            self.assertIn(b"\r\n", (skill / "SKILL.md").read_bytes())
            archive = package(skill, Path(tmp) / "out")
            with zipfile.ZipFile(archive) as zf:
                for text_name in ("SKILL.md", "scripts/run.py", "references/guide.md", "assets/notes.unknownext"):
                    data = zf.read(f"good-skill/{text_name}")
                    self.assertNotIn(b"\r\n", data, text_name)
                    self.assertIn(b"\n", data, text_name)
                self.assertEqual(zf.read("good-skill/assets/blob.bin"), binary)
                self.assertEqual(zf.getinfo("good-skill/scripts/run.py").external_attr >> 16 & 0o777, 0o755)
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
