#!/usr/bin/env python3
"""
Skill validator — the Agent Skills specification's rules plus Skillshaper's (sc2) standards.
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
Updated: 2026-09-30 06:03 ET — v1.4: every released version is exempt by its first docstring line (1.1
named sc2's standards; a copy may open the docstring on the quotes' line); the walk leaves
*-workspace folders and __MACOSX unentered and, given the packager's output folder, cuts a
link into it as the packager does; a dotfile is not read, since it never ships;
desktop.ini is junk; a script that starts with #! and carries a binary payload is not
held to UTF-8.
Updated: 2026-09-30 06:34 ET — v1.5: a dotfile the skill names is an error, since the package leaves it
out; a bundled script's BOM is a warning, not a compile error (Python runs it); a NUL
byte in a script is an ERROR line on Python 3.10 too; junk is named once, not also as an
orphan; beside also means beside the link a skill is reached through.
Updated: 2026-09-30 12:36 ET — v1.6: a bundled file that cannot be read (held open, no permission) is an ERROR
line naming it and the reason, not a traceback; a UTF-8 BOM is named in every bundled text
file, an error where it breaks the file (before a #! line, or in a .json) and left alone in
a .ps1, which Windows PowerShell reads by its BOM.
Updated: 2026-09-30 14:08 ET — v1.7: frontmatter PyYAML refuses is an ERROR line, not a traceback, and the built-in
reader refuses the same (an unquoted ": " or a tab after the key, an unclosed [ { or quote) and reads
yes/no and a trailing # comment as PyYAML does; a folder that cannot be listed is an ERROR line; a
referenced name holding a space (or %20) is resolved; the BOM rule decides by what runs (a .sh, .bash,
.zsh, .py or suffixless file), so a .sh with no #! line is an error and a .md or .ps1 opening with #! is
not called unrunnable; every text type the packager rewrites, at every level of the skill, is read
(root-level LICENSE and README.md included; a non-UTF-8 file outside references/, scripts/ and assets/
is a warning); .PY is compiled.
Updated: 2026-09-30 14:46 ET — v1.8: the built-in frontmatter reader reads what PyYAML reads for the shapes a SKILL.md
uses (YAML's own quote escapes, a comment after a closing bracket, values continued on indented lines, > and |
with - and +, block lists, nested and indented mappings, and null, boolean, number and date values typed as
PyYAML types them, yEs a string), refuses what PyYAML refuses (a tab in a plain value, text after a closing
quote, an unknown escape) and refuses by name what it does not take (an anchor, alias or tag, a nested flow
collection, a list of mappings, a complex key); a description that is not text is named as a boolean, number
or date; a null name is no name; the BOM is the name BOM, never an invisible literal.
Updated: 2026-09-30 15:37 ET — v1.9: the built-in reader reads a small, named subset of YAML and refuses everything else by
name: for any input it returns exactly what PyYAML 6 returns, or refuses, and never stops on a traceback (an
empty list item or flow value, an indentless block list, a comment after a block header, an escaped line break,
[don't, stop] and a colon inside a flow list read as PyYAML reads them; a plain value opening with ` @ % - , ] }
refused as PyYAML refuses it); it runs in linear time without recursion, within a size cap; a mapping nested
deeper than one level is now refused by name; a key YAML types (on, yes, 1, ~) and a list or mapping
description are named as YAML types them; the U+2028 and U+2029 escapes are written by name.
Updated: 2026-09-30 16:43 ET — v1.10: a number past Python's 4,300-digit limit for printing is shown by its size, so
check() ends on an ERROR line, never a traceback; with PyYAML, a tag it cannot build (!!bool maybe, an
empty !!int) is an ERROR line naming what failed; the reserved-character message quotes one character,
the tab message says the reader takes no tab anywhere, and a BOM and a line break YAML reads each get one
sentence; the subset below names the key characters and cap, no tab, and one-line list items; the
messages and help name no host (the Agent Skills format is for any agent).
Updated: 2026-09-30 17:14 ET — v1.11: the Agent Skills specification's rules (agentskills.io/specification,
read 2026-09-30): metadata a mapping of text keys to text values, license and allowed-tools text,
compatibility 1-500 characters, each an ERROR line; the stricter rules some hosts apply on upload
are named as theirs; a name that is a list or mapping is named so; a value a !! tag made is told to
drop the tag; "Use before", "Use after" and "Use while" count as when-to-use cues; "honor", in American spelling.

Errors are what the Agent Skills specification's rules exclude, what some hosts reject on upload
(angle brackets in the description, more than one SKILL.md), or what leaves the
skill broken: frontmatter keys and limits (metadata a mapping of text keys to text values,
license and allowed-tools text, compatibility 1 to 500 characters; and frontmatter that is not valid YAML,
read by PyYAML when it is installed; without it, the built-in reader reads this subset
and refuses the rest by name with the way to write it, or pip install pyyaml -
key: value values, the key of letters, digits, _ and - (or quoted without escapes), up to
128 characters, the value plain, single- or double-quoted, on one line or continued on
indented lines; > and | blocks with chomping and indent indicators; flow lists and flow
mappings of such values; block lists of one-line items at the key's indent or indented;
one level of nested mapping; comments, empty values and null forms; no tab anywhere;
values typed as PyYAML types them), a key YAML
types as a boolean, number or null, a name that differs from its folder, a description that is not text,
angle brackets in the description, a body over 500 lines, a referenced file that
does not exist or is a dotfile the package leaves out (bare or ./-prefixed, in SKILL.md and in
every other text file the package ships; test files - *_selftest.py, test_*.py,
*_test.py, anything under tests/ - name throwaway fixtures and are exempt),
a bundled Python script that does not compile, a bundled file (references/, scripts/, assets/)
that is not UTF-8 (a script that starts with #! and holds a NUL byte carries a binary payload,
is stored byte-for-byte, and is exempt), a bundled file or folder that cannot be read or listed
(held open by another program, or no permission), and a UTF-8 BOM where it breaks the file:
before the #! line of a script that is run by name (.sh, .bash, .zsh, .py, or no suffix), at the
start of a .sh, .bash or .zsh (a shell reads it as part of the first command), or in a .json,
which JSON forbids and json.loads rejects.

Warnings are what makes a skill trigger badly or age badly: no "when to use" cue
in the description (the description is all a model sees when it picks a skill),
trigger phrases kept in the body instead, files nothing points to, long
references without a contents list, a UTF-8 BOM in SKILL.md or any other text file
the package ships (a .ps1 excepted: Windows PowerShell reads a UTF-8 script by its BOM),
a text file outside references/, scripts/ and assets/ (LICENSE, README.md) that is not UTF-8,
and paths from sandboxes that no longer exist (/mnt/skills, /home/claude), one
person's user folder in any letter case, or tool names only one surface has.

Usage:
    python validate_skill.py <skill-folder> [<skill-folder> ...] [--strict]

Exit 0 when no errors (and, with --strict, no warnings); 1 otherwise; 2 for an
unknown option. Needs only the standard library; uses PyYAML for the frontmatter
when present.
"""

