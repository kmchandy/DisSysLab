# API Key Setup

Every DisSysLab office that uses an AI analyst needs an Anthropic API
key. This guide walks you through getting one and putting it where
`dsl run` can find it.

Time required: about 3 minutes.

---

## 1. Get a key

Open [console.anthropic.com](https://console.anthropic.com/) and create
an API key. Paid accounts get higher rate limits; a free account works
for the gallery offices.

Your key starts with **`sk-ant-`** and is about 100 characters long.
**Copy the whole thing to your clipboard.** Anthropic only shows it
once — if you close the window you will need to generate a new one.

---

## 2. Put the key in a `.env` file

DisSysLab reads the key from a file named `.env` in your office folder.
The fastest way to create it — on macOS, with the key still on your
clipboard:

```bash
cd path/to/your/office
echo "ANTHROPIC_API_KEY=$(pbpaste)" > .env
```

That's it. The file now contains exactly one line that looks like:

```
ANTHROPIC_API_KEY=sk-ant-api03-...(about 100 chars)...
```

**On Linux** the equivalent is `xclip -o` or `xsel -b` instead of
`pbpaste`. **On Windows** (PowerShell):

```powershell
"ANTHROPIC_API_KEY=$(Get-Clipboard)" | Out-File -Encoding utf8 .env
```

### If you prefer a text editor

Open `.env` in **VS Code**, **nano**, or any other plain-text editor.
Paste your key on a single line after `ANTHROPIC_API_KEY=`. Save.

> **Do not use TextEdit on macOS.** TextEdit silently saves `.env` as
> Rich Text Format (RTF), which `dsl run` cannot read. If you've
> already used TextEdit, delete the file (`rm .env`) and recreate it
> with the `pbpaste` one-liner above, or with VS Code.

---

## 3. Verify it worked

Run `dsl doctor` from the same folder:

```bash
dsl doctor
```

You should see:

```
Local .env:
  [OK] .env format: ANTHROPIC_API_KEY present (prefix sk-ant-…, len 108)

Credentials:
  [OK] ANTHROPIC_API_KEY: set (prefix sk-ant-…, len 108)
```

If anything says **FAIL**, jump to the next section.

---

## Troubleshooting

`dsl doctor` prints a specific hint for each problem. The common ones:

### `saved as RTF (probably via TextEdit)`

TextEdit saved your file as rich text, not plain text. Fix:

```bash
rm .env
echo "ANTHROPIC_API_KEY=$(pbpaste)" > .env
```

Re-copy your key to the clipboard first if needed.

### `contains shell commands`

You pasted terminal history into `.env` instead of a single
`KEY=VALUE` line. Same fix:

```bash
rm .env
echo "ANTHROPIC_API_KEY=$(pbpaste)" > .env
```

### `no ANTHROPIC_API_KEY line found` or `ANTHROPIC_API_KEY is set to empty string`

The file exists but doesn't have your key in it. Open `.env` and add
a line:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### `value starts with '...', not 'sk-ant-'`

You probably copied only part of the key, or copied a placeholder.
Go back to [console.anthropic.com](https://console.anthropic.com/),
copy the full key (starts with `sk-ant-`), and redo step 2.

### `Error code: 401` when running an office

The key was found but Anthropic rejected it. Either the key is
revoked or you copied the wrong one. Generate a fresh key from
[console.anthropic.com](https://console.anthropic.com/) and redo
step 2.

### `dsl --version` shows the wrong version

Your shell is finding a different `dsl` binary than the one you just
installed. Check which one it's using:

```bash
which dsl
pip show dissyslab | grep -E '^(Version|Location)'
```

If the `which` path is not inside the `pip` install location, you
probably forgot to activate your virtual environment:

```bash
source /path/to/your/venv/bin/activate
dsl --version
```

---

## Where to put `.env` for multiple offices

Each office folder gets its own `.env`. `dsl run path/to/office/`
looks for `.env` inside **that folder**. If you share one key across
several offices, you can either:

- Copy `.env` into each office folder, or
- Export the key in your shell once, so every office picks it up:

  ```bash
  export ANTHROPIC_API_KEY=sk-ant-api03-...
  ```

  (Add that line to `~/.zshrc` or `~/.bashrc` to make it permanent.)

---

*Last reviewed for DisSysLab v1.1.3.*
