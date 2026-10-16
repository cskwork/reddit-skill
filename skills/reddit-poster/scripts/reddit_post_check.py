#!/usr/bin/env python3
"""Reddit post linter — catches the syntax mistakes that silently break a post.

Usage:
    reddit_post_check.py <package-dir> [<package-dir> ...]
    reddit_post_check.py title.txt body.md post.md
    reddit_post_check.py --selftest

A package dir holds title.txt, body.md and (recommended) post.md with a `**Flair:**` line.
Exit 0 = PASS, 1 = errors found, 2 = usage/IO problem. Stdlib only.

Skips prose checks inside fenced and 4-space-indented code blocks, because Markdown there
is literal — flagging it would be a false positive.
"""
from __future__ import annotations
import os
import re
import sys

TITLE_MAX = 300
BODY_MAX = 40000
COMPOSER_MAX = 10000
# Word markers must be uppercase: case-insensitive matching fired on ordinary prose
# ("manage my todo list") and that is a *blocking* error. Brace/bracket markers stay
# as they are, since those never occur naturally.
PLACEHOLDER = re.compile(r"\{\{|<[Ii]nsert[^>]*>|\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b")
HTML_TAG = re.compile(r"</?(?:div|span|br|b|i|u|p|table|tr|td|th|a|h[1-6]|img|font|center)\b[^>]*>", re.I)
AUTOLINK = re.compile(r"<https?://[^>\s]+>|<mailto:[^>\s]+>")


def mask_code(text: str) -> str:
    """Blank out code regions so prose checks don't fire on literal Markdown."""
    out, fence = [], None
    for line in text.split("\n"):
        if fence:
            if line.strip().startswith(fence):
                fence = None
            out.append("")
            continue
        m = re.match(r"\s*(`{3,}|~{3,})", line)
        if m:
            fence = m.group(1)
            out.append("")
            continue
        if line.startswith("    ") or line.startswith("\t"):
            out.append("")
            continue
        out.append(line)
    # Inline code is literal too, and it was leaking into every prose check: a pipe in
    # `delete|wal` read as a table row, an asterisk in `*x*` read as emphasis. Masked with
    # 'x' rather than spaces so a line *ending* in inline code is not then mistaken for a
    # single-trailing-space hard break.
    return re.sub(r"`[^`\n]*`", lambda mm: "x" * len(mm.group(0)), "\n".join(out))


def check_title(title: str) -> list[tuple[str, str]]:
    f = []
    t = title.strip("\n")
    if not t.strip():
        return [("error", "title is empty")]
    if len(t) > TITLE_MAX:
        f.append(("error", f"title is {len(t)} chars (limit {TITLE_MAX})"))
    if "\n" in t:
        f.append(("error", "title spans multiple lines — Reddit titles are one line"))
    for pat, what in ((r"\*\*|__", "bold"), (r"\]\(", "link"), (r"^#", "heading"),
                      (r"~~", "strikethrough"), (r"`", "code")):
        if re.search(pat, t, re.M):
            f.append(("error", f"title contains Markdown ({what}) — titles do not render Markdown"))
    # em/en dash, curly quotes, ellipsis, nbsp are ordinary typography, not emoji
    odd = re.sub("[\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u00a0]", "", t)
    if re.search(r"[^\x00-\x7f]", odd):
        f.append(("warn", "title has non-ASCII characters (emoji/accents) — many subs strip or ban these"))
    if t.isupper() and len(t) > 12:
        f.append(("warn", "title is ALL CAPS"))
    if re.search(r"\b(NSFW|spoilers?)\b", t, re.I):
        f.append(("warn", "title auto-tags the post NSFW/Spoiler on Reddit — intended?"))
    if PLACEHOLDER.search(t):
        f.append(("error", "title contains placeholder text"))
    return f


def has_nested_emphasis(text: str) -> bool:
    """True only for real nesting (_a __b__ c_) — which old Reddit fails to render.

    A naive regex cannot tell nesting from two sibling spans, so it flags
    '**a** and **b**' and '*i* and **b**' as nested (false positives that block
    PASS). Collapse each *balanced* bold run to a sentinel first; only genuine
    nesting then leaves a single-marker span straddling that sentinel.
    """
    sent = "\x00"
    for m in ("*", "_"):
        e = re.escape(m)
        bold = re.compile(rf"(?<!{e}){e}{e}(?!{e})[^{e}\n]+(?<!{e}){e}{e}(?!{e})")
        span = re.compile(rf"(?<!{e}){e}(?![{e}\s])[^{e}\n]*{sent}[^{e}\n]*{e}(?![{e}])")
        if span.search(bold.sub(sent, text)):
            return True
    return False