import bisect
import fnmatch
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
JUNK_DIRS = {"__pycache__", "node_modules", ".pytest_cache", "__MACOSX"}
JUNK_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
ROOT_SKIP_DIRS = {"evals", "tests"}
BUNDLE_DIRS = ("references", "scripts", "assets")
# The text types: read here for encoding and BOM, and written with LF by package_dual.py (which takes this
# list); a file with no suffix (LICENSE, Makefile) that holds no NUL byte counts too. Everything else is
# binary to both.
TEXT_SUFFIXES = {".md", ".markdown", ".mdx", ".rst", ".adoc", ".tex", ".bib", ".txt",
                 ".json", ".jsonl", ".ndjson", ".ipynb", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                 ".conf", ".properties", ".csv", ".tsv", ".xml", ".svg", ".html", ".htm",
                 ".css", ".scss", ".sass", ".less", ".sql", ".graphql", ".gql", ".proto",
                 ".py", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1",
                 ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".jsx", ".tsx", ".vue", ".svelte",
                 ".rb", ".pl", ".pm", ".php", ".lua", ".r", ".jl", ".go", ".rs", ".java",
                 ".kt", ".kts", ".scala", ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs",
                 ".dart", ".ex", ".exs", ".erl", ".hs", ".ml", ".clj", ".tf", ".hcl", ".gradle"}
# What is run by name, so its first bytes carry meaning: a shell or the kernel reads the #! line of these
# (and of a file with no suffix); a shell also reads a BOM at the start of a .sh as part of the first command.
RUN_SUFFIXES = {".sh", ".bash", ".zsh", ".py"}
SHELL_SUFFIXES = {".sh", ".bash", ".zsh"}
BOM = "\ufeff"  # named, never a literal: an editor or a paste can drop the invisible character without a visible diff
# How PyYAML 6 (YAML 1.1) types a plain scalar, so the built-in reader agrees: its implicit-resolver patterns,
# copied, and its constructors' arithmetic. Booleans come in exactly three spellings (yEs is text); a date is
# only YYYY-MM-DD (2026-9-30 is text); 2026.09.30 and 1e3 are text.
YAML_BOOLS = {w: v for words, v in ((("yes", "true", "on"), True), (("no", "false", "off"), False))
              for word in words for w in (word, word.capitalize(), word.upper())}
YAML_NULLS = {"", "~", "null", "Null", "NULL"}
YAML_INT = re.compile(r"[-+]?0b[0-1_]+|[-+]?0[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+"
                      r"|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+")
YAML_FLOAT = re.compile(r"[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?"
                        r"|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)")
YAML_DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
YAML_DATETIME = re.compile(r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt]|[ \t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]*)?"
                           r"(?:[ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?")
# YAML's double-quote escapes, every value written as an escape: an invisible literal (U+2028 once stood here)
# can be dropped by an editor or a paste without a visible diff.
YAML_ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f", "r": "\r",
                "e": "\x1b", " ": " ", '"': '"', "\\": "\\", "/": "/", "N": "\x85", "_": "\xa0",
                "L": "\N{LINE SEPARATOR}", "P": "\N{PARAGRAPH SEPARATOR}"}
YAML_ESCAPE_CODES = {"x": 2, "u": 4, "U": 8}
# The built-in reader's bounds, each refused by name: a real frontmatter is a few hundred characters.
FRONTMATTER_LIMIT = 100_000
KEY_LIMIT = 128
# What the built-in reader refuses before it reads: a tab, a character YAML reads as a line break other than LF
# (U+2028, U+2029, NEL, a CR without LF), a BOM, and anything YAML does not count as printable.
_SCREEN = re.compile("[\t\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}\x85\N{ZERO WIDTH NO-BREAK SPACE}]|\r(?!\n)"
                     "|[^\n\r\x20-\x7e\xa0-" + chr(0xD7FF) + chr(0xE000) + "-" + chr(0xFFFD)
                     + chr(0x10000) + "-" + chr(0x10FFFF) + "]")
_KEY_LINE = re.compile(r"""(?:([A-Za-z0-9_][A-Za-z0-9_-]*)|"([^"\\]*)"|'([^']*)')( *):(.*)""", re.S)
_BLOCK_HEADER = re.compile(r"[|>](?:[+-][1-9]?|[1-9][+-]?)?(?: +#.*)?", re.S)
_HEX = set("0123456789abcdefABCDEF")
# A bundled path, written bare or with a ./ prefix; ../ and foo/scripts/ stay out.
REF_PATTERN = re.compile(r"(?<![\w/.-])(?:\./)?((?:references|scripts|assets)/[\w.\-/]*[\w])")
WHEN_CUE = re.compile(r"\b(use (this skill |it )?(when|whenever|while|before|after|for|to)|trigger(s|ed)?|apply when"
                      r"|invoke when)\b", re.I)
STALE_MARKERS = {
    "/mnt/skills": "a hosted sandbox's path that other surfaces do not have",
    "/mnt/user-data": "a hosted sandbox's path that other surfaces do not have",
    "/home/claude": "a hosted sandbox's path that other surfaces do not have",
    "str_replace": "a tool name only some surfaces use; say 'edit in place'",
}
# One person's profile folder: breaks on every other machine and discloses the
# account name wherever the skill is shared. Placeholders such as <you> pass.
# Case-insensitive: Windows paths are, and shells often print c:/users/<name>.
# A name starts with a letter or digit, so an elided c:/users/... is no one's.
USER_PATH = re.compile(r"(?:[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}|/Users/|/home/)"
                       r"(?!(?:claude|Public|Default|All Users)\b)([A-Za-z0-9][A-Za-z0-9._-]*)", re.I)


def _parse_frontmatter(text):
    """Return (dict, body_text) or raise ValueError: the frontmatter as PyYAML reads it when PyYAML is
    installed, else as the built-in reader reads its subset (_mini_yaml). Either way one ValueError whose
    message starts with "frontmatter" or names the missing ---, never a traceback."""
    if not text.startswith("---"):
        raise ValueError("no YAML frontmatter found: SKILL.md must start with a --- line")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("frontmatter is not closed: put a --- line after it")
    raw, body = m.group(1), m.group(2)
    try:
        import yaml  # type: ignore
    except ImportError:
        try:
            data = _mini_yaml(raw)
        except ValueError:
            raise
        except Exception as e:  # a backstop: the reader refuses by name, so this is a bug to report, not a verdict
            raise ValueError(f"frontmatter could not be read by the built-in reader ({type(e).__name__}); "
                             "install PyYAML (pip install pyyaml), which reads it") from None
    else:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:  # what an upload would refuse too: one ERROR line, not a traceback
            raise ValueError(f"frontmatter is not valid YAML: {' '.join(str(e).split())}") from None
        except (ValueError, TypeError, OverflowError, RecursionError) as e:  # a date or number YAML cannot make
            raise ValueError(f"frontmatter is not valid YAML: {' '.join(str(e).split())}") from None
        except Exception as e:  # a tag PyYAML cannot build (!!bool maybe, an empty !!int): named, as the built-in path does
            raise ValueError(f"frontmatter is not valid YAML: PyYAML could not build a value from it "
                             f"({type(e).__name__}); check any !! tag, or drop it") from None
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping of name, description and the other keys")
    return data, body


def _invalid(what):
    """What YAML itself refuses: PyYAML refuses it too."""
    return ValueError(f"frontmatter is not valid YAML: {what}")


def _unsupported(key, shape, instead):
    """A shape outside the built-in reader's subset: refused by name, with the way to write it."""
    return ValueError(f"frontmatter uses {shape} in the value of {key}, which the built-in reader does not take; "
                      f"{instead}, or install PyYAML (pip install pyyaml)")


