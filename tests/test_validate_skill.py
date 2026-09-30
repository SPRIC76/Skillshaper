"""
Tests for sc2/scripts/validate_skill.py — Skillshaper (sc2) v1.4 | standard library only
tests/test_validate_skill.py | Created: 2026-09-30 03:55 ET
Updated: 2026-09-30 14:08 ET — SeventhReview: frontmatter PyYAML refuses (with and without PyYAML), an unlistable folder,
a referenced name holding a space, the BOM rule's edges and every text type at every level; each
failed before its fix.
Updated: 2026-09-30 14:46 ET — EighthReview: the frontmatter parity table (every verdict recorded from PyYAML 6.0.3, run through
the built-in reader always and through PyYAML where installed), the shapes the built-in reader refuses by name, the
BOM as a name, and the docs and .gitignore against the code; each failed before its fix.

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


class SixthReview(unittest.TestCase):
    """The sixth review (42503ab): a bundled file that cannot be read, and a BOM in every bundled text file."""

    def test_a_bundled_file_that_cannot_be_read_is_an_error_line_not_a_traceback(self):
        for rel in ("references/z.md", "assets/logo.png"):
            with self.subTest(rel), tempfile.TemporaryDirectory() as tmp:
                skill = make_skill(tmp, body="See references/z.md and assets/logo.png.",
                                   files={"references/z.md": "z\n", "assets/logo.png": b"\x89PNG"})
                with unreadable(skill / rel):
                    errors, _ = validate_skill.check(skill)
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        rc = validate_skill.main([str(skill)])
                self.assertEqual(len(errors), 1, errors)
                self.assertRegex(errors[0], rf"^{rel} could not be read \(.+\); ")
                self.assertEqual(rc, 1)
                self.assertIn("good-skill: 1 error(s)", out.getvalue())

    def test_a_bom_in_every_bundled_text_file_is_named_and_an_error_where_it_breaks_the_file(self):
        bom = validate_skill.BOM
        files = {"references/notes.md": f"{bom}# notes\n", "scripts/x.txt": f"{bom}x\n", "scripts/c.yaml": f"{bom}a: 1\n",
                 "scripts/w.ps1": f"{bom}Write-Host hi\n", "scripts/run.sh": f"{bom}#!/bin/sh\necho hi\n",
                 "scripts/data.json": f'{bom}{{"a": 1}}\n', "scripts/sheb.py": f"{bom}#!/usr/bin/env python3\nprint(1)\n",
                 "scripts/bom.py": f"{bom}print(1)\n"}
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="See " + ", ".join(files) + ".", files=files)
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(sorted(e.split(" ")[0] for e in errors), ["scripts/data.json", "scripts/run.sh", "scripts/sheb.py"], errors)
            self.assertTrue(all("byte-order mark" in e for e in errors), errors)
            self.assertEqual(sorted(w.split(" ")[0] for w in warnings if "byte-order mark" in w),
                             ["references/notes.md", "scripts/bom.py", "scripts/c.yaml", "scripts/x.txt"], warnings)
            self.assertFalse([w for w in warnings if "w.ps1" in w], warnings)  # Windows PowerShell reads UTF-8 by its BOM
            self.assertFalse([e for e in errors if "does not compile" in e], errors)


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


@contextlib.contextmanager
def without_pyyaml():
    """The built-in frontmatter reader, whether or not PyYAML is installed: `import yaml` raises ImportError."""
    import sys
    saved = sys.modules.get("yaml", "<absent>")
    sys.modules["yaml"] = None
    try:
        yield
    finally:
        if saved == "<absent>":
            del sys.modules["yaml"]
        else:
            sys.modules["yaml"] = saved


def _has_pyyaml():
    try:
        import yaml  # noqa: F401
    except ImportError:
        return False
    return True


class SeventhReview(unittest.TestCase):
    """The seventh review (eff4bb1): frontmatter YAML refuses, read alike with and without PyYAML; a folder
    that cannot be listed; a referenced name holding a space; the BOM rule's edges and every text type."""

    REFUSED = {"colon": "description: Use when: the user asks.", "colon-end": "description: Use when asked:",
               "tab": "description:\tUse when asked.", "no-space": "description:Use when asked.",
               "unclosed-list": "description: [Use when asked", "unclosed-map": "description: {use: when asked",
               "unclosed-quote": "description: \"Use when asked"}
    AGREED = {"bool": ("description: yes", None), "comment": ("description: Use when asked #not a comment", "Use when asked"),
              "quoted-colon": ("description: \"Use when: the user asks.\"", "Use when: the user asks."),
              "quoted-hash": ("description: 'Use when # asked'", "Use when # asked")}

    def _frontmatter_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            for label, line in self.REFUSED.items():
                with self.subTest(label):
                    md = f"---\nname: good-skill\n{line}\n---\n\n# Body\n".encode("utf-8")
                    skill = make_skill(Path(tmp) / label, md_bytes=md)
                    errors, _ = validate_skill.check(skill)
                    self.assertEqual(len(errors), 1, errors)
                    self.assertTrue(errors[0].startswith("frontmatter is not valid YAML"), errors)
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        rc = validate_skill.main([str(skill), "--strict"])
                    self.assertEqual(rc, 1)
                    self.assertIn("good-skill: 1 error(s)", out.getvalue())
            for label, (line, want) in self.AGREED.items():
                with self.subTest(label):
                    text = f"---\nname: good-skill\n{line}\n---\n\n# Body\n"
                    fm, _ = validate_skill._parse_frontmatter(text)
                    got = fm.get("description")
                    self.assertEqual(got if isinstance(got, str) else None, want, fm)
                    skill = make_skill(Path(tmp) / label, md_bytes=text.encode("utf-8"))
                    errors, warnings = validate_skill.check(skill)
                    if want is None:  # yes is a boolean to both readers: not text, so not a description
                        self.assertEqual(len(errors), 1, errors)
                        self.assertRegex(errors[0], r"^description is a boolean \(True\), not text")
                    else:
                        self.assertEqual(errors, [])
                        self.assertFalse([w for w in warnings if "when to use" in w], warnings)

    @unittest.skipUnless(_has_pyyaml(), "PyYAML is not installed here")
    def test_frontmatter_pyyaml_refuses_is_an_error_line_with_pyyaml(self):
        self._frontmatter_cases()

    def test_frontmatter_pyyaml_refuses_is_an_error_line_without_pyyaml(self):
        with without_pyyaml():
            self._frontmatter_cases()

    def test_a_folder_that_cannot_be_listed_is_an_error_line_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp) / "a", body="See references/guide.md.",
                               files={"references/guide.md": "g\n", "references/secret/x.md": "x\n", "private/x.md": "x\n"})
            with unlistable(skill / "references" / "secret"), unlistable(skill / "private"):
                errors, _ = validate_skill.check(skill)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = validate_skill.main([str(skill)])
            self.assertEqual(sorted(e.split(" ")[0] for e in errors), ["private/", "references/secret/"], errors)
            for e in errors:
                self.assertRegex(e, r"^\S+/ could not be listed \(.+\); check its permissions$")
            self.assertEqual(rc, 1)
            self.assertIn("good-skill: 2 error(s)", out.getvalue())
            # tests/ at the root is never entered, so a folder there that cannot be listed is no concern
            skill = make_skill(Path(tmp) / "b", files={"tests/private/t.py": "pass\n"})
            with unlistable(skill / "tests" / "private"):
                errors, _ = validate_skill.check(skill)
            self.assertEqual(errors, [])

    def test_a_referenced_name_holding_a_space_is_resolved_and_not_an_orphan(self):
        body = ("See references/my guide.md and assets/my file.txt, then [the guide](references/my%20guide.md), "
                "`references/my guide.md` and <assets/my%20file.txt>.")
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body=body, files={"references/my guide.md": "# g\n", "assets/my file.txt": "x\n"})
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(errors, [], errors)
            self.assertFalse([w for w in warnings if "orphan" in w], warnings)
            skill = make_skill(tmp, "other-skill", body="See references/my guide.md.", files={"assets/my file.txt": "x\n"})
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("does not exist", errors[0])
            # a name only mentioned in its %20 form is still mentioned
            skill = make_skill(tmp, "third-skill", body="Read [it](assets/my%20file.txt).", files={"assets/my file.txt": "x\n"})
            _, warnings = validate_skill.check(skill)
            self.assertFalse([w for w in warnings if "orphan" in w], warnings)

    def test_the_bom_rule_decides_by_what_runs_and_reads_every_text_type_at_every_level(self):
        bom = validate_skill.BOM
        files = {"references/notes.md": f"{bom}#!/bin/sh\nnot a script, a note\n",   # a note whose first line looks like a shebang
                 "scripts/plain.sh": f"{bom}echo hi\n",                              # a shell reads the BOM as part of the command
                 "scripts/pwsh.ps1": f"{bom}#!/usr/bin/env pwsh\nWrite-Host hi\n",   # Windows PowerShell reads its BOM
                 "scripts/Upper.PY": "def (:\n",                                     # compiled whatever the case of .py
                 "scripts/conf.toml": f"{bom}[a]\nb = 1\n", "scripts/app.js": f"{bom}console.log(1)\n",
                 "scripts/rows.jsonl": f'{bom}{{"a": 1}}\n', "scripts/table.csv": f"{bom}a,b\n",
                 "scripts/doc.xml": f"{bom}<a/>\n", "scripts/Makefile": f"{bom}all:\n\techo\n",
                 "scripts/latin.js": "// caf\xe9\n".encode("cp1252"),               # a type the validator once never read
                 "LICENSE": "caf\xe9\n".encode("cp1252"),                            # root-level, shipped byte-for-byte
                 "README.md": f"{bom}# hi\n", "run.sh": f"{bom}#!/bin/sh\necho hi\n"}
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(tmp, body="See " + ", ".join(f for f in files if f.split("/")[0] in ("references", "scripts", "assets")) + ".",
                               files=files)
            errors, warnings = validate_skill.check(skill)
            self.assertEqual(sorted(e.split(" ")[0] for e in errors), ["run.sh", "scripts/Upper.PY", "scripts/latin.js", "scripts/plain.sh"], errors)
            self.assertTrue([e for e in errors if e.startswith("scripts/Upper.PY does not compile")], errors)
            self.assertTrue([e for e in errors if e.startswith("scripts/latin.js is not UTF-8")], errors)
            self.assertTrue([e for e in errors if e.startswith("run.sh has a UTF-8 byte-order mark (BOM) before its #! line")], errors)
            self.assertTrue([e for e in errors if e.startswith("scripts/plain.sh starts with a UTF-8 byte-order mark (BOM), which a shell")], errors)
            self.assertEqual(sorted(w.split(" ")[0] for w in warnings if "byte-order mark" in w),
                             ["README.md", "references/notes.md", "scripts/Makefile", "scripts/app.js", "scripts/conf.toml",
                              "scripts/doc.xml", "scripts/rows.jsonl", "scripts/table.csv"], warnings)
            self.assertFalse([w for w in warnings if "references/notes.md" in w and "#!" in w], warnings)
            self.assertEqual([w.split(" (")[0] for w in warnings if "not UTF-8" in w], ["LICENSE is not UTF-8"], warnings)
            self.assertFalse([line for line in errors + warnings if "pwsh.ps1" in line], errors + warnings)


