# Reddit Markdown — verified reference

Source of truth: Reddit Help, *Formatting Guide* (`support.reddithelp.com/hc/en-us/articles/360043033952`),
retrieved article body via `support.reddithelp.com/api/v2/help_center/en-us/articles/360043033952.json`
(the public page is Cloudflare-gated and truncates; the Zendesk API returns the full HTML body).
"new" = reddit.com, "old" = old.reddit.com. When a rule says old doesn't support it, that syntax
silently degrades — it does not error.

## Contents

- [Text](#text)
- [Paragraphs and line breaks](#paragraphs-and-line-breaks)
- [Headings](#headings)
- [Lists](#lists)
- [Blockquotes](#blockquotes)
- [Tables](#tables)
- [Code](#code)
- [Links](#links)
- [Thematic breaks](#thematic-breaks)
- [Emojis](#emojis)
- [Escaping and HTML entities](#escaping-and-html-entities)
- [Write-for-both-parsers checklist](#write-for-both-parsers-checklist)

## Text

| Written | Renders |
|---|---|
| `*italic*` or `_italic_` | italic |
| `**bold**` or `__bold__` | bold |
| `***bold-italic***` or `___bi___` | bold-italic |
| `~~strikethrough~~` | strikethrough |
| `>!spoiler!<` | hidden spoiler |
| `^superscript` or `^(superscript)` | superscript |
| `` `code` `` | inline code |

- Emphasis can cover part of a word, but only with asterisks: `vul*pu*ta**te**` works,
  `vul_pu_ta__te__` does not.
- `>!…!<` leaks the markers into visible text if the closing `!<` is missing — always balance.
- Superscript: `^word` superscripts one word; `^(many words)` needs the parens; superscripting
  each word individually (`^a ^b`) is the old-Reddit-safe form. Space the words with a
  non-breaking space (`&nbsp;` / `&#x2005;`) to keep the spacing even.
- Superscript containing a link: superscript the **link text** itself,
  `[^be ^reddited](https://example.com)`, and avoid parenthesised `^(…)`. Towers (multiple
  superscript levels) do not work on new Reddit.
- No nested emphasis: `_this is __really__ important_` fails on old Reddit.

## Paragraphs and line breaks

- Paragraphs are separated by a **blank line**. Extra blank lines do **not** add vertical space.
- A single newline is treated as a space — adjacent lines join into one paragraph.
- Hard line break: **two trailing spaces** at the end of the line (works everywhere) or a
  trailing backslash (`\`, new Reddit only).
- Forced blank space: a line containing only `&nbsp;` (`&#x2003;` for an em-space).
- A line starting with `-` mid-paragraph becomes a list; escape it (`\-`).

## Headings

```
# H1        ## H2       ### H3
#### H4     ##### H5    ###### H6   (H6 renders italic on new Reddit)
```

- Requires a space after the hashes. `#foo` is not a heading.
- Setext form also works for the first two levels: underline with `===` (H1) or `---` (H2).
- Use `##`/`###` in a post; `#` is visually shouty and some subs' CSS resizes it.

## Lists

- Unordered: `- ` or `* ` — identical behaviour.
- Ordered: must start at `1.`; `1)` also works on new Reddit but not old.
- Sublists: indent **2 spaces** under an unordered parent, **3 spaces** under an ordered parent.
- Blank lines between items are optional; spacing changes nothing at render time.
- A list immediately after a paragraph with no blank line gets absorbed into that paragraph.
- List items can contain their own paragraphs, blockquotes and code.

## Blockquotes

- Start the line with `>`. For multi-line quotes, prefix **every** line with `>`.
- Nest with `> >`.
- `>` + a blank `>` line separates quoted paragraphs; lists, headings and tables all work
  inside a quote as long as every line carries the `>`.

## Tables

```
| Ticker | Investment | Profit |
|--------|-----------:|:------:|
| BTC    | $100       | $-50   |
```

- Row 2 is the marker row; the header row is auto-bold. The row of dashes is required.
- `:---` left, `---:` right, `:--:` centre, `---` left by default.
- One colon and one dash is enough — columns need not align in the source.
- Keep the leading and trailing `|`. Without them the parser misreads rows (leading/trailing
  pipes are the documented fix for both parsers' quirks).
- Cells cannot contain newlines. Pipes inside a cell must be escaped or avoided.

## Code

- Inline: `` `code` ``. To include a backtick, wrap in more backticks (`` ``a ` b`` ``), or
  pad with spaces.
- Block, portable: indent every line by **4 spaces** — this is the only form old Reddit renders.
- Block, new-Reddit only: ``` or `~~~` fences, open and close matching in char and count.
- Nested fences need different delimiters or a longer outer fence (`~~~~` outside, ``` inside).
- Nothing inside a code region is parsed as Markdown — that's the point, and the reason to use
  it for stack traces, config and command output.
- No syntax highlighting on Reddit — a bare fence is fine.

## Links

| Written | Result |
|---|---|
| `[text](https://url)` | hyperlinked text |
| `[text](https://url "title")` | hover title (quotes — old Reddit rejects parens here) |
| `<https://url>` | force-autolink (use when a raw URL mis-parses) |
| `https://url` | autolink, no brackets needed |
| `r/subreddit`, `/r/subreddit`, `u/user` | auto userlink/sublink |
| `[text][1]` + `[1]: https://url` | reference link, definition outside the paragraph |

- **No space** between `]` and `(` — `[a] (url)` breaks on reddit.com.
- The scheme is required: `[a](www.reddit.com)` does not link; write `https://`.
- URLs with spaces must be `%20`-encoded; `<…>` helps when a raw URL parses oddly at its end.

## Thematic breaks

- `---`, `***`, or `___` on their own line, 3+ characters, with blank lines around it.
  Careful: `---` directly under text makes an H2 instead (setext heading).

## Emojis

- Custom community emojis are referenced as `:name:` **only** where the community has that
  emoji defined — otherwise the text shows literally.
- The `:smile` shortcode picker exists in the **rich text editor** on desktop only. In the
  Markdown editor, `:smile` is plain text — paste the actual emoji character or leave it out.

## Escaping and HTML entities

- `\` before a character stops the parser treating it as Markdown: `\-`, `\*`, `\#`, `\[`.
- HTML entities work and are the only way to force certain characters/spacing:
  `&nbsp;` (non-breaking space), `&mdash;` (em dash), `&#x2003;` (em space),
  `&#x200b;` (zero-width), `&#x2005;` (four-per-em space, for superscript spacing).
- Raw HTML **tags** are not supported: `<div>`, `<br>`, `<b>` render as literal text. Don't
  hand-write HTML; only entities.

## Write-for-both-parsers checklist

Reddit is read on new reddit, old reddit, and a dozen third-party clients. For a post that must
look right everywhere:

- [ ] Two trailing spaces for hard breaks, never `\` alone.
- [ ] 4-space indented code blocks, not ``` fences.
- [ ] Quotes for link titles, `1.` not `1)`, leading/trailing pipes on tables.
- [ ] No nested emphasis, no superscript towers, no `^(…)` wrapping links.
- [ ] Blank line before and after every list, table, heading and quote.
- [ ] No raw HTML tags.
