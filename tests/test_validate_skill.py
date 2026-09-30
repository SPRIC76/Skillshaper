"""
Tests for sc2/scripts/validate_skill.py — Skillshaper (sc2) v1.4 | standard library only
tests/test_validate_skill.py | Created: 2026-09-30 03:55 ET

Run from the repository root:
    python -B -m unittest discover -s tests -v

Every fixture is built in a temporary folder; nothing here touches a real
skills home or the user's profile.
"""

import contextlib
import importlib.util
import io
import os
import re
import tempfile
import unittest
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


validate_skill = _load("validate_skill")

GOOD_MD = "---\nname: {name}\ndescription: Does a thing. Use when asked for the thing.\n---\n\n# Body\n\n{body}\n"


def make_skill(root, name="good-skill", body="Nothing to see.", files=None, md_bytes=None):
    """A minimal valid skill folder under root; files maps relative path to text or bytes."""
    skill = Path(root) / name
    skill.mkdir(parents=True, exist_ok=True)
    md = skill / "SKILL.md"
    if md_bytes is not None:
        md.write_bytes(md_bytes)
    else:
        md.write_text(GOOD_MD.format(name=name, body=body), encoding="utf-8", newline="\n")
    for rel, content in (files or {}).items():
        p = skill / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8", newline="\n")
    return skill


@contextlib.contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class RepoLayout(unittest.TestCase):
    """High: the skill must sit in sc2/ so */SKILL.md discovery finds it, and validate clean."""

    def test_skill_lives_in_sc2_and_validates_clean(self):
        self.assertTrue((REPO / "sc2" / "SKILL.md").is_file(), "sc2/SKILL.md missing")
        self.assertFalse((REPO / "SKILL.md").exists(), "SKILL.md still at the repository root")
        errors, warnings = validate_skill.check(REPO / "sc2")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_skill_and_readme_say_version_1_4_and_folder_sc2(self):
        text = (REPO / "sc2" / "SKILL.md").read_text(encoding="utf-8")
        fm, _ = validate_skill._parse_frontmatter(text)
        self.assertEqual(fm["name"], "sc2")
        self.assertEqual(str(fm["metadata"]["version"]), "1.4")
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        for line in readme.splitlines():
            if "package_dual.py" in line and "--version" in line and "<X.Y>" not in line:
                self.assertIn("--version 1.4", line, line)
        self.assertNotRegex(readme, r"skills/skillshaper/|\./skillshaper\b|`skillshaper/`",
                            "README installs the folder under a name other than sc2")
        self.assertNotRegex(readme, r"--version 1\.[0-3]\b")


class DotFolder(unittest.TestCase):
    """Medium: validating '.' must use the resolved folder name."""

    def test_dot_resolves_to_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, "dot-skill")
            with chdir(skill):
                errors, _ = validate_skill.check(".")
                self.assertEqual(errors, [])
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = validate_skill.main(["."])
                self.assertEqual(rc, 0)
                self.assertTrue(out.getvalue().startswith("dot-skill: "), out.getvalue())


class References(unittest.TestCase):
    """Medium: ./ prefixed paths must be checked; test files must not raise missing-reference errors."""

    def test_plain_missing_reference_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="See scripts/missing.py.")
            errors, _ = validate_skill.check(skill)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("scripts/missing.py", errors[0])

    def test_dot_slash_prefix_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run ./scripts/missing.py, read `./references/gone.md`, load ./assets/z")
            errors, _ = validate_skill.check(skill)
            named = {re.search(r"references (\S+),", e).group(1) for e in errors}
            self.assertEqual(named, {"scripts/missing.py", "references/gone.md", "assets/z"}, errors)

    def test_dot_slash_present_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run ./scripts/run.py", files={"scripts/run.py": "print(1)\n"})
            errors, _ = validate_skill.check(skill)
            self.assertEqual(errors, [])

    def test_test_files_are_exempt_from_missing_reference_check(self):
        fixture = "def build():\n    return ['scripts/x.py', 'references/guide.md', 'assets/z.bin']\n"
        files = {
            "scripts/mutate_selftest.py": fixture,
            "scripts/test_thing.py": fixture,
            "scripts/thing_test.py": fixture,
            "scripts/tests/helper.py": fixture,
            "scripts/real.py": "print('hi')\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            body = "Run scripts/real.py. Tests: " + ", ".join(f for f in files if f != "scripts/real.py")
            skill = make_skill(tmp, body=body, files=files)
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [], errors)
            self.assertEqual([w for w in warnings if "orphan" in w], [], warnings)

    def test_test_files_still_count_for_orphan_check(self):
        files = {
            "scripts/mutate_selftest.py": "LOGO = 'assets/logo.bin'\n",
            "assets/logo.bin": b"\x00\x01",
        }
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/mutate_selftest.py.", files=files)
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [])
            self.assertEqual([w for w in warnings if "orphan" in w], [], warnings)

    def test_non_test_script_still_errors_on_missing_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/real.py.",
                               files={"scripts/real.py": "PATH = 'references/nope.md'\n"})
            errors, _ = validate_skill.check(skill)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("references/nope.md", errors[0])