def _refused(where, what, instead):
    """A line the built-in reader does not take, named with its SKILL.md line."""
    return ValueError(f"frontmatter {where} {what}, which the built-in reader does not take; {instead}, or install "
                      f"PyYAML (pip install pyyaml)")


def _kind(value):
    """A value that is not text, named as YAML typed it."""
    import datetime
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, (datetime.date, datetime.datetime)):
        return "a date"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "a mapping"
    return type(value).__name__


def _shown(value):
    """A frontmatter value as a message shows it: str(value), or, for a number past Python's 4,300-digit limit
    for printing (hex, octal and sexagesimal numbers are built past it), its size instead of its digits."""
    try:
        return str(value)
    except ValueError:
        if not isinstance(value, int):
            return "too long to show"
        n = abs(value)
        digits = max(1, int(n.bit_length() * 0.30102999566398120))  # log10(2): the count, or one short
        return f"{digits + (n >= 10 ** digits):,} digits long"


def _resolve(text, what):
    """A plain scalar as PyYAML 6 types it (its resolver patterns and its constructors' arithmetic): null, a
    YAML 1.1 boolean, an int, a float, a date, else the text. What PyYAML would fail to construct (0x_,
    2026-13-40, =) and a date with a time are refused by name."""
    if text in YAML_NULLS:
        return None
    if text in YAML_BOOLS:
        return YAML_BOOLS[text]
    if text in ("=", "<<"):
        raise _invalid(f"{what} is {text}, which YAML reads as a {'value' if text == '=' else 'merge'} key, not text; "
                       "quote it")
    try:
        if YAML_INT.fullmatch(text):
            value, sign = text.replace("_", ""), 1
            if value[0] == "-":
                sign = -1
            if value[0] in "+-":
                value = value[1:]
            if value == "0":
                return 0
            if value.startswith("0b"):
                return sign * int(value[2:], 2)
            if value.startswith("0x"):
                return sign * int(value[2:], 16)
            if value[0] == "0":
                return sign * int(value, 8)
            if ":" in value:
                total, base = 0, 1
                for digit in reversed([int(part) for part in value.split(":")]):
                    total += digit * base
                    base *= 60
                return sign * total
            return sign * int(value)
        if YAML_FLOAT.fullmatch(text):
            value, sign = text.replace("_", "").lower(), 1
            if value[0] == "-":
                sign = -1
            if value[0] in "+-":
                value = value[1:]
            if value == ".inf":
                return sign * float("inf")
            if value == ".nan":
                return float("nan")
            if ":" in value:
                total, base = 0.0, 1
                for digit in reversed([float(part) for part in value.split(":")]):
                    total += digit * base
                    base *= 60
                return sign * total
            return sign * float(value)
    except (ValueError, OverflowError):
        raise _invalid(f"{what} is {text[:40]}, which YAML takes for a number but cannot read as one; quote it") from None
    m = YAML_DATE.fullmatch(text)
    if m:
        import datetime
        try:
            return datetime.date(*(int(x) for x in m.groups()))
        except ValueError as e:
            raise _invalid(f"{what} is {text}, which YAML reads as a date that does not exist ({e}); quote it") from None
    if YAML_DATETIME.fullmatch(text):
        raise ValueError(f"frontmatter uses a date with a time ({text}) in {what}, which the built-in reader does not "
                         "take; quote it, or install PyYAML (pip install pyyaml)")
    return text


def _screen(raw):
    """Refuse, by name and line, what the built-in reader never reads: a frontmatter past FRONTMATTER_LIMIT, a
    tab, a line break other than LF or CRLF, a BOM, and any character YAML does not count as printable."""
    if len(raw) > FRONTMATTER_LIMIT:
        raise ValueError(f"frontmatter is {len(raw):,} characters; the built-in reader takes at most "
                         f"{FRONTMATTER_LIMIT:,} (a real one is a few hundred): shorten it, or install PyYAML "
                         "(pip install pyyaml)")
    m = _SCREEN.search(raw)
    if not m:
        return
    at = m.start()
    where = f"line {raw.count(chr(10), 0, at) + 2}"
    line_start = raw.rfind("\n", 0, at) + 1
    before = raw[line_start:at]
    ch = m.group()
    if ch == "\t":
        key = re.fullmatch(r" *([A-Za-z0-9_][A-Za-z0-9_-]*) *: *", before)
        if key:
            raise _invalid(f"a tab after '{key.group(1)}:' cannot start a value; use spaces")
        if not before.strip(" "):
            raise ValueError(f"frontmatter {where} starts with a tab, which YAML does not take as indentation (and "
                             "the built-in reader takes no tab); use spaces")
        # Not "YAML refuses": YAML reads a tab inside quotes, a block or a comment; this reader takes none.
        raise ValueError(f"frontmatter {where} holds a tab, which the built-in reader does not take (it takes no tab "
                         "anywhere); use spaces, or \\t inside double quotes, or install PyYAML (pip install pyyaml)")
    if ch == "\r":
        raise _refused(where, "holds a carriage return without a line feed", "save the file with LF or CRLF line ends")
    if ch == BOM:  # PyYAML keeps one inside a value as text
        raise _refused(where, "holds a byte-order mark (U+FEFF)", "remove it, or write it as \\uFEFF inside double quotes")
    breaks = {"\N{LINE SEPARATOR}": ("a Unicode line separator, U+2028", "\\L"),
              "\N{PARAGRAPH SEPARATOR}": ("a Unicode paragraph separator, U+2029", "\\P"),
              "\x85": ("a next-line control character, U+0085", "\\N")}
    if ch in breaks:
        name, escape = breaks[ch]
        raise _refused(where, f"holds a line break YAML reads ({name})",
                       f"remove it, or write it as {escape} inside double quotes")
    raise _invalid(f"{where} holds the character U+{ord(ch):04X}, which YAML does not take in a document; remove it, "
                   "or write it as an escape inside double quotes")


