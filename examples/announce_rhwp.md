stumbled on this and thought it deserved more visibility — RHWP is a viewer/editor for HWP and HWPX, the Korean word-processor format from Hancom that ~50M people use daily but historically has had no real OSS reader (think "the Microsoft Word of Korea" with a strong proprietary lock-in).

built in pure Rust with a WASM compile target. same parser runs:

- in the browser (online demo: https://edwardkim.github.io/rhwp/)
- as VS Code / Chrome / Firefox / Safari / Edge extensions
- as npm packages (`@rhwp/editor` full UI, `@rhwp/core` API)
- as a native Rust crate (`cargo build`, Rust 1.75+)

HWP/HWPX is genuinely nasty to parse — proprietary binary container, encrypted streams, embedded compound documents — so the format reverse engineering is the bulk of the work. currently 1,100+ tests covering edge cases, v0.7.9 just shipped (Apr 30), and the maintainer is merging external contributor PRs.

the methodology side caught my eye too: the author keeps detailed AI-pair-programming notes in `mydocs/` (2,200+ files documenting design decisions, prompts, and how Claude Code was used as an implementation partner while the human kept architecture ownership). worth a read whether or not you care about HWP.

repo: https://github.com/edwardkim/rhwp (MIT)

not my project — just a fan sharing because rust+wasm for proprietary-format parsing feels like a niche that deserves more attention here.

*(disclosure: posted via my own reddit skill — https://github.com/cskwork/reddit-skill)*
