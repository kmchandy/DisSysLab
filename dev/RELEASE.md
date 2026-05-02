# Releasing a new version of dissyslab

This document covers the full release loop end-to-end: what to do before
cutting a release, what `dev/release.sh` automates for you, and what to do
after PyPI accepts the upload. Read it once; after that the loop is muscle
memory.

`dev/release.sh` already automates the build/upload/push mechanics. The
parts it does **not** handle — the human-on-real-machine smoke test, the
clean-venv verification, and the environment hygiene that prevents stale
`dsl` binaries from shadowing PyPI installs — are documented here.

## One-time setup

Three things, run once, that retire whole categories of release-day pain.

### 1. Install `build` and `twine` system-wide via pipx

`dev/release.sh` calls `pyproject-build` and `twine`, expecting both on PATH.
The cleanest way is pipx (each tool gets its own isolated venv but the
binaries land in `~/.local/bin`, which pipx puts on your PATH).

```bash
brew install pipx && pipx ensurepath
pipx install build
pipx install twine
```

Verify:

```bash
which pyproject-build              # ~/.local/bin/pyproject-build
which twine                        # ~/.local/bin/twine
```

This means the build/upload step works from any shell, with or without a
venv active. You will never again hit `ModuleNotFoundError: No module
named 'build'` mid-release.

### 2. Kill the stale `dsl` lurking in framework Python

If you have ever `pip install dissyslab`'d into the framework Python
(`/Library/Frameworks/Python.framework/Versions/3.12/`), the resulting
`dsl` binary will shadow venv-scoped `dsl` binaries for the rest of time
unless removed. Symptom: `dsl --version` reports an ancient number even
inside a fresh venv.

```bash
/Library/Frameworks/Python.framework/Versions/3.12/python3 -m pip uninstall -y dissyslab
which -a dsl                       # should now show no framework path
```

### 3. Build a dedicated dev venv with dissyslab installed editable

This is where you do day-to-day work and Step 0's smoke test. It is
distinct from any throwaway "verify" venv you create per release.

```bash
python3 -m venv ~/.venvs/dsl-dev
~/.venvs/dsl-dev/bin/pip install --upgrade pip
~/.venvs/dsl-dev/bin/pip install -e ~/Documents/DisSysLab
```

After this, `source ~/.venvs/dsl-dev/bin/activate` puts you in an
environment where `dsl` reflects your working tree.

## Release checklist

Replace `X.Y.Z` with the new version (e.g. `1.2.13`).

### Step 0 — Smoke-test the change on your real machine

Sandbox tests are necessary but not sufficient. The bar is "the human ran
the new feature on this Mac and saw it work". Skipping this is how
v1.2.11 shipped a Ctrl-C summary that didn't actually fire.

```bash
cd ~/Documents/DisSysLab
source ~/.venvs/dsl-dev/bin/activate
which dsl                          # must point inside ~/.venvs/dsl-dev/bin
dsl --version                      # the version currently in pyproject.toml

# Exercise whatever you just changed. For a CLI feature, that means
# running it. Examples:
cd /tmp && rm -rf rel_smoke && dsl new rel_smoke
# Type a description at the > prompt; verify files land and `dsl run .` works
dsl edit rel_smoke                 # round-trip

deactivate
```

If anything misbehaves, fix it now. Do not proceed.

### Step 1 — Bump version

Edit two files. Both must change to the same number; nothing else should
change.

```bash
cd ~/Documents/DisSysLab
grep -n 'version' pyproject.toml dissyslab/__init__.py
```

Edit:

- `pyproject.toml` — change `version = "X.Y.Z-1"` to `version = "X.Y.Z"`
- `dissyslab/__init__.py` — change `__version__ = "X.Y.Z-1"` to `__version__ = "X.Y.Z"`

Verify nothing else moved:

```bash
git diff pyproject.toml dissyslab/__init__.py
```

### Step 2 — Commit the version bump on its own

```bash
git add pyproject.toml dissyslab/__init__.py
git commit -m "Bump version to X.Y.Z"
git log -1 --stat                  # confirm only those two files
```