class _Reader:
    """The built-in frontmatter reader: a small, named subset of YAML, read as PyYAML 6 reads it, in one pass
    (every line and character is read a bounded number of times; nothing recurses past one nested mapping).

    Taken: top-level key: value lines (a plain key of letters, digits, _ and -, or a quoted key without
    escapes, up to 128 characters); plain, single- and double-quoted values, on the key's line or the lines
    below it, continued on lines indented past the key; > and | blocks with their chomping and indent
    indicators and a comment after the header, the header on the key's line; one-line or continued [lists]
    and {maps} of scalars, each map entry a key: value pair; block lists of one-line scalar items, at the
    key's own indent or indented; one level of nested mapping holding the same values; comments; empty
    values and ~, null, and typed values as PyYAML types them. It takes no tab anywhere, not even inside
    quotes, a block or a comment (_screen). Among what it refuses by name: a key such as x.y:, ~: or one
    holding a space, {a}, and a quote continued at column 0 (not indented past its key).

    Everything else is a ValueError whose message starts with "frontmatter" and names the shape: what YAML
    refuses (PyYAML refuses it too) or what lies outside the subset (install PyYAML to read it). The
    invariant, held by a seeded differential test: for any input the result equals PyYAML's, type and
    value, or the input is refused by name."""

    def __init__(self, raw):
        _screen(raw)
        self.text = raw.replace("\r\n", "\n")
        self.lines = self.text.split("\n")
        self.n = len(self.lines)
        self.starts, pos = [], 0
        for line in self.lines:
            self.starts.append(pos)
            pos += len(line) + 1

    # -- lines ---------------------------------------------------------------------------------------------

    def col(self, i):
        line = self.lines[i]
        return len(line) - len(line.lstrip(" "))

    def idle(self, i):
        """A blank line or a comment line."""
        rest = self.lines[i].lstrip(" ")
        return not rest or rest[0] == "#"

    def skip(self, i):
        while i < self.n and self.idle(i):
            i += 1
        return i

    def where(self, i):
        return f"line {i + 2}"  # the SKILL.md line: the frontmatter starts on line 2

    def line_of(self, p):
        return bisect.bisect_right(self.starts, p) - 1

    def eol(self, i):
        return self.starts[i] + len(self.lines[i])

    def bound(self, end_line):
        """The text offset where the value whose region ends before end_line stops being read."""
        return self.starts[end_line] if end_line < self.n else len(self.text)

    def region(self, i, k):
        """The first line after line i that is not blank and not indented past column k: a value that starts
        on line i under a key at column k is read no further."""
        j = i + 1
        while j < self.n and (not self.lines[j].strip(" ") or self.col(j) > k):
            j += 1
        return j

    # -- structure -----------------------------------------------------------------------------------------

    def document(self):
        i = self.skip(0)
        if i == self.n:
            return None  # only comments or nothing: PyYAML reads None
        data, i = self.mapping(i, self.col(i), 0)
        if i < self.n:
            raise _invalid(f"{self.where(i)} is indented less than the first key; line the keys up")
        return data

    def mapping(self, i, ind, depth):
        data = {}
        while True:
            i = self.skip(i)
            if i >= self.n or self.col(i) < ind:
                return data, i
            if self.col(i) > ind:
                raise _invalid(f"{self.where(i)} ({self.lines[i].strip()[:30]!r}) is indented past the keys above it "
                               "but continues no value; line it up with them")
            key, label, rest = self.key(i, ind)
            data[key], i = self.value(i, ind, rest, label, depth)

    def key(self, i, c):
        line = self.lines[i][c:]
        if line == "-" or line.startswith("- "):
            raise ValueError(f"frontmatter {self.where(i)} is a list item (- ...) where a key belongs; a list goes "
                             "under its key, as 'key:' and then '- item' lines")
        if line == "?" or line.startswith("? "):
            raise _unsupported("this mapping", "a complex key (? )", "write the key plainly")
        if c == 0 and line[:3] in ("---", "...") and line[3:4] in ("", " "):
            raise _refused(self.where(i), f"is a document marker ({line[:3]})", "keep one document between the --- lines")
        m = _KEY_LINE.fullmatch(line)
        if not m:
            raise _refused(self.where(i), f"is not a 'key: value' line ({line[:40]!r})",
                           "write a key of letters, digits, _ and -, or a quoted key without escapes, then ': '")
        plain, dq, sq, _, rest = m.groups()
        label = plain if plain is not None else dq if dq is not None else sq
        if len(label) > KEY_LIMIT:
            raise _refused(self.where(i), f"has a key of {len(label)} characters", f"keep keys to {KEY_LIMIT}")
        if rest and rest[0] != " ":
            raise _invalid(f"'{label}:{rest[:1]}' needs a space after the colon")
        key = _resolve(plain, f"the key {plain}") if plain is not None else label
        return key, label, rest

    def value(self, i, k, rest, label, depth):
        v = rest.lstrip(" ")
        if not v or v[0] == "#":
            return self.below(i, k, label, depth)
        return self.node(i, self.eol(i) - len(v), k, label, True)

    def below(self, i, k, label, depth):
        """The value of a key with nothing after its colon: null, a block list, a nested mapping, or a scalar
        that starts on a line below."""
        j = self.skip(i + 1)
        if j >= self.n:
            return None, j
        c = self.col(j)
        line = self.lines[j][c:]
        if (line == "-" or line.startswith("- ")) and c >= k:
            return self.block_list(j, k, c, label)
        if c <= k:
            return None, j
        m = _KEY_LINE.fullmatch(line)
        if m and (not m.group(5) or m.group(5)[0] == " "):
            if depth >= 1:
                raise _unsupported(label, "a mapping inside a nested mapping",
                                   "keep one level of keys under a top-level key (metadata: and then key: value lines)")
            return self.mapping(j, c, depth + 1)
        return self.node(j, self.starts[j] + c, k, label, False)

    def block_list(self, j, k, ic, label):
        """Items '- value' at column ic under a key at column k (ic == k is YAML's indentless list), each one
        scalar on its own line."""
        items = []
        while True:
            rest = self.lines[j][ic + 1:]
            v = rest.lstrip(" ")
            items.append(None if not v or v[0] == "#" else self.item(j, self.eol(j) - len(v), v, label))
            nxt = self.skip(j + 1)
            if nxt >= self.n:
                return items, nxt
            c = self.col(nxt)
            line = self.lines[nxt][c:]
            if c == ic and (line == "-" or line.startswith("- ")):
                j = nxt
                continue
            if c <= k:
                return items, nxt
            if c > ic:
                raise _unsupported(label, "a list item that goes on over more lines (or holds a nested list)",
                                   "write each item as one plain or quoted value after '- '")
            raise _invalid(f"{self.where(nxt)} ({line[:30]!r}) lines up with no key or item of {label}")

    def item(self, j, pos, v, label):
        one = "write each item as one plain or quoted value after '- '"
        ch = v[0]
        if (ch == "-" and v[1:2] in ("", " ")) or ch == "[":
            raise _unsupported(label, "a list inside a list", one)
        if ch == "{":
            raise _unsupported(label, "a list of mappings (- {key: value})", one)
        if ch in "|>" and _BLOCK_HEADER.fullmatch(v.rstrip(" ")):
            raise _unsupported(label, f"a {ch} block as a list item", one)
        self.named_indicator(ch, label)
        eol = self.eol(j)
        if ch in "'\"":
            value, p = self.quoted(p=pos, bound=eol, label=label, item=True)
            if self.text[p:eol].strip(" ").startswith(":"):
                raise _unsupported(label, "a list of mappings (- key: value)", one)
            self.after(p, eol, label, "quote")
            return value
        self.plain_start(v, label)
        value, p = self.plain(pos, eol, 0, False)
        if p < eol and self.text[p] == ":":
            raise _unsupported(label, "a list of mappings (- key: value)", one)
        return _resolve(value, f"an item of {label}")

    def node(self, j, pos, k, label, inline):
        """A value that starts at text offset pos on line j, under a key at column k."""
        text = self.text
        ch = text[pos]
        v = text[pos:self.eol(j)].rstrip(" ")
        if ch in "|>" and _BLOCK_HEADER.fullmatch(v):
            if not inline:
                raise _unsupported(label, f"a {ch} block that starts on the line below its key", f"write {ch} after the key")
            return self.block(j, k, v)
        if ch in "[{":
            if not inline:
                raise _unsupported(label, f"a {ch} that starts on the line below its key", "write it after the key")
            end_line = self.region(j, k)
            value, p = self.flow(pos, self.bound(end_line), label)
            return value, self.finish(p, end_line, label, "]" if ch == "[" else "}")
        self.named_indicator(ch, label)
        end_line = self.region(j, k)
        if ch in "'\"":
            value, p = self.quoted(p=pos, bound=self.bound(end_line), label=label)
            return value, self.finish(p, end_line, label, "quote")
        self.plain_start(v, label)
        value, p = self.plain(pos, self.bound(end_line), k + 1, False)
        if p < self.bound(end_line) and text[p] == ":":
            if not inline:
                raise _unsupported(label, "a nested key that is not a plain name",
                                   "write the nested key as letters, digits, _ and -, or quote the value")
            raise _invalid(f"the value of {label} holds an unquoted ': ' (or a colon ending the value), which YAML "
                           "reads as a second key; quote the value or write it as a > block")
        return _resolve(value, f"the value of {label}"), self.finish(p, end_line, label, None)

    def named_indicator(self, ch, label):
        if ch == "&":
            raise _unsupported(label, "a YAML anchor (&)", "write the value plainly")
        if ch == "*":
            raise _unsupported(label, "a YAML alias (*)", "write the value out in full")
        if ch == "!":
            raise _unsupported(label, "a YAML tag (!)", "drop the tag")

    def plain_start(self, v, label):
        """A plain value must not open with a character YAML reserves (N3: `code`, @, %, - , a lone |)."""
        ch, nxt = v[0], v[1:2]
        if ch in "`@%,]}|>" or (ch in "-?:" and nxt in ("", " ")):
            raise _invalid(f"the value of {label} starts with '{ch}', which YAML reserves at the start of "
                           "a plain value; quote the value")
        if ch in "?:":
            raise _unsupported(label, f"a plain value that starts with {ch}", "quote the value")

    def after(self, p, eol, label, what):
        """Only a comment may follow a closing quote or bracket on its line."""
        tail = self.text[p:eol]
        rest = tail.strip(" ")
        if not rest:
            return
        if rest[0] == "#":
            if tail[0] == " ":
                return
            raise _unsupported(label, f"a # right after the closing {what}", "put a space before the #")
        noun = "quotes" if what == "quote" else "brackets"
        raise _invalid(f"the value of {label} has text after its closing {what} ({rest[:20]!r}); put it inside the "
                       f"{noun} or drop them")

    def finish(self, p, end_line, label, what):
        """The value ended at offset p: the rest of its line holds at most a comment, and the lines left in its
        region are blank or comments. Returns the line to go on from."""
        if p >= self.bound(end_line):
            return end_line
        li = self.line_of(p)
        if what is not None:
            self.after(p, self.eol(li), label, what)
        for i in range(li + 1, end_line):
            if not self.idle(i):
                raise _invalid(f"{self.where(i)} ({self.lines[i].strip()[:30]!r}) is indented under {label}, whose "
                               "value has ended; quote the whole value, or line the line up with the keys")
        return end_line

    # -- scalars, ported from PyYAML 6's scanner -------------------------------------------------------------

    def unclosed(self, label, what, bound, item):
        if item:
            return _unsupported(label, f"an item that opens {what} and does not close it on its line",
                                "close it on the item's line")
        if bound >= len(self.text):
            return _invalid(f"the value of {label} opens {what} it does not close")
        return _refused(f"line {self.line_of(bound) + 2}",
                        f"is not indented past the key {label}, whose value opens {what} it does not close before it",
                        f"close it, or indent the lines {what} runs over past the key")

    def quoted(self, p, bound, label, item=False):
        """A single- or double-quoted scalar from offset p, read no further than bound: '' is one quote inside
        single quotes; a backslash escapes inside double quotes, a line break included; a line break folds to a
        space and a blank line to a newline. Returns (value, offset after the closing quote)."""
        text = self.text
        quote = text[p]
        double = quote == '"'
        p += 1
        chunks = []
        while True:
            while True:
                start = p
                while p < bound and text[p] not in "'\"\\ \n":
                    p += 1
                if p > start:
                    chunks.append(text[start:p])
                ch = text[p] if p < bound else "\0"
                nxt = text[p + 1] if p + 1 < bound else "\0"
                if not double and ch == "'" and nxt == "'":
                    chunks.append("'")
                    p += 2
                elif (double and ch == "'") or (not double and ch in '"\\'):
                    chunks.append(ch)
                    p += 1
                elif double and ch == "\\":
                    if nxt in YAML_ESCAPES:
                        chunks.append(YAML_ESCAPES[nxt])
                        p += 2
                    elif nxt in YAML_ESCAPE_CODES:
                        width = YAML_ESCAPE_CODES[nxt]
                        digits = text[p + 2:min(p + 2 + width, bound)]
                        if len(digits) != width or not set(digits) <= _HEX:
                            raise _invalid(f"the value of {label} holds the escape \\{nxt}{digits[:width]}, which needs "
                                           f"{width} hexadecimal digits")
                        code = int(digits, 16)
                        if code > 0x10FFFF:
                            raise _invalid(f"the value of {label} holds the escape \\{nxt}{digits}, past the last "
                                           "Unicode character (U+10FFFF)")
                        chunks.append(chr(code))
                        p += 2 + width
                    elif nxt == "\n":  # an escaped line break: the break and the next line's indent are dropped
                        breaks, p = self.quoted_breaks(p + 2, bound)
                        chunks.extend(breaks)
                    elif nxt == "\0":
                        raise self.unclosed(label, "a quote", bound, item)
                    else:
                        raise _invalid(f"the value of {label} holds the escape \\{nxt}, which YAML does not know; write "
                                       "\\\\ for a backslash, or use single quotes, where a backslash is plain text")
                else:
                    break
            if p < bound and text[p] == quote:
                return "".join(chunks), p + 1
            start = p
            while p < bound and text[p] == " ":
                p += 1
            if p >= bound:
                raise self.unclosed(label, "a quote", bound, item)
            if text[p] == "\n":
                breaks, p = self.quoted_breaks(p + 1, bound)
                chunks.extend(breaks or [" "])
            else:
                chunks.append(text[start:p])

    def quoted_breaks(self, p, bound):
        breaks = []
        while True:
            while p < bound and self.text[p] == " ":
                p += 1
            if p < bound and self.text[p] == "\n":
                breaks.append("\n")
                p += 1
            else:
                return breaks, p

    def plain(self, p, bound, indent, flow):
        """A plain scalar from offset p, read no further than bound: cut at ': ' (and, inside [ ] or { }, at
        , ? [ ] { }) and at ' #'; lines folded as PyYAML folds them. Returns (text, offset where it stopped)."""
        text = self.text
        stops = ",?[]{}" if flow else ""
        after_colon = " \n" + (",[]{}" if flow else "")
        chunks, spaces = [], []
        while True:
            if p < bound and text[p] == "#":
                break
            start = p
            while p < bound:
                ch = text[p]
                if ch in " \n" or ch in stops or (ch == ":" and (p + 1 >= bound or text[p + 1] in after_colon)):
                    break
                p += 1
            if p == start:
                break
            chunks.extend(spaces)
            chunks.append(text[start:p])
            spaces, p, column = self.plain_spaces(p, bound)
            if not spaces or (p < bound and text[p] == "#") or (not flow and column < indent):
                break
        return "".join(chunks), p

    def plain_spaces(self, p, bound):
        text = self.text
        start = p
        while p < bound and text[p] == " ":
            p += 1
        if p < bound and text[p] == "\n":
            p += 1
            column, breaks = 0, []
            while p < bound and text[p] in " \n":
                if text[p] == " ":
                    column += 1
                else:
                    breaks.append("\n")
                    column = 0
                p += 1
            return breaks or [" "], p, column
        return ([text[start:p]] if p > start else []), p, len(text)

    def flow(self, pos, bound, label):
        """A [list] or {map} of scalars from offset pos, read no further than bound; a comment inside it, a
        collection inside it, or a key without ': ' is refused by name."""
        text = self.text
        opener = text[pos]
        closer = "]" if opener == "[" else "}"
        out = [] if opener == "[" else {}
        p = pos + 1
        while True:
            p = self.flow_gap(p, bound, label, opener, closer)
            ch = text[p] if p < bound else "\0"
            if ch == "\0":
                raise self.unclosed(label, f"a {opener}", bound, False)
            if ch == closer:
                return out, p + 1
            if ch == ",":
                raise _invalid(f"the value of {label} has an empty item (a comma with nothing before it) inside "
                               f"{opener} {closer}")
            if opener == "[":
                item, p = self.flow_scalar(p, bound, label)
                p = self.flow_gap(p, bound, label, opener, closer)
                if p < bound and text[p] == ":":
                    raise _unsupported(label, "a key: value pair inside [ ]", "quote the item")
                out.append(item)
            else:
                start = p
                key, p = self.flow_scalar(p, bound, label, key=True)
                while p < bound and text[p] == " ":
                    p += 1
                if p >= bound or text[p] != ":" or "\n" in text[start:p]:
                    raise _unsupported(label, "a key without ': ' on its line inside { } ({a} or {a:1})",
                                       "write key: value pairs")
                p = self.flow_gap(p + 1, bound, label, opener, closer)
                value = None
                if p < bound and text[p] not in ",}":
                    value, p = self.flow_scalar(p, bound, label)
                    p = self.flow_gap(p, bound, label, opener, closer)
                    if p < bound and text[p] == ":":
                        raise _invalid(f"the value of {label} holds a second ':' in one pair inside {{ }}; quote the value")
                out[key] = value
            ch = text[p] if p < bound else "\0"
            if ch == ",":
                p += 1
            elif ch not in (closer, "\0"):
                raise _invalid(f"the value of {label} holds {text[p:p + 12]!r} after an item inside {opener} {closer}; "
                               "separate the items with commas")

    def flow_gap(self, p, bound, label, opener, closer):
        while p < bound and self.text[p] in " \n":
            p += 1
        if p < bound and self.text[p] == "#":
            raise _unsupported(label, f"a comment inside {opener} {closer}", "move it after the closing bracket")
        return p

    def flow_scalar(self, p, bound, label, key=False):
        text = self.text
        ch = text[p]
        if ch in "'\"":
            return self.quoted(p=p, bound=bound, label=label)
        if ch in "[{":
            raise _unsupported(label, "a flow collection inside another ([a, [b]])", "write one flat list")
        self.named_indicator(ch, label)
        nxt = text[p + 1] if p + 1 < bound else "\0"
        if ch in "?:":
            raise _unsupported(label, f"an item that starts with {ch} inside [ ] or {{ }}", "quote the item")
        if ch in "-,]}|>'\"%@`#" and not (ch == "-" and nxt not in "\0 \n"):
            raise _invalid(f"an item of {label} starts with {ch}, which YAML reserves at the start of a plain value; "
                           "quote the item")
        value, p = self.plain(p, bound, 0, True)
        return _resolve(value, f"the {'key' if key else 'item'} {value[:40]} of {label}"), p

    def block(self, j, k, header):
        """A > or | block whose header ends line j, under a key at column k: PyYAML's scan_block_scalar, line
        for line (indent found from the first non-blank line or given by the indicator, a > joining lines with
        a space, - dropping the final line breaks and + keeping them all). Returns (text, next line)."""
        text, n = self.text, len(self.text)
        folded = header[0] == ">"
        chomp, increment = None, None
        for ch in header[1:3]:
            if ch in "+-":
                chomp = ch == "+"
            elif ch.isdigit():
                increment = int(ch)
        p = self.starts[j + 1] if j + 1 < self.n else n
        min_indent = k + 1
        column = 0
        if increment is None:
            breaks, max_indent = [], 0
            while p < n and text[p] in " \n":
                if text[p] == "\n":
                    breaks.append("\n")
                    column = 0
                else:
                    column += 1
                    max_indent = max(max_indent, column)
                p += 1
            indent = max(min_indent, max_indent)
        else:
            indent = min_indent + increment - 1
            breaks, p, column = self.block_breaks(p, column, indent)
        chunks, line_break = [], ""
        while column == indent and p < n:
            chunks.extend(breaks)
            leading_non_space = text[p] != " "
            end = text.find("\n", p)
            end = n if end < 0 else end
            chunks.append(text[p:end])
            p = end
            line_break = "\n" if p < n else ""
            if p < n:
                p += 1
                column = 0
            breaks, p, column = self.block_breaks(p, column, indent)
            if column == indent and p < n:
                if folded and line_break == "\n" and leading_non_space and text[p] != " ":
                    if not breaks:
                        chunks.append(" ")
                else:
                    chunks.append(line_break)
            else:
                break
        if chomp is not False:
            chunks.append(line_break)
        if chomp is True:
            chunks.extend(breaks)
        return "".join(chunks), (self.n if p >= n else self.line_of(p))

    def block_breaks(self, p, column, indent):
        text, n = self.text, len(self.text)
        breaks = []
        while column < indent and p < n and text[p] == " ":
            p += 1
            column += 1
        while p < n and text[p] == "\n":
            breaks.append("\n")
            p += 1
            column = 0
            while column < indent and p < n and text[p] == " ":
                p += 1
                column += 1
        return breaks, p, column