class EighthReview(unittest.TestCase):
    """The eighth review (0bb76bf): the built-in frontmatter reader reads what PyYAML reads, for the shapes a
    SKILL.md uses, and refuses by name what it does not; the BOM is a name, not an invisible literal; the docs
    and .gitignore say what the code does."""

    # Every verdict here was recorded from PyYAML 6.0.3 on 2026-09-30, so the parity is checked against the
    # record with and without PyYAML: ("text", key, value) reads that value and validates clean; ("none", key)
    # reads None; ("typed", kind) is a description that is not text; ("error", fragment) is refused by both
    # readers, the fragment being the built-in reader's wording.
    PARITY = [
        ("apostrophe", "description: 'Use when it''s asked.'", ("text", "description", "Use when it's asked.")),
        ("escaped-quote", 'description: "Use when \\"asked\\"."', ("text", "description", 'Use when "asked".')),
        ("escaped-backslash", 'description: "Use when asked\\\\now."', ("text", "description", "Use when asked\\now.")),
        ("escaped-tab", 'description: "Use when\\tasked."', ("text", "description", "Use when\tasked.")),
        ("escaped-unicode", 'description: "Use when asked \\u00e9"', ("text", "description", "Use when asked é")),
        ("single-backslash", "description: 'Use when asked\\now.'", ("text", "description", "Use when asked\\now.")),
        ("quoted-colon", 'description: "Use when: the user asks."', ("text", "description", "Use when: the user asks.")),
        ("quoted-hash", "description: 'Use when # asked'", ("text", "description", "Use when # asked")),
        ("comment", "description: Use when asked #not a comment", ("text", "description", "Use when asked")),
        ("url", "description: Use when https://example.com/x is asked", ("text", "description", "Use when https://example.com/x is asked")),
        ("colon-no-space", "description: Use when asked:now", ("text", "description", "Use when asked:now")),
        ("trailing-space", "description: Use when asked   ", ("text", "description", "Use when asked")),
        ("bool-mixed", "description: yEs", ("text", "description", "yEs")),
        ("dotted", "description: Use when 2026.09.30 asks", ("text", "description", "Use when 2026.09.30 asks")),
        ("continuation", "description: Use when asked\n  to do the thing.", ("text", "description", "Use when asked to do the thing.")),
        ("continuation-two", "description: Use when asked\n  to do\n  the thing.", ("text", "description", "Use when asked to do the thing.")),
        ("continuation-blank", "description: Use when asked\n\n  to do the thing.", ("text", "description", "Use when asked\nto do the thing.")),
        ("quoted-continuation", 'description: "Use when asked\n  to do the thing."', ("text", "description", "Use when asked to do the thing.")),
        ("single-continuation", "description: 'Use when asked\n  to do the thing.'", ("text", "description", "Use when asked to do the thing.")),
        ("block-clip", "description: >\n  Use when\n  asked.\n", ("text", "description", "Use when asked.\n")),
        ("block-strip", "description: >-\n  Use when asked.\n", ("text", "description", "Use when asked.")),
        ("block-keep", "description: >+\n  Use when asked.\n", ("text", "description", "Use when asked.\n")),
        ("block-indent-indicator", "description: >2\n  Use when asked.\n", ("text", "description", "Use when asked.\n")),
        ("literal-strip", "description: |-\n  Use when\n  asked.\n", ("text", "description", "Use when\nasked.")),
        ("literal-keep", "description: |+\n  Use when asked.\n", ("text", "description", "Use when asked.\n")),
        ("one-space-indent", " description: Use when asked.", ("text", "description", "Use when asked.")),
        ("quoted-key", '"description": Use when asked', ("text", "description", "Use when asked")),
        ("duplicate", "description: one\ndescription: Use when asked", ("text", "description", "Use when asked")),
        ("flow-comment", "allowed-tools: [Read, Write] # both", ("text", "allowed-tools", ["Read", "Write"])),
        ("flow-quoted", "allowed-tools: [\"Read\", 'Write, too']", ("text", "allowed-tools", ["Read", "Write, too"])),
        ("flow-multiline", "allowed-tools: [Read,\n  Write]", ("text", "allowed-tools", ["Read", "Write"])),
        ("flow-trailing-comma", "allowed-tools: [Read, Write,]", ("text", "allowed-tools", ["Read", "Write"])),
        ("flow-empty", "allowed-tools: []", ("text", "allowed-tools", [])),
        ("block-list", "allowed-tools:\n  - Read\n  - Write", ("text", "allowed-tools", ["Read", "Write"])),
        ("block-list-quoted", "allowed-tools:\n  - \"Read\"\n  - 'Write'", ("text", "allowed-tools", ["Read", "Write"])),
        ("block-list-one-space", "allowed-tools:\n - Read\n - Write", ("text", "allowed-tools", ["Read", "Write"])),
        ("flow-map", 'metadata: {version: "1.4", note: plain}', ("text", "metadata", {"version": "1.4", "note": "plain"})),
        ("nested-map", 'metadata:\n  version: "1.4"\n  nested:\n    deep: 1', ("text", "metadata", {"version": "1.4", "nested": {"deep": 1}})),
        ("nested-map-one-space", 'metadata:\n version: "1.4"', ("text", "metadata", {"version": "1.4"})),
        ("hex", "metadata: {n: 0x1f, o: 017, b: 0b11, u: 1_000, s: 1:30, f: .5, e: 1e3}",
         ("text", "metadata", {"n": 31, "o": 15, "b": 3, "u": 1000, "s": 90, "f": 0.5, "e": "1e3"})),
        ("tilde", "description: ~", ("none", "description")),
        ("null-word", "description: null", ("none", "description")),
        ("null-upper", "description: NULL", ("none", "description")),
        ("empty", "description:", ("none", "description")),
        ("comment-only", "description: # nothing", ("none", "description")),
        ("nested-empty", "metadata:\n", ("none", "metadata")),
        ("bool", "description: yes", ("typed", "a boolean")),
        ("bool-title", "description: Yes", ("typed", "a boolean")),
        ("bool-upper", "description: NO", ("typed", "a boolean")),
        ("float", "description: 1.4", ("typed", "a number")),
        ("int", "description: 12", ("typed", "a number")),
        ("date", "description: 2026-09-30", ("typed", "a date")),
        ("colon", "description: Use when: the user asks.", ("error", "unquoted ': '")),
        ("colon-end", "description: Use when asked:", ("error", "unquoted ': '")),
        ("continuation-colon", "description: Use when asked\n  to: do it", ("error", "unquoted ': '")),
        ("tab-after-key", "description:\tUse when asked.", ("error", "tab after")),
        ("tab-in-plain", "description: Use when\tasked.", ("error", "holds a tab")),
        ("tab-indent", "metadata:\n\tversion: \"1.4\"", ("error", "starts with a tab")),
        ("no-space", "description:Use when asked.", ("error", "needs a space after the colon")),
        ("unclosed-list", "description: [Use when asked", ("error", "opens a [ it does not close")),
        ("unclosed-map", "description: {use: when asked", ("error", "opens a { it does not close")),
        ("unclosed-quote", 'description: "Use when asked', ("error", "opens a quote it does not close")),
        ("unclosed-quote-then-key", 'description: "Use when asked\nlicense: x', ("error", "opens a quote it does not close")),
        ("text-after-quote", 'description: "Use" when asked', ("error", "text after its closing quote")),
        ("text-after-bracket", "allowed-tools: [Read] Write", ("error", "text after its closing ]")),
        ("unknown-escape", 'description: "Use \\q when asked"', ("error", "escape \\q")),
        ("alias", "description: *a", ("error", "alias")),
        ("list-not-map", "- description: Use when asked", ("error", "a list")),
    ]
    # What PyYAML reads that the built-in reader does not: refused by name, with the way to write it.
    UNSUPPORTED = [("anchor", "description: &a Use when asked", "anchor"), ("tag", "description: !!str Use when asked", "tag"),
                   ("flow-nested", "allowed-tools: [Read, [Write]]", "flow collection inside another"),
                   ("complex-key", "? description\n: Use when asked", "complex key"),
                   ("list-of-maps", "allowed-tools:\n  - name: Read", "list of mappings")]

    def _parity(self, builtin, crlf=False):
        with tempfile.TemporaryDirectory() as tmp:
            for label, line, verdict in self.PARITY:
                with self.subTest(label + (" crlf" if crlf else "")):
                    head = " name: good-skill\n" if label == "one-space-indent" else "name: good-skill\n"
                    if verdict[0] in ("text", "none") and verdict[1] != "description":
                        head += "description: Use when asked.\n"
                    text = f"---\n{head}{line}\n---\n\n# Body\n"
                    if crlf:
                        text = text.replace("\n", "\r\n")
                    skill = make_skill(Path(tmp) / label, md_bytes=text.encode("utf-8"))
                    if verdict[0] == "error":
                        with self.assertRaises(ValueError) as cm:
                            validate_skill._parse_frontmatter(text)
                        self.assertTrue(str(cm.exception).startswith("frontmatter"), cm.exception)
                        if builtin:
                            self.assertIn(verdict[1], str(cm.exception))
                        errors, _ = validate_skill.check(skill)
                        self.assertEqual(len(errors), 1, errors)
                        continue
                    fm, _ = validate_skill._parse_frontmatter(text)
                    errors, warnings = validate_skill.check(skill)
                    if verdict[0] == "text":
                        self.assertEqual(fm[verdict[1]], verdict[2])
                        self.assertEqual(errors, [], errors)
                        if verdict[1] == "description" and validate_skill.WHEN_CUE.search(verdict[2]):
                            self.assertFalse([w for w in warnings if "when to use" in w], warnings)
                    elif verdict[0] == "none":
                        self.assertIsNone(fm[verdict[1]], fm)
                        self.assertEqual(errors, ["frontmatter has no description"] if verdict[1] == "description" else [], errors)
                    else:
                        self.assertNotIsInstance(fm["description"], str)
                        self.assertEqual(len(errors), 1, errors)
                        self.assertRegex(errors[0], rf"^description is {verdict[1]} \(.+\), not text")
            with self.subTest("name null"):
                errors, _ = validate_skill.check(make_skill(Path(tmp) / "nn", md_bytes=b"---\nname: ~\ndescription: Use when asked.\n---\n"))
                self.assertIn("frontmatter has no name", errors)

    def test_the_built_in_reader_gives_the_recorded_pyyaml_verdict_on_every_shape(self):
        with without_pyyaml():
            self._parity(builtin=True)
            self._parity(builtin=True, crlf=True)

    @unittest.skipUnless(_has_pyyaml(), "PyYAML is not installed here")
    def test_pyyaml_gives_the_recorded_verdict_on_every_shape(self):
        self._parity(builtin=False)
        self._parity(builtin=False, crlf=True)

    def test_a_shape_the_built_in_reader_does_not_take_is_refused_by_name_with_the_way_to_write_it(self):
        with without_pyyaml(), tempfile.TemporaryDirectory() as tmp:
            for label, line, named in self.UNSUPPORTED:
                with self.subTest(label):
                    text = f"---\nname: good-skill\n{line}\n---\n\n# Body\n"
                    with self.assertRaises(ValueError) as cm:
                        validate_skill._parse_frontmatter(text)
                    message = str(cm.exception)
                    self.assertTrue(message.startswith("frontmatter uses "), message)
                    self.assertIn(named, message)
                    self.assertIn("install PyYAML", message)
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        rc = validate_skill.main([str(make_skill(Path(tmp) / label, md_bytes=text.encode("utf-8")))])
                    self.assertEqual(rc, 1)
                    self.assertIn("good-skill: 1 error(s)", out.getvalue())

    @unittest.skipUnless(_has_pyyaml(), "PyYAML is not installed here")
    def test_pyyaml_reads_the_shapes_the_built_in_reader_refuses_by_name(self):
        for label, line, _ in self.UNSUPPORTED:
            with self.subTest(label):
                fm, _ = validate_skill._parse_frontmatter(f"---\nname: good-skill\n{line}\n---\n")
                self.assertEqual(fm["name"], "good-skill")

    def test_the_bom_is_a_name_not_an_invisible_literal(self):
        """A literal U+FEFF inside a string literal is invisible; an editor, a paste or a normalising tool can
        drop it without a visible diff, and the BOM rule would then never fire."""
        self.assertEqual(validate_skill.BOM, chr(0xFEFF))
        for path in (Path(validate_skill.__file__), Path(__file__)):
            self.assertNotIn(chr(0xFEFF), path.read_text(encoding="utf-8"), f"{path.name} holds a literal BOM")

    def test_the_docs_say_what_the_code_does_and_git_ignores_what_the_docs_produce(self):
        import fnmatch
        skill_md = (REPO / "sc2" / "SKILL.md").read_text(encoding="utf-8")
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("package_dual.py <skill-folder> --version <X.Y> [--output <dir>] [--deploy <skills-home>] [--strict]", skill_md)
        self.assertIn("a changelog at the root included", skill_md)  # the missing-reference check reads every shipped text file
        for doc, name in ((skill_md, "SKILL.md"), (readme, "README.md")):
            self.assertIn("`.sh`, `.bash`, `.zsh`, `.py`, or no suffix", doc, name)
            self.assertIn("`.pytest_cache`", doc, name)
            self.assertIn("`.pyc`", doc, name)
            self.assertIn("with and without PyYAML for the shapes a SKILL.md uses", doc, name)
        self.assertIn("icacls", readme)  # the ACL deny two tests set and lift, and how to lift it after a killed run
        patterns = (REPO / ".gitignore").read_text(encoding="utf-8").split()
        for produced in ("sc2.skill", "sc2-v1.4.zip", "sc2-v2.0-rc1.zip"):
            self.assertTrue(any(fnmatch.fnmatch(produced, pat) for pat in patterns), f"{produced} is not ignored")
        self.assertIn("dist/", patterns)


if __name__ == "__main__":
    unittest.main()