class Encoding(unittest.TestCase):
    """Medium and low: bad bytes give an ERROR line, a BOM is tolerated and reported."""

    def test_non_utf8_skill_md_is_an_error_line(self):
        raw = "---\nname: enc-skill\ndescription: Use when testing \u2014 encoding.\n---\n\nBody\n".encode("cp1252")
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, "enc-skill", md_bytes=raw)
            errors, _ = validate_skill.check(skill)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("SKILL.md", errors[0])
            self.assertRegex(errors[0], r"(?i)utf-8")

    def test_non_utf8_bundled_script_is_an_error_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/bad.py.", files={"scripts/bad.py": b"# caf\xe9\nprint(1)\n"})
            errors, _ = validate_skill.check(skill)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("scripts/bad.py", errors[0])
            self.assertRegex(errors[0], r"(?i)utf-8")

    def test_bom_is_tolerated_and_reported(self):
        raw = b"\xef\xbb\xbf" + GOOD_MD.format(name="bom-skill", body="Body").encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, "bom-skill", md_bytes=raw)
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [], errors)
            self.assertEqual(len(warnings), 1, warnings)
            self.assertIn("BOM", warnings[0])


class CommandLine(unittest.TestCase):
    """Low: unknown flags are a usage error, not a skill folder."""

    def test_unknown_flag_is_usage_error(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = validate_skill.main(["--bogus"])
        self.assertEqual(rc, 2)
        self.assertNotIn("SKILL.md not found", out.getvalue())
        self.assertIn("--bogus", out.getvalue())
        self.assertIn("Usage", out.getvalue())

    def test_help_prints_doc(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = validate_skill.main(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("Usage", out.getvalue())


class UserFolder(unittest.TestCase):
    """Low: the user-folder check is case-insensitive."""

    def test_lowercase_windows_path_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Copy to c:/users/other/skills and C:\\Users\\someone\\x.")
            _, warnings = validate_skill.check(skill)
            named = {re.search(r"user folder '([^']+)'", w).group(1) for w in warnings if "user folder" in w}
            self.assertEqual(named, {"other", "someone"}, warnings)

    def test_another_skills_validate_skill_py_is_still_checked(self):
        """Low (second review): only Skillshaper's own validator, which names the markers it hunts, is exempt."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/validate_skill.py first.",
                               files={"scripts/validate_skill.py": "OUT = '/home/claude/x'\nIN = 'C:/Users/hidden/y'\n"})
            _, warnings = validate_skill.check(skill)
            self.assertTrue(any("/home/claude" in w for w in warnings), warnings)
            self.assertTrue(any("user folder 'hidden'" in w for w in warnings), warnings)


class SecondReview(unittest.TestCase):
    """Lows from the second review: a common cue, one path style, and dotfiles the packager drops."""

    def test_triggers_on_counts_as_a_when_cue(self):
        md = b"---\nname: good-skill\ndescription: Checks things. Triggers on skill talk.\n---\n\n# Body\n"
        with tempfile.TemporaryDirectory() as tmp:
            _, warnings = validate_skill.check(make_skill(tmp, md_bytes=md))
            self.assertFalse([w for w in warnings if "when to use" in w], warnings)

    def test_nested_skill_md_is_named_with_forward_slashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="See references/sub/SKILL.md.",
                               files={"references/sub/SKILL.md": "# nested\n"})
            errors, _ = validate_skill.check(skill)
            self.assertTrue(any("references/sub/SKILL.md" in e for e in errors), errors)

    def test_a_dotfile_in_a_bundle_folder_is_not_an_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, files={"scripts/.keep": ""})
            _, warnings = validate_skill.check(skill)
            self.assertFalse([w for w in warnings if "orphan" in w], warnings)


if __name__ == "__main__":
    unittest.main()