def _mini_yaml(raw):
    """The frontmatter as the built-in reader reads it (see _Reader): exactly what PyYAML returns, type and
    value, or a ValueError naming the shape it refuses. Never another exception."""
    return _Reader(raw).document()


def _carries_payload(path, data):
    """A script that starts with #! and holds a NUL byte carries a binary payload after its text
    (a self-extracting archive: tar and gzip bytes always hold a NUL), which the packager stores
    byte-for-byte; it is not held to UTF-8. Python must be UTF-8 to run, so .py never is."""
    return path.suffix.lower() != ".py" and data.startswith(b"#!") and b"\0" in data


def _longer_name(text, start, ref, names):
    """The shipped file meant by a reference cut short at a space: names (longest first) holds every
    shipped file's relative path; the one that starts with ref and that the text, or its %20-decoded
    form, goes on with from start is it. Otherwise ref as matched."""
    tail = text[start:start + 512].split("\n", 1)[0]
    tails = (tail, unquote(tail))
    for name in names:
        if len(name) > len(ref) and name.startswith(ref) and any(t.startswith(name) for t in tails):
            return name
    return ref


def _unreadable(rel, e):
    """The ERROR line for a file the operating system would not let this run read."""
    return (f"{rel} could not be read ({e.strerror or e}); close the program holding it open, or check "
            "its permissions, and run again")


