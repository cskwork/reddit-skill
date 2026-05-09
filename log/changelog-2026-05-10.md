# 2026-05-10 변경 결정 로그

## 배경 — 왜 이 변경이 필요했나

세션에서 사용자가 `/reddit-poster`로 Reddit 게시를 요청했을 때, MCP 도구(`mcp__reddit__*`)가 deferred tools 목록에 로드되지 않은 상태였다. 이유를 추적해보니:

- `~/.claude.json`의 `mcpServers.reddit`은 `C:/Users/a` 스코프(home dir)에 등록됨
- 하지만 working directory(`D:/Git/symphony-multi-agent`)의 프로젝트 항목은 `mcpServers: {}`로 비어 있어 user-scope 상속이 자동 적용되지 않음
- 결과적으로 MCP 경로는 매번 working dir에 따라 들쭉날쭉하게 동작 → 사용자 경험상 "왜 안 떠?" 마찰

CLI는 같은 패키지지만 transport가 transparent하므로 working dir 무관하게 항상 동작. 사용자도 "결국 CLI로 돌아가는데 왜 MCP가 1급이지?"라고 의문 제기.

## 결정

CLI를 1급(primary), MCP는 옵션(optional)으로 재포지셔닝. **단, MCP 코드는 제거하지 않는다.**

## 왜 옵션 C(MCP 완전 제거)가 아니라 옵션 B인가

옵션 C(MCP 제거)를 거부한 이유:

1. **리포 이름 자체가 `reddit-mcp`** — MCP를 빼면 rebrand가 강제되고, 기존 GitHub stars/issues 컨텍스트와 외부 링크가 깨진다.
2. **breaking change** — 외부 사용자 중 MCP 경로로 연동한 사람들이 모두 깨진다. CLI 경로가 그들에게 더 좋다는 가정은 우리가 강요할 게 아님.
3. **한계 비용은 `server.py` 80줄 정도** — 유지비가 작아서 미리 자르는 게 이득이 아님.
4. **MCP 자체는 잘못 없다** — 마찰은 MCP가 아니라 Claude Code의 working-dir-별 MCP 로딩 정책에서 옴. 그건 MCP 패키지가 풀 문제가 아니다.

옵션 A(`.env`만 추가, 문서 변경 없음)를 거부한 이유:

1. 사용자의 핵심 마찰을 해결 못 함 — README가 여전히 MCP 우선이면 새 사용자도 같은 경로로 빠진다.
2. README headline은 그대로 "Reddit MCP server with proper post-flair support" — 진실(CLI도 동등하게 강력)을 가린다.

## 변경 사항

### 1. `src/reddit_mcp/auth.py` — `.env` 로딩 추가

자격증명 해석 순서:

```
env vars  →  .env (cwd부터 위로 5단계 walk-up)  →  ~/.claude.json fallback
```

- `_find_dotenv()` — cwd부터 부모 디렉터리로 올라가며 `.env` 탐색. 5단계 또는 filesystem root에서 중단.
- `_parse_dotenv()` — stdlib만 사용한 미니 파서. comments(`#`), 빈 줄, `KEY=value`, quoted values, `export` 접두사 처리.
- `_from_dotenv()` — 4개 키 모두 있을 때만 `Creds` 반환.

**왜 stdlib parser인가:** `python-dotenv` 의존성을 추가하지 않기 위해서. 4개 키만 읽으면 되는 단순 케이스라 외부 의존성 정당화 안 됨. parser 본체 ~15줄.

**왜 walk-up인가:** 사용자가 repo 루트에 `.env` 두고 하위 디렉터리에서 `uv run reddit-post` 실행하는 경우를 지원. git, npm 등 표준 도구의 동작과 일치.

**왜 env vars가 여전히 1순위인가:** 12-factor 원칙. CI 환경, Docker, ephemeral 셸에서 env가 명시적으로 주입되면 그게 진실의 원천. `.env`는 "로컬 개발 편의 파일"이지 인증 우선순위의 최상위가 아니다.

### 2. `.env.example` 추가

리포 루트에 placeholder 파일 추가. 사용자가 `cp .env.example .env` 한 줄로 셋업 시작 가능. `.env`는 이미 `.gitignore`에 있음(line 9).

### 3. `README.md` 재구성

순서 변경:

```
Before:                          After:
1. Install                       1. Install
2. Credentials                   2. Credentials (.env primary)
3. Use as a CLI                  3. CLI (full features)
4. Use as MCP server             4. Optional: use as MCP server
5. Skill                         5. Skill
6. Why this exists               6. Why this exists
```

Headline 수정: "Reddit MCP server with proper post-flair support" → "A Reddit CLI for posting with proper flair handling, with an optional MCP server on the side."

`.claude.json` fallback은 "backward compatibility" 섹션으로 강등. 새 사용자에게는 `.env`만 안내.

### 4. `pyproject.toml` description 동기화

```
Before: "Reddit MCP server with proper post flair support, plus a standalone PRAW poster script."
After:  "Reddit CLI for posting with proper flair support (plus an optional MCP server). Built on PRAW."
```

PyPI 메타데이터 일관성. CLI가 1급임을 패키지 레벨에서도 표명.

### 5. `skills/reddit-poster/SKILL.md` intro 수정

기존: "Available as a CLI (`reddit-post`) or as MCP tools..."
변경: "Drives the **`reddit-post` CLI** (primary path — works in any session regardless of MCP loading state). The same package also exposes MCP tools..."

이미 모든 예시가 `uv run reddit-post`였지만, 인트로에서 명시적으로 "CLI primary"를 못박음. 또한 `.env` 우선 자격증명 체인 명시.

## 검증

- `uv run reddit-post flairs AI_Agents` 실행 → `.claude.json` fallback 경로로 정상 인증 (backward compat 확인)
- `_parse_dotenv()` 단위 테스트 → comments / quoted values / export 접두사 모두 통과
- `_find_dotenv()` + `_from_dotenv()` 임시 디렉터리 테스트 → `.env` 발견 + 파싱 + Creds 반환 모두 정상
- Windows tempfile 정리 시 `PermissionError`는 cwd가 임시 디렉터리에 잠겨서 발생한 cosmetic — 코드 버그 아님

## 의도적으로 하지 않은 것

1. **`.env`에 `python-dotenv` 채택** — 의존성 추가 가치 없음. 4개 키 stdlib 파서로 충분.
2. **MCP 코드 제거** — 위 옵션 C 거부 사유.
3. **리포 rename** — `reddit-mcp` 그대로 유지. MCP가 여전히 살아있고, 이름의 historical 의미를 깨면 외부 링크/디스커버리가 손상됨.
4. **`scripts/post.py` 정리** — 별도 standalone 스크립트로 보이는데 이번 작업 범위 아님. 추후 별건으로.
5. **CHANGELOG.md 같은 user-facing changelog** — 리포에 그런 파일이 없고, 이번 변경은 internal restructure이지 새 feature가 아니라서 user-facing 알림은 README 헤더 한 줄로 충분.

## 후속 권장

- 다음 push 전 `git status`로 `.env` 누출 없는지 한 번 더 확인 (이번 세션엔 만들지 않았지만 사용자가 추가하면 자동 ignore 되어야 함)
- skill을 사용자 글로벌(`~/.claude/skills/reddit-poster/SKILL.md`)에 이미 깔아두었다면 이번 SKILL.md 변경은 수동으로 동기화 필요
- 이번 세션에서 진행 중이던 Reddit 게시 플로우(symphony-multi-agent 홍보, draft 작성 완료, dry-run 직전)는 보류 상태. 사용자가 재개 지시하면 계속.