def check_body(body: str) -> list[tuple[str, str]]:
    f = []
    if len(body) > BODY_MAX:
        f.append(("error", f"body is {len(body)} chars (limit {BODY_MAX})"))
    elif len(body) > COMPOSER_MAX:
        f.append(("warn", f"body is {len(body)} chars: over the {COMPOSER_MAX}-char rich-text "
                          "composer cap. Paste with the Markdown editor (limit 40000) or trim."))
    if PLACEHOLDER.search(body):
        f.append(("error", f"placeholder text left in body: {PLACEHOLDER.search(body).group(0)!r}"))
    for m in HTML_TAG.finditer(body):
        if not AUTOLINK.fullmatch(m.group(0)):
            f.append(("error", f"raw HTML tag {m.group(0)!r} renders as literal text — use entities"))
    prose = mask_code(body)
    lines = prose.split("\n")
    if re.search(r"\`\`\`", body):
        f.append(("warn", "fenced code block: invisible on old.reddit.com — 4-space indent for both"))
    if has_nested_emphasis(prose):
        f.append(("error", "nested emphasis does not render on old Reddit"))
    if re.search(r"\^\(", prose) and re.search(r"\]\(", prose):
        f.append(("warn", "parenthesised superscript combined with a link misparses on old Reddit"))
    if body.count(">!") != body.count("!<"):
        f.append(("error", "unbalanced spoiler markers >! … !<"))
    if re.search(r":[a-z][a-z0-9_+-]{1,30}:", prose):
        f.append(("warn", "emoji shortcode (:name:) is literal text in the Markdown editor"))
    table_like = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
    for i, ln in enumerate(lines):
        prev = lines[i - 1] if i else ""
        s = ln.strip()
        if table_like.match(ln) and "|" not in (lines[i - 1] if i else ""):
            f.append(("error", f"table marker row on line {i+1} has no header row above it"))
        # A list directly under a heading cannot merge into a paragraph — the heading
        # closes the block. Measured: 50 of 51 hits on real posts were exactly that.
        prev_is_heading = bool(re.match(r"^\s*#{1,6}\s", prev))
        if (re.match(r"^\s*(?:[-*+]|\d+[.)])\s", ln) and prev.strip() and not prev_is_heading
                and not re.match(r"^\s*(?:[-*+]|\d+[.)])\s", prev)
                and not prev.rstrip().endswith("  ")):
            f.append(("warn", f"list starts on line {i+1} with no blank line above — Reddit may merge it into the paragraph"))
        if ln.lstrip().startswith("#") and not re.match(r"^#{1,6}\s+\S", ln):
            f.append(("error", f"heading on line {i+1} needs a space and text after the #"))
        if re.match(r"^#\s", ln) and not re.match(r"^#\s*$", ln):
            f.append(("warn", f"level-1 heading on line {i+1} — ## reads better in a post"))
        if ln.rstrip("\n").endswith(" ") and not ln.endswith("  ") and ln.strip():
            f.append(("warn", f"line {i+1} ends with a single space — a hard break needs two"))
    if re.search(r"\n\n\n\n", body):
        f.append(("warn", "three+ consecutive blank lines: extra blank lines add no space on Reddit (use &nbsp;)"))
    pipe_rows = [ln for ln in prose.split("\n") if re.match(r"^\s*\|.*\|", ln)]
    has_marker_row = re.search(r"^\s*\|[\s:|-]*-{2,}[\s:|-]*\|", prose, re.M)
    if pipe_rows and not has_marker_row:
        f.append(("error", "table row without a marker row — tables need the |---| separator row"))
    return f


def check_post_md(text: str) -> list[tuple[str, str]]:
    f = []
    m = re.search(r"^\s*[-*]?\s*\*{0,2}Flair\*{0,2}:\s*(.+)$", text, re.M | re.I)
    if not m:
        f.append(("error", "post.md has no `**Flair:** …` line — flair is a UI field and must be recorded"))
    elif re.search(r"\b(none|n/?a|tbd|todo|\?)\b", m.group(1), re.I):
        f.append(("error", f"flair not resolved: {m.group(1).strip()!r}"))
    if not re.search(r"r/[A-Za-z0-9_]{2,}", text):
        f.append(("warn", "post.md does not name the target subreddit"))
    if "Markdown editor" not in text:
        f.append(("warn", "post.md does not remind to switch the composer to the Markdown editor"))
    return f