def _read_utf8(path, rel, errors):
    """Text of path, or None after an ERROR line naming the file and the bad byte, or why it
    could not be read (held open with no share mode, no permission)."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(f"{rel} is not UTF-8 ({e.reason} at byte {e.start}); save it as UTF-8")
    except OSError as e:
        errors.append(_unreadable(rel, e))
    return None


# Every released version opens its docstring with this line; only the owner's name in it has changed
# (1.1: "plus sc2's standards."), and the words before "upload rules" (1.4's tenth review dropped the base
# workflow's name; the eleventh named the Agent Skills specification's rules), and a copy may start the
# docstring on the opening quotes' line.
_SIGNATURE = re.compile(r"^(?:\"\"\"|''')?\s*Skill validator — the (?:(?:base [\w-]+'s )?upload rules|Agent Skills "
                        r"specification's rules) plus .{1,40} standards\.$")


def _is_this_validator(path):
    """This file names the markers it hunts; a copy of it, of any released version or edited, opens
    with the signature line and is exempt; another skill's file of the same name does not and is checked."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = [f.readline().strip() for _ in range(4)]
    except OSError:
        return False
    return any(_SIGNATURE.match(line) for line in head)


def _inside(path, folder):
    """Is path the folder itself or somewhere inside it, links followed on both sides?"""
    p, f = (os.path.normcase(os.path.realpath(x)) for x in (path, folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def archive_cut(real, root, out, name, is_dir, skill=None):
    """Must a walk of the skill at root not take this link, because it reaches the archives
    package_dual.py writes to out? The output folder and any folder above it are cut; when out
    is a folder of its own, anything in it; when the archives go beside the skill, only the
    archives themselves ({name}.skill, {name}-v*.zip): a LICENSE linked from the repository
    root stays. Beside means out holds the skill's real folder, or the folder that holds
    skill, the path as given (a link to the skill keeps its archives beside the link).
    Shared by the packager and this validator, so both read the same skill."""
    if out is None or _inside(real, root):
        return False
    if _inside(out, real):
        return True
    beside = _inside(root, out) or (skill is not None and _inside(os.path.dirname(os.path.abspath(skill)), out))
    if not beside:
        return _inside(real, out)
    if is_dir or os.path.normcase(os.path.dirname(real)) != os.path.normcase(os.path.realpath(out)):
        return False
    base = os.path.basename(real)
    return os.path.normcase(base) == os.path.normcase(name + ".skill") or fnmatch.fnmatch(base, name + "-v*.zip")


def _tree(skill, out=None, problems=None):
    """Every path under the skill as the packager reads it: links of every kind followed
    alike, a link back to a folder already on the way down (a loop) or out to the archives
    (archive_cut, when the packager names its output folder) cut, and folders that never
    ship (__pycache__ and the like, dot-folders such as .git or the .old-* a locked deploy
    leaves, *-workspace folders, evals/ and tests/ at the root) listed but not entered.
    A folder this run may not list is one line in problems (an ERROR), not a traceback."""
    root = os.path.realpath(skill)
    found = []

    def walk(folder, chain, top):
        try:
            children = sorted(folder.iterdir())
        except OSError as e:
            if problems is not None:
                rel = "." if folder == skill else folder.relative_to(skill).as_posix()
                problems.append(f"{rel}/ could not be listed ({e.strerror or e}); check its permissions")
            return
        for child in children:
            real = os.path.realpath(child)
            is_dir = child.is_dir()
            if archive_cut(real, root, out, skill.name, is_dir, skill):
                continue
            found.append(child)
            if is_dir:
                key = os.path.normcase(real)
                if key in chain or child.name in JUNK_DIRS or child.name.startswith(".") \
                        or child.name.endswith("-workspace") or (top and child.name in ROOT_SKIP_DIRS):
                    continue
                walk(child, chain | {key}, False)

    walk(skill, frozenset({os.path.normcase(root)}), True)
    return found


def _is_test_file(rel):
    """Test code names fixtures that need not exist, so it skips the missing-reference check."""
    return "tests" in rel.parts[:-1] or any(fnmatch.fnmatchcase(rel.name, pat)
                                            for pat in ("*_selftest.py", "test_*.py", "*_test.py"))


SPEC = "the Agent Skills specification"


def _spec_shapes(fm):
    """The optional keys' shapes, by the Agent Skills specification (https://agentskills.io/specification, read
    2026-09-30): metadata is "a map from string keys to string values"; allowed-tools is "a space-separated
    string"; license names a license or a bundled license file; compatibility "Must be 1-500 characters if
    provided" (over 500 is checked in check()). The page says none of these as "should", so each is an ERROR line."""
    errors = []
    if "metadata" in fm:
        meta = fm["metadata"]
        if not isinstance(meta, dict):
            kind = "text" if isinstance(meta, str) else _kind(meta)
            errors.append(f"metadata is {kind}, not a mapping: {SPEC} takes key: value lines under it, each value "
                          "text")
        else:
            for k, v in meta.items():
                if not isinstance(k, str):
                    errors.append(f"metadata key {_shown(k)} is {_kind(k)}, not text: {SPEC} takes text keys; "
                                  "quote it")
                elif not isinstance(v, str):
                    advice = ("give it a value in quotes, or drop it" if v is None
                              else "write it as one line of text" if isinstance(v, (list, dict, bytes, set))
                              else "quote it")
                    errors.append(f"metadata value {k} is {_kind(v)} ({_shown(v)}), not text: {SPEC} takes text "
                                  f"values; {advice}")
    for key, shape in (("license", "a license name or a bundled license file's name"),
                       ("allowed-tools", "one space-separated string, such as Bash(git:*) Read")):
        if key in fm and not isinstance(fm[key], str):
            errors.append(f"{key} is {_kind(fm[key])}, not text: {SPEC} takes {shape}")
    if "compatibility" in fm:
        comp = fm["compatibility"]
        if comp is None or (isinstance(comp, str) and not comp.strip()):
            errors.append(f"compatibility is empty: {SPEC} takes 1 to 500 characters; write the requirement, or drop "
                          "the key")
    return errors


def check(skill_dir, out=None):
    """Return (errors, warnings) for one skill folder; out, when package_dual.py passes its
    output folder, cuts a link out to the archives as the packager does."""
    # abspath, not resolve(): '.' and '..' become the folder's own name, and a
    # junction or symlink an agent reaches the skill through keeps its name.
    skill = Path(os.path.abspath(skill_dir))
    errors, warnings = [], []
    md = skill / "SKILL.md"
    if not md.is_file():
        return [f"{skill}: SKILL.md not found"], []

    tree = _tree(skill, out, errors)
    nested =[p for p in tree if p.name == "SKILL.md" and p != md and p.is_file()]
    if nested:
        errors.append("more than one SKILL.md (some hosts take exactly one on upload): "
                      + ", ".join(p.relative_to(skill).as_posix() for p in nested))

    text = _read_utf8(md, "SKILL.md", errors)
    if text is None:
        return errors, warnings
    if text.startswith(BOM):
        text = text[1:]
        warnings.append("SKILL.md starts with a UTF-8 byte-order mark (BOM); save it as plain UTF-8, "
                        "which every surface reads")
    try:
        fm, body = _parse_frontmatter(text)
    except ValueError as e:
        return errors + [str(e)], warnings

    # A key YAML types as something other than text (on:, yes:, 1:, ~:) is named with its type, never
    # joined into the list of text keys (a TypeError with PyYAML before 1.4's ninth review).
    extra = [k for k in fm if k not in ALLOWED_KEYS]
    for k in extra:
        if not isinstance(k, str):
            errors.append(f"a frontmatter key is read by YAML as {_kind(k)} ({_shown(k)}), not text; quote it, or drop it")
    names = sorted(k for k in extra if isinstance(k, str))
    if names:
        errors.append(f"frontmatter keys not allowed: {', '.join(names)}")

    name = "" if fm.get("name") is None else _shown(fm["name"]).strip()
    if isinstance(fm.get("name"), (list, dict)):  # named as what it is, never quoted as if it were the name
        errors.append(f"name is {_kind(fm['name'])} ({name}), not text: write the folder's kebab-case name")
    elif not name:
        errors.append("frontmatter has no name")
    else:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
            errors.append(f"name '{name}' must be kebab-case, at most 64 characters")
        if name != skill.name:
            errors.append(f"name '{name}' differs from its folder '{skill.name}'; agents load by name")

    desc = fm.get("description")
    if desc is not None and not isinstance(desc, str):
        advice = ("write it as one line of text, or a > block" if isinstance(desc, (list, dict))
                  else "a !! tag made it so; drop the tag" if isinstance(desc, (bytes, set))  # quoting keeps the tag
                  else "YAML reads it so unquoted; quote it")
        errors.append(f"description is {_kind(desc)} ({_shown(desc)}), not text: {advice}")
        desc = ""
    elif not desc or not desc.strip():
        errors.append("frontmatter has no description")
        desc = ""
    desc = desc.strip()
    if "<" in desc or ">" in desc:
        errors.append("description contains angle brackets (< or >), which some hosts reject on upload")
    if len(desc) > 1024:
        errors.append(f"description is {len(desc)} characters; the limit is 1024")
    if desc and not WHEN_CUE.search(desc):
        warnings.append("description says what the skill is but not when to use it; "
                        "the description is the only text a model sees when choosing a skill")
    comp = fm.get("compatibility")
    try:
        long_comp = bool(comp) and len(str(comp)) > 500
    except ValueError:  # a number past Python's 4,300-digit limit for printing: thousands of characters as written
        long_comp = True
    if long_comp:
        errors.append("compatibility is over 500 characters")
    errors += _spec_shapes(fm)

    body_lines = body.count("\n") + 1
    if body_lines > 500:
        errors.append(f"SKILL.md body is {body_lines} lines; keep it under 500 and move depth to references/")
    if re.search(r"^\s*TRIGGER\b", body, re.M):
        warnings.append("trigger phrases sit in the body; move them into the description, "
                        "which is what decides whether the skill loads")

    # Every file the package ships is read where it is text (a TEXT_SUFFIXES type, or no suffix and no NUL
    # byte): under references/, scripts/ and assets/ a file that is not UTF-8 is an error; at the root or
    # in any other folder (LICENSE, README.md) a warning, since the package ships it byte-for-byte. A
    # dotfile (.notes.md, a Mac's ._run.py) and junk never reach the archive, so they are not read.
    texts = {md: text}
    shipped = [p for p in tree if p.is_file() and p != md
               and not any(part.startswith(".") for part in p.relative_to(skill).parts)
               and p.name not in JUNK_FILES and p.suffix.lower() != ".pyc"
               and not set(p.relative_to(skill).parts[:-1]) & JUNK_DIRS]
    for p in shipped:
        rel = p.relative_to(skill)
        try:
            data = p.read_bytes()
        except OSError as e:  # held open with no share mode, or no permission: named once, here
            errors.append(_unreadable(rel.as_posix(), e))
            continue
        if _carries_payload(p, data):
            continue
        if not (p.suffix.lower() in TEXT_SUFFIXES or (not p.suffix and b"\0" not in data)):
            continue
        try:
            texts[p] = data.decode("utf-8")
        except UnicodeDecodeError as e:
            if rel.parts[0] in BUNDLE_DIRS:
                errors.append(f"{rel.as_posix()} is not UTF-8 ({e.reason} at byte {e.start}); save it as UTF-8")
            else:
                warnings.append(f"{rel.as_posix()} is not UTF-8 ({e.reason} at byte {e.start}); the package ships it "
                                f"byte-for-byte, but save it as UTF-8, which every surface reads")

    # A referenced name may hold a space (or its %20 form in a link): when the match does not exist but a
    # shipped file's name starts with it and the text goes on with that name, the longer name is meant.
    names = sorted((p.relative_to(skill).as_posix() for p in shipped), key=len, reverse=True)
    for src, t in texts.items():
        if src != md and _is_test_file(src.relative_to(skill)):
            continue
        seen = set()
        for m in REF_PATTERN.finditer(t):
            ref = m.group(1)
            if not (skill / ref).exists() and not (src.parent / ref).exists():
                ref = _longer_name(t, m.start(1), ref, names)
            if ref in seen:
                continue
            seen.add(ref)
            if any(part.startswith(".") and part not in (".", "..") for part in ref.split("/")):
                # present here, but the package leaves every dotfile out, so the installed skill lacks it
                errors.append(f"{src.relative_to(skill).as_posix()} references {ref}, which the package leaves "
                              f"out (a dotfile); rename it without the leading dot")
            elif not (skill / ref).exists() and not (src.parent / ref).exists():
                errors.append(f"{src.relative_to(skill).as_posix()} references {ref}, which does not exist")

    # Dotfiles (.keep, .gitignore) and junk never reach the archive, so they cannot be orphans in it;
    # junk is named once, below. A name mentioned only in its %20 form is still mentioned.
    bundled = [p for p in shipped if p.relative_to(skill).parts[0] in BUNDLE_DIRS]
    everything = "\n".join(texts.values())
    everything += "\n" + unquote(everything)
    for p in bundled:
        rel = p.relative_to(skill).as_posix()
        if rel not in everything and p.name not in everything:
            warnings.append(f"{rel} is not mentioned by SKILL.md or any other file (orphan)")
        if p.suffix.lower() == ".md" and p in texts and texts[p].count("\n") > 300:
            if "contents" not in texts[p][:1500].lower():
                warnings.append(f"{rel} is over 300 lines with no contents list")
    for p, source in texts.items():
        if p == md:
            continue
        rel = p.relative_to(skill).as_posix()
        suffix = p.suffix.lower()
        run = suffix in RUN_SUFFIXES or not p.suffix
        if source.startswith(BOM):
            # A BOM breaks a file where the first bytes carry meaning: a shell or the kernel does not
            # honor a #! line that does not open the file (and the packager stores it without the
            # executable bit); a shell reads a BOM at the start of a .sh as part of the first command;
            # JSON forbids a BOM (json.loads rejects it). A .md or .ps1 is not run by its first line,
            # so a #! there is only text. Elsewhere it is a warning, except in a .ps1: Windows
            # PowerShell reads a UTF-8 script by its BOM and ANSI without one.
            if run and source.startswith(BOM + "#!"):
                errors.append(f"{rel} has a UTF-8 byte-order mark (BOM) before its #! line, so a shell or the kernel "
                              f"does not honor it (Windows' py launcher aside) and it is not stored executable; save "
                              f"it as plain UTF-8")
            elif suffix in SHELL_SUFFIXES:
                errors.append(f"{rel} starts with a UTF-8 byte-order mark (BOM), which a shell reads as part of the "
                              f"first command (bash, dash and sh fail on it); save it as plain UTF-8")
            elif suffix == ".json":
                errors.append(f"{rel} starts with a UTF-8 byte-order mark (BOM), which JSON forbids and json.loads "
                              f"rejects; save it as plain UTF-8")
            elif suffix == ".py":  # Python skips a BOM when it runs the file
                warnings.append(f"{rel} starts with a UTF-8 byte-order mark (BOM); Python runs it, but save it "
                                f"as plain UTF-8")
            elif suffix != ".ps1":
                warnings.append(f"{rel} starts with a UTF-8 byte-order mark (BOM); save it as plain UTF-8, which "
                                f"every surface reads")
        if suffix == ".py":
            try:
                compile(source.lstrip(BOM), str(p), "exec")
            except (SyntaxError, ValueError) as e:  # a NUL byte is a ValueError on Python 3.10
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
