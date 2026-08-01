# Install reddit-poster

<details>
<summary><strong>Claude Code</strong></summary>

### Install

```bash
claude plugin marketplace add cskwork/reddit-poster
claude plugin install reddit-poster@reddit-poster
```

Type `/reddit-poster`.

### Verify

```bash
claude plugin list
```

### Update

```bash
claude plugin marketplace update reddit-poster
```

### Uninstall

```bash
claude plugin uninstall reddit-poster
claude plugin marketplace remove reddit-poster
```

</details>

<details>
<summary><strong>Codex</strong></summary>

### Install

```bash
codex plugin marketplace add cskwork/reddit-poster --ref main
codex plugin add reddit-poster@reddit-poster
```

Type `$reddit-poster`.

### Verify

```bash
codex plugin list
```

### Uninstall

```bash
codex plugin remove reddit-poster
codex plugin marketplace remove reddit-poster
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

### Install (extension, always-on)

```bash
gemini extensions install https://github.com/cskwork/reddit-poster
```

### Install (command, opt-in)

```bash
mkdir -p ~/.gemini/commands
curl -fsSL https://raw.githubusercontent.com/cskwork/reddit-poster/main/skills/reddit-poster/agents/gemini.toml \
  -o ~/.gemini/commands/reddit-poster.toml
```

Type `/reddit-poster` in a new session.

### Verify

```bash
gemini extensions list
```

### Uninstall

```bash
gemini extensions uninstall reddit-poster
```

</details>

<details>
<summary><strong>Cursor, OpenCode, Amp, and other agent-skills harnesses</strong></summary>

### Install

```bash
npx skills add cskwork/reddit-poster
npx skills add cskwork/reddit-poster -g
```

Type `/reddit-poster` in a new agent chat.

### Verify

```bash
npx skills list
```

### Update

```bash
npx skills update reddit-poster
```

### Uninstall

```bash
npx skills remove reddit-poster
```

</details>

<details>
<summary><strong>Antigravity (agy)</strong></summary>

### Install

```bash
agy plugin install https://github.com/cskwork/reddit-poster
```

### Verify

```bash
agy plugin list
```

### Uninstall

```bash
agy plugin uninstall reddit-poster
```

</details>
