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
import subprocess
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


class ThirdReview(unittest.TestCase):
    """The third review (f6ebd36): what a failed deploy leaves, an older copy of this validator, a dotted path."""

    def test_a_skill_md_inside_a_dot_folder_is_not_a_nested_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, files={".old-abc123/SKILL.md": "# the copy a locked file kept\n",
                                           ".git/SKILL.md": "# not ours\n"})
            errors, _ = validate_skill.check(skill)
            self.assertFalse([e for e in errors if "more than one SKILL.md" in e], errors)

    def test_an_edited_or_older_copy_of_this_validator_is_exempt(self):
        own = Path(validate_skill.__file__).read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/validate_skill.py first.",
                               files={"scripts/validate_skill.py": own + "\n# a local note\n"})
            _, warnings = validate_skill.check(skill)
            self.assertFalse([w for w in warnings if "validate_skill.py" in w], warnings)

    def test_a_link_loop_is_walked_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp)
            link = skill / "loop"
            if os.name == "nt":
                r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(skill)], capture_output=True)
                made = r.returncode == 0
            else:
                os.symlink(skill, link, target_is_directory=True)
                made = True
            if not made:
                self.skipTest("no junction on this platform")
            errors, _ = validate_skill.check(skill)
            self.assertEqual(errors, [])

    def test_dots_after_users_are_not_a_user_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Paths look like c:/users/.... or C:\\Users\\...\\x.")
            _, warnings = validate_skill.check(skill)
            self.assertFalse([w for w in warnings if "user folder" in w], warnings)


class FourthReview(unittest.TestCase):
    """The fourth review (1da47e9): older copies of this validator, and what the packager skips."""

    def test_the_1_1_validator_and_a_docstring_on_its_opening_line_are_exempt(self):
        own = Path(validate_skill.__file__).read_text(encoding="utf-8")
        first = own.split('"""', 2)[1].strip().splitlines()[0]
        v11 = own.replace(first, "Skill validator — the base skill-creator's upload rules plus sc2's standards.", 1)
        inline = own.replace('"""\n' + first, '"""' + first, 1)
        self.assertNotEqual(v11, own)
        self.assertNotEqual(inline, own)
        for label, text in (("v1.1", v11), ("docstring on the opening line", inline)):
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                skill = make_skill(tmp, body="Run scripts/validate_skill.py first.",
                                   files={"scripts/validate_skill.py": text})
                _, warnings = validate_skill.check(skill)
                self.assertFalse([w for w in warnings if "validate_skill.py" in w], warnings)

    def test_a_workspace_folder_is_not_entered(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, files={"references/scratch-workspace/SKILL.md": "# notes\n",
                                           "references/scratch-workspace/bad.py": "def (:\n"})
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [])
            self.assertFalse([w for w in warnings if "workspace" in w], warnings)

    def test_a_link_to_the_output_folder_is_not_entered_when_the_packager_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "src")
            dist = Path(tmp) / "dist"
            dist.mkdir()
            (dist / "good-skill.skill").write_bytes(b"PK")
            link = skill / "references"
            if os.name == "nt":
                made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(dist)],
                                      capture_output=True).returncode == 0
            else:
                os.symlink(dist, link, target_is_directory=True)
                made = True
            if not made:
                self.skipTest("no junction on this platform")
            _, warnings = validate_skill.check(skill, out=dist)
            self.assertFalse([w for w in warnings if "good-skill.skill" in w], warnings)

    def test_what_the_packager_drops_raises_no_error(self):
        """A Mac's AppleDouble files (__MACOSX/, ._name) and other dotfiles never reach the archive."""
        apple = b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X        \xff\xfe"
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/run.py.",
                               files={"scripts/run.py": "print('hi')\n",
                                      "scripts/__MACOSX/._run.py": apple,
                                      "scripts/._run.py": apple,
                                      "references/.notes.md": apple})
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [])
            self.assertIn("junk in the skill folder: scripts/__MACOSX", warnings)

    def test_a_script_carrying_a_binary_payload_is_not_held_to_utf8(self):
        """A self-extracting script (#!, then tar or gzip bytes, which always hold a NUL) is packaged
        byte-for-byte; a script saved in another encoding, or UTF-16, is still an error."""
        shar = b"#!/bin/sh\nsed '1,/^exit$/d' \"$0\" | tar xz\nexit\n\x1f\x8b\x08\x00\r\n\x00\xff\r\n"
        cp1252 = "#!/bin/sh\necho 'café'\n".encode("cp1252")
        utf16 = "#!/bin/sh\necho hi\n".encode("utf-16")
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/unpack.sh, scripts/greet.sh, scripts/wide.sh.",
                               files={"scripts/unpack.sh": shar, "scripts/greet.sh": cp1252, "scripts/wide.sh": utf16})
            errors, _ = validate_skill.check(skill)
            self.assertEqual(sorted(e.split(" ")[0] for e in errors), ["scripts/greet.sh", "scripts/wide.sh"], errors)


class FifthReview(unittest.TestCase):
    """The fifth review (3814807): what Python runs, what the package ships, and one junk file named once."""

    def test_a_bundled_script_saved_with_a_bom_compiles_and_the_bom_is_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/bom.py.", files={"scripts/bom.py": b"\xef\xbb\xbfprint('bom ok')\n"})
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [])
            self.assertTrue([w for w in warnings if "scripts/bom.py" in w and "byte-order mark" in w], warnings)

    def test_a_dotfile_the_skill_names_is_missing_from_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Copy references/.env.example, then run scripts/.helper.py.",
                               files={"references/.env.example": "KEY=\n", "scripts/.helper.py": "print(1)\n"})
            errors, _ = validate_skill.check(skill)
            named = sorted(e for e in errors if "leaves out" in e)
            self.assertEqual(len(named), 2, errors)
            self.assertIn("references/.env.example", named[0])
            self.assertIn("scripts/.helper.py", named[1])

    def test_a_script_holding_a_nul_byte_is_an_error_line_on_every_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/nul.py.", files={"scripts/nul.py": b"x = 1\x00\n"})
            errors, _ = validate_skill.check(skill)
            self.assertTrue([e for e in errors if e.startswith("scripts/nul.py does not compile")], errors)

    def test_a_junk_file_is_named_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="Run scripts/run.py.", files={"scripts/run.py": "print(1)\n",
                                                                     "scripts/desktop.ini": "[.ShellClassInfo]\n"})
            _, warnings = validate_skill.check(skill)
            self.assertEqual([w for w in warnings if "desktop.ini" in w], ["junk in the skill folder: scripts/desktop.ini"])


if __name__ == "__main__":
    unittest.main()