def check_paths(paths: list[str]) -> list[tuple[str, str, str]]:
    files = {}
    for p in paths:
        if os.path.isdir(p):
            for name in ("title.txt", "body.md", "post.md"):
                fp = os.path.join(p, name)
                if os.path.exists(fp):
                    files[fp] = open(fp, encoding="utf-8").read()
            if "body.md" not in " ".join(files):
                return [("error", p, "package dir has no body.md")]
        else:
            files[p] = open(p, encoding="utf-8").read()
    out = []
    for fp, text in files.items():
        base = os.path.basename(fp)
        if base == "title.txt":
            found = check_title(text)
        elif base == "body.md":
            found = check_body(text)
        elif base == "post.md":
            found = check_post_md(text)
        else:
            continue
        out += [(lvl, fp, msg) for lvl, msg in found]
    if not files:
        out.append(("error", ",".join(paths), "nothing to check (no title.txt/body.md/post.md)"))
    return out


def selftest() -> int:
    bad_title = "**My Cool Thing** [link](https://x.com) " + "x" * 300
    assert any(l == "error" for l, _ in check_title(bad_title)), "over-long/Markdown title not caught"
    assert any("Markdown" in m for l, m in check_title(bad_title) if l == "error")
    assert check_title("A perfect plain title") == []
    bad_body = (
        "Intro paragraph with a single trailing space \n"
        "- merged list item\n"
        "#no space heading\n"
        "| a | b |\n| 1 | 2 |\n"
        "spoil >!unclosed\n"
        "<div>raw html</div>\n"
        "TODO: fill this in\n"
    )
    codes = {m for _, m in check_body(bad_body)}
    for expect in ("single space", "blank line above", "after the #", "marker row",
                   "unbalanced spoiler", "raw HTML", "placeholder"):
        assert any(expect in c for c in codes), f"missed: {expect} -> {codes}"
    good_body = ("**TL;DR** it works.\n\n## Section\n\n### Deeper\n\n- one\n- two\n\n"
                 "| a | b |\n|---|---|\n| 1 | 2 |\n\n    indented code = literal *stars*\n")
    assert check_body(good_body) == [], check_body(good_body)
    # Real posts that Reddit accepted fine must not be flagged. Each line here is a
    # false positive found by running the linter over 21 live r/hermesagent posts.
    accepted = ("I use it to manage my todo list and calendar.\n\n"
                "    a | b\n    c | d\n\n" + "word " * 200)
    seen = [m for _, m in check_body(accepted)]
    assert not any("placeholder" in m for m in seen), seen
    assert not any("marker row" in m for m in seen), seen
    assert not any("TL;DR" in m for m in seen), seen
    assert not any("blank line above" in m for m in check_body("## Section\n- one\n- two\n")), \
        "list under a heading was flagged"
    # ...while the genuine versions of those problems still fire.
    assert any("placeholder" in m for _, m in check_body("TODO: finish\n")), "lost placeholder detection"
    assert any("marker row" in m for _, m in check_body("| a | b |\n| 1 | 2 |\n")), "lost broken-table detection"
    inline = "- **`hermes pm`** manages it: `hermes sessions set-journal-mode delete|wal`, plus `a|b`.\n"
    assert not any("marker row" in m for _, m in check_body(inline)), "pipe inside inline code flagged as a table"
    assert not any("emphasis" in m for _, m in check_body("a `*not italic*` and `**not bold**` here\n")), "inline emphasis flagged"
    for nested in ("_this is __really__ important_", "*this is **really** important*"):
        assert has_nested_emphasis(nested), f"missed real nesting: {nested}"
    for sibling in ("**a** and **b**", "*italic* and **bold**", "__bold__ and __more__",
                    "**a** *b* **c**", "*one* two **three**"):
        assert not has_nested_emphasis(sibling), f"false positive on siblings: {sibling}"
    sibs = "**a** and **b**\n\n*italic* and **bold**\n"
    assert not any("nested emphasis" in m for _, m in check_body(sibs)), check_body(sibs)
    assert check_post_md("# Post\n\n- **Subreddit:** r/selfhosted\n- **Flair:** Guide\n- Paste with the composer in Markdown editor mode\n") == []
    assert any("flair" in m.lower() for _, m in check_post_md("- Subreddit: r/x\n"))
    print("selftest OK")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    if argv[0] == "--selftest":
        return selftest()
    try:
        findings = check_paths(argv)
    except OSError as exc:
        print(f"[error] {exc}")
        return 2
    errors = [x for x in findings if x[0] == "error"]
    warns = [x for x in findings if x[0] == "warn"]
    for lvl, where, msg in findings:
        print(f"[{lvl}] {os.path.basename(where)}: {msg}")
    status = "FAIL" if errors else "PASS"
    print(f"\n{status}: {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