A standalone bump commit makes a revert trivial if PyPI rejects the
upload and you want to back out cleanly.

### Step 3 — Confirm tooling is in place

```bash
which pyproject-build twine        # both must resolve (see one-time setup)
git status --short                 # must be empty (release.sh refuses otherwise)
git rev-parse --abbrev-ref HEAD    # must be "main" (release.sh refuses otherwise)
```

### Step 4 — Run release.sh

This handles the mechanical part: clean previous artifacts, build wheel
+ sdist, verify the artifacts have the expected version in their
filenames, twine upload, and push commits to origin/main.

```bash
./dev/release.sh
```

It will print the version it parsed from your files and ask you to
confirm. Type `y` if it matches what you intended; anything else aborts.
On success it prints "released dissyslab X.Y.Z" and a verify command.

When prompted by twine, paste your PyPI API token (starts with `pypi-`).

**If twine fails with `400 File already exists` or `403 Forbidden` on a
retry**, do NOT keep retrying. Open the project page in a browser:

```bash
open https://pypi.org/project/dissyslab/X.Y.Z/
```

If both `dissyslab-X.Y.Z-py3-none-any.whl` and `dissyslab-X.Y.Z.tar.gz`
appear there, the upload succeeded — twine's error stream was
misleading. Skip to Step 5. If only one appears, upload only the missing
file:

```bash
twine upload dist/dissyslab-X.Y.Z.tar.gz           # if only the wheel landed
# or
twine upload dist/dissyslab-X.Y.Z-py3-none-any.whl # if only the sdist landed
```

If neither appeared, re-run `./dev/release.sh` (the script is idempotent
for the build step).

### Step 5 — Tag the commit and push the tag

`release.sh` does not tag — do it manually after PyPI is happy. That way
a failed upload does not leave you with an orphan tag to clean up.

```bash
git tag vX.Y.Z
git push --tags
```

### Step 6 — Verify from PyPI in a fresh throwaway venv

This proves that what landed on PyPI is what users will actually
install.

```bash
deactivate                         # if any venv is active
cd /tmp
python3 -m venv verify-X-Y-Z
source verify-X-Y-Z/bin/activate
pip install --upgrade pip
pip install dissyslab==X.Y.Z

rehash                             # clear zsh's command hash (see Step 7)
which dsl                          # must point inside /tmp/verify-X-Y-Z/bin
dsl --version                      # must print X.Y.Z
dsl --help | head -25              # spot-check that new commands appear

deactivate
rm -rf /tmp/verify-X-Y-Z           # toss the verification venv
```

If Step 6 succeeds, the release is shipped.

### Step 7 — If `dsl --version` shows an old number in Step 6

Three diagnostics, in order:

```bash
which dsl
which -a dsl
echo $PATH | tr ':' '\n' | head -10
```

**If `which dsl` and `which -a dsl` disagree** (the singular shows a
stale path; the all-versions shows the venv first), it is zsh's command
hash:

```bash
rehash
which dsl                          # should now show the venv path
dsl --version
```

**If `which -a dsl` shows the venv path NOT first**, your PATH has a
stale `dsl` ahead of the venv. Confirm the venv install is healthy by
calling its binary directly:

```bash
/tmp/verify-X-Y-Z/bin/dsl --version
```

If that prints the right version, the release itself is fine and you
have a separate PATH cleanup to do — usually the framework-Python
uninstall in the one-time-setup section above.

**If `pip show dissyslab` reports the wrong version inside the venv**,
the install itself is broken — re-run:

```bash
pip install --force-reinstall dissyslab==X.Y.Z
```

## Why this layout

Two independent verifications between steps 0 and 6 cover every failure
mode actually hit on the last several releases:

- **Step 0 (smoke test in dev venv)** catches "the code does not do what
  I think it does on this machine".
- **Step 6 (clean install from PyPI)** catches "PyPI is serving the
  wrong artifact" and "the package is not installable as published".

PyPI's misleading 400/403 errors and the framework-Python `dsl` ghost
are not failure modes you can prevent — they are environmental hazards.
The doc names them so they stop being surprises.
