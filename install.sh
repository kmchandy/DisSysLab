#!/usr/bin/env bash
#
# DisSysLab one-line installer for Pat.
#
# Usage:
#     curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
#
# Or download and run locally:
#     bash install.sh
#
# Flags:
#     --no-modify-rc   Don't touch your shell rc; print the export
#                      lines and let you copy them yourself.
#     --backend=NAME   Skip the interactive prompt and pick NAME.
#                      One of: ollama, openrouter, claude.
#
# What it does, in order:
#   1. Check Python 3.10+ is on PATH.
#   2. Ask which AI backend you want (Ollama / OpenRouter / Claude).
#   3. For Ollama: install it, start it, pull qwen3:30b (~19 GB).
#      For OpenRouter / Claude: prompt for an API key (skippable).
#   4. Create a Python venv at ~/.dissyslab/venv.
#   5. pip install dissyslab into it.
#   6. Append PATH + DSL_BACKEND (+ key + model) to your shell rc
#      (~/.zshrc or ~/.bashrc, depending on $SHELL). A backup is
#      written next to the rc file before any edit. Pass
#      --no-modify-rc to skip.
#
# Tested on: macOS (Apple Silicon and Intel) and Ubuntu 22.04+.
# Probably works on other Linuxes; ymmv.
#

set -euo pipefail

# ── Parse flags ──────────────────────────────────────────────────────

MODIFY_RC=1
BACKEND_FLAG=""
for arg in "$@"; do
    case "$arg" in
        --no-modify-rc) MODIFY_RC=0 ;;
        --backend=*)    BACKEND_FLAG="${arg#--backend=}" ;;
        *) ;;
    esac
done

# ── Cosmetic helpers ─────────────────────────────────────────────────

bold()   { printf '\033[1m%s\033[0m\n'    "$*"; }
green()  { printf '\033[32m✓ %s\033[0m\n' "$*"; }
yellow() { printf '\033[33m! %s\033[0m\n' "$*"; }
red()    { printf '\033[31m✗ %s\033[0m\n' "$*"; }
header() { echo; bold "── $* ─────────────────────────"; }

die() {
    red "$*"
    echo
    echo "Installation aborted. Open an issue at"
    echo "  https://github.com/kmchandy/DisSysLab/issues"
    echo "with the message above and your OS details."
    exit 1
}

# Print a Pat-friendly explanation when Ollama can't be started on
# port 11434. The previous behaviour was a single-line "did not start"
# which left the user to guess between (a) didn't drag Ollama.app to
# /Applications, (b) macOS too old for the current Ollama, (c) port
# 11434 in use by something else, (d) headless server hung. This
# checks each of those in order and prints the most specific cause
# we can identify, plus a concrete next step.
#
# Triggers from the curl-to-11434 health check around step 4.
diagnose_ollama_failure() {
    red "Ollama service did not respond on port 11434."
    echo
    bold "── Diagnostics ──"

    # (a) CLI missing — almost certainly a failed/partial install.
    if ! command -v ollama >/dev/null 2>&1; then
        yellow "The 'ollama' command is not on your PATH."
        if [ "$PLATFORM" = "mac" ]; then
            echo "  Fix: install Ollama from https://ollama.com/download"
            echo "       — download Ollama.dmg, open it, drag Ollama.app"
            echo "       to Applications, then re-run this installer."
        else
            echo "  Fix: re-run the Ollama Linux installer:"
            bold  "         curl -fsSL https://ollama.com/install.sh | sh"
            echo "       then re-run this installer."
        fi
        echo
        echo "Or switch to a hosted backend (no download, ~pennies per run):"
        bold "       bash install.sh --backend=openrouter"
        exit 1
    fi

    # (b) Mac: Ollama.app missing even though the CLI exists.
    # Brew normally installs both; if the .app is missing, the user
    # likely installed just the CLI binary (or only downloaded the
    # dmg without dragging it).
    if [ "$PLATFORM" = "mac" ] && [ ! -d "/Applications/Ollama.app" ]; then
        yellow "/Applications/Ollama.app is missing."
        echo "  The 'ollama' CLI is on PATH, but the Mac app bundle is not"
        echo "  in /Applications. Recent Ollama versions need the .app"
        echo "  installed (it owns the launchd entry that serves port 11434)."
        echo
        echo "  Fix: download Ollama.dmg from https://ollama.com/download,"
        echo "       open it, and drag Ollama into the Applications folder."
        echo "       Then re-run this installer."
        echo
        echo "Or switch to a hosted backend:"
        bold "       bash install.sh --backend=openrouter"
        exit 1
    fi

    # (c) Mac: too-old macOS. Ollama drops support for older releases
    # quietly; the symptom on Pat's machine was "Unable to find
    # application name 'Ollama'" from launchctl/AppleScript when the
    # current Ollama refuses to launch on the older OS.
    if [ "$PLATFORM" = "mac" ]; then
        # `sw_vers -productVersion` returns e.g. "13.6.4" or "10.15.7".
        MACOS_VERSION="$(sw_vers -productVersion 2>/dev/null || echo unknown)"
        MACOS_MAJOR="${MACOS_VERSION%%.*}"
        # Ollama's current macOS minimum is 11.0 (Big Sur), with most
        # newer releases preferring 12+. Anything reporting "10.x" is
        # definitely too old; flag 11 too with a softer message.
        if [ "$MACOS_MAJOR" = "10" ] || \
           { [ "$MACOS_MAJOR" -lt 11 ] 2>/dev/null; }; then
            yellow "macOS $MACOS_VERSION is older than Ollama supports."
            echo "  Current Ollama needs macOS 11 (Big Sur) or newer."
            echo "  This explains errors like:"
            echo "     Unable to find application name 'Ollama'"
            echo "  Even though brew/curl succeeded, the OS won't launch the app."
            echo
            echo "  Options:"
            echo "    1. Upgrade macOS (System Settings → Software Update)."
            echo "    2. Try Ollama on a different / newer machine."
            echo "    3. Use a hosted backend on this machine — no install,"
            echo "       no download, ~pennies per run:"
            bold  "         bash install.sh --backend=openrouter"
            echo
            exit 1
        fi
    fi

    # (d) Port 11434 may be busy with a different process (e.g. an
    # older Ollama instance Pat forgot was running, or a Docker
    # container bound to that port).
    if command -v lsof >/dev/null 2>&1; then
        BUSY="$(lsof -nP -iTCP:11434 -sTCP:LISTEN 2>/dev/null | tail -n +2 | head -1 || true)"
        if [ -n "$BUSY" ]; then
            yellow "Port 11434 is in use by another process:"
            echo "  $BUSY"
            echo
            echo "  Fix: stop that process, or pick a different port for Ollama."
            echo "       Then re-run this installer."
            exit 1
        fi
    fi

    # (e) Fall-through: CLI is present, .app is present (or Linux),
    # macOS is recent, port is free — but the daemon still didn't come
    # up. Most likely cause is the daemon crashed during startup;
    # print the tail of its log so the user has something to file.
    yellow "ollama is installed but the daemon did not bind to port 11434."
    if [ -f /tmp/ollama.log ]; then
        echo
        echo "  Last lines of /tmp/ollama.log:"
        tail -10 /tmp/ollama.log | sed 's/^/    /'
        echo
    fi
    echo "  Fix: try running 'ollama serve' in another terminal and"
    echo "       watch what it prints. Then re-run this installer."
    echo "       If the error message mentions an Anthropic / OpenRouter"
    echo "       fallback, try:"
    bold  "         bash install.sh --backend=openrouter"
    exit 1
}

# Read one line from the user's keyboard.
#
# `curl | bash` redirects stdin to the curl pipe, so plain `read` would
# silently consume installer-script bytes. We always read from /dev/tty
# instead, which is the controlling terminal regardless of how the
# script was launched. If /dev/tty is unavailable (e.g. CI), we return
# the empty string and the caller falls back to a default.
prompt_user() {
    local prompt_text="$1"
    local default_value="${2:-}"
    local reply=""
    # `-r /dev/tty` is true even when /dev/tty exists but isn't actually
    # connected to a terminal (e.g. headless CI). The reliable test is
    # to try opening it for write and read inside an `if` block; if
    # either fails we silently fall back to the default. Suppress
    # stderr so the failing-open noise doesn't leak to the user.
    if { printf "%s " "$prompt_text" > /dev/tty; } 2>/dev/null; then
        if IFS= read -r reply < /dev/tty 2>/dev/null; then
            :
        else
            reply=""
        fi
    fi
    if [ -z "$reply" ]; then
        reply="$default_value"
    fi
    printf '%s' "$reply"
}

# ── 0. Banner ────────────────────────────────────────────────────────

bold "DisSysLab installer"
echo "Describe a continuous office of specialist agents in plain English."
echo "Sense → think → respond. Each agent uses the AI best suited to its job."
echo

# ── 1. Detect OS ─────────────────────────────────────────────────────

header "Step 1/6: Detect OS"

OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM="mac";   green "Detected macOS";;
    Linux)  PLATFORM="linux"; green "Detected Linux";;
    *)      die "Unsupported OS: $OS. We currently support macOS and Linux. Windows users: please install manually via the docs.";;
esac

# ── 2. Check Python 3.10+ ────────────────────────────────────────────

header "Step 2/6: Check Python 3.10+"

if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found. Install Python 3.10 or newer from https://www.python.org/downloads/ then re-run this installer."
fi

PYV="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYMAJ="${PYV%%.*}"
PYMIN="${PYV##*.}"
if [ "$PYMAJ" -lt 3 ] || { [ "$PYMAJ" -eq 3 ] && [ "$PYMIN" -lt 10 ]; }; then
    die "Found Python $PYV but DisSysLab needs Python 3.10+. Upgrade Python from https://www.python.org/downloads/ then re-run."
fi
green "Python $PYV is fine"

# ── 3. Choose backend ────────────────────────────────────────────────

header "Step 3/6: Choose an AI backend"

BACKEND=""
API_KEY=""

# Default model identifiers for each hosted option. Kept in lockstep
# with dissyslab.backends.openrouter_backend.DEFAULT_MODEL and
# dissyslab.backends.anthropic_backend.DEFAULT_MODEL so the rc-file
# export agrees with the library's hardcoded fallback.
OPENROUTER_DEFAULT_MODEL="qwen/qwen-2.5-7b-instruct"

if [ -n "$BACKEND_FLAG" ]; then
    BACKEND="$BACKEND_FLAG"
    green "Backend selected via --backend=$BACKEND"
else
    echo "DisSysLab can use three different AI engines. Pick one — you can"
    echo "change later by editing your shell rc file."
    echo
    bold  "  1) Ollama (free, local, slow)"
    echo  "     Runs entirely on your laptop. Downloads ~19 GB of model"
    echo  "     weights one time. A typical office takes 15–60 min per run."
    echo  "     No API key required."
    echo
    bold  "  2) OpenRouter (a few cents per run, fast, requires key)"
    echo  "     Uses Qwen-2.5-7B hosted on OpenRouter. Office runs typically"
    echo  "     finish in 1–5 minutes. Costs pennies per run. You'll need"
    echo  "     to create an API key at https://openrouter.ai/keys."
    echo
    bold  "  3) Claude (more expensive, fastest, requires key)"
    echo  "     Uses Anthropic's Claude. Highest-quality output, ~25–50¢ per"
    echo  "     office run. You'll need a key from https://console.anthropic.com."
    echo
    while [ -z "$BACKEND" ]; do
        CHOICE="$(prompt_user 'Enter 1, 2, or 3 [default: 1]:' '1')"
        case "$CHOICE" in
            1|ollama)     BACKEND="ollama" ;;
            2|openrouter) BACKEND="openrouter" ;;
            3|claude|anthropic) BACKEND="claude" ;;
            *)
                yellow "Please enter 1, 2, or 3."
                ;;
        esac
    done
    green "Backend: $BACKEND"
fi

# For the hosted backends, offer to capture an API key now. We let
# Pat skip — sometimes she hasn't signed up yet and wants to come back
# later. In that case we still write DSL_BACKEND so the framework
# fails with a useful "key missing" message instead of silently
# falling back to Ollama.
if [ "$BACKEND" = "openrouter" ]; then
    echo
    echo "OpenRouter API key (starts with 'sk-or-v1-')."
    echo "Leave blank to skip — you can export it later with:"
    bold  "       export OPENROUTER_API_KEY='sk-or-v1-...'"
    API_KEY="$(prompt_user 'Paste your OpenRouter key (or press Enter to skip):' '')"
    if [ -n "$API_KEY" ]; then
        green "OpenRouter key captured"
    else
        yellow "No key entered — DSL_BACKEND will be set, but you must export OPENROUTER_API_KEY before running any office."
    fi
elif [ "$BACKEND" = "claude" ]; then
    echo
    echo "Anthropic API key (starts with 'sk-ant-')."
    echo "Leave blank to skip — you can export it later with:"
    bold  "       export ANTHROPIC_API_KEY='sk-ant-...'"
    API_KEY="$(prompt_user 'Paste your Anthropic key (or press Enter to skip):' '')"
    if [ -n "$API_KEY" ]; then
        green "Anthropic key captured"
    else
        yellow "No key entered — DSL_BACKEND will be set, but you must export ANTHROPIC_API_KEY before running any office."
    fi
fi

# ── 4. Backend-specific install ──────────────────────────────────────

header "Step 4/6: Install backend dependencies"

if [ "$BACKEND" = "ollama" ]; then
    # Ollama install
    if command -v ollama >/dev/null 2>&1; then
        green "Ollama is already installed"
    else
        if [ "$PLATFORM" = "mac" ]; then
            if ! command -v brew >/dev/null 2>&1; then
                die "Homebrew is not installed. The simplest install path on Mac is:
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"
Run that, then re-run this installer. (Or install Ollama manually from https://ollama.com/download.)"
            fi
            bold "Installing Ollama via homebrew..."
            brew install ollama
        else
            bold "Installing Ollama via the official Linux installer..."
            curl -fsSL https://ollama.com/install.sh | sh
        fi
        green "Ollama installed"
    fi

    # Start service
    if ! curl -sSf -o /dev/null http://127.0.0.1:11434/api/version 2>/dev/null; then
        yellow "Ollama service is not running. Starting it..."
        if [ "$PLATFORM" = "mac" ]; then
            ollama serve >/tmp/ollama.log 2>&1 &
            sleep 2
        else
            if command -v systemctl >/dev/null 2>&1; then
                sudo systemctl start ollama || true
                sleep 2
            else
                ollama serve >/tmp/ollama.log 2>&1 &
                sleep 2
            fi
        fi
    fi

    if curl -sSf -o /dev/null http://127.0.0.1:11434/api/version 2>/dev/null; then
        green "Ollama is responding on port 11434"
    else
        diagnose_ollama_failure
    fi

    # Pull the model
    if ollama list 2>/dev/null | grep -q '^qwen3:30b'; then
        green "qwen3:30b is already downloaded"
    else
        yellow "Downloading qwen3:30b — about 19 GB, takes 20–40 minutes on a typical home connection."
        yellow "This is a one-time cost. Pat gets free AI forever after this."
        echo
        ollama pull qwen3:30b
        green "qwen3:30b downloaded"
    fi
else
    green "Skipping Ollama install — using $BACKEND. No ~19 GB download."
    echo
    echo "(If you later want to add a free local fallback, install Ollama"
    echo "from https://ollama.com/download and run 'ollama pull qwen3:30b'.)"
fi

# ── 5. Install DisSysLab ─────────────────────────────────────────────

header "Step 5/6: Install DisSysLab into a venv"

DSL_HOME="${DSL_HOME:-$HOME/.dissyslab}"
mkdir -p "$DSL_HOME"

if [ ! -d "$DSL_HOME/venv" ]; then
    python3 -m venv "$DSL_HOME/venv"
fi

"$DSL_HOME/venv/bin/pip" install --upgrade pip >/dev/null
"$DSL_HOME/venv/bin/pip" install --upgrade dissyslab

green "DisSysLab installed at $DSL_HOME/venv"

# Sanity-check: does the installed dissyslab actually recognise the
# backend name we're about to write into the shell rc? When the user
# picks an option that's been recently renamed/aliased (e.g. "claude"
# before the v1.4 alias landed in PyPI), the install banner can say
# "Backend: claude" while the installed wheel will throw
# `Unknown backend: 'claude'` the first time Pat runs an office. This
# warns at install time so the gap is visible *here*, not 90 seconds
# later when Pat thinks she did something wrong.
#
# We only warn — never abort — because the user may know they're
# ahead of PyPI (e.g. testing a backend that's in main but not yet
# released).
if ! "$DSL_HOME/venv/bin/python" -c \
    "import sys; from dissyslab.backends import get_backend; sys.exit(0 if get_backend('$BACKEND') else 1)" \
    >/dev/null 2>&1; then
    echo
    yellow "Heads-up: the installed dissyslab version does not yet recognise"
    yellow "DSL_BACKEND=$BACKEND. The shell-rc export will still be written,"
    yellow "but the first 'dsl run' will fail with:"
    yellow "    Unknown backend: '$BACKEND'"
    yellow ""
    yellow "Either wait for a newer dissyslab release on PyPI, or pick a"
    yellow "different backend with:"
    bold   "       bash install.sh --backend=openrouter"
    echo
fi

# ── 6. Update shell config ──────────────────────────────────────────

header "Step 6/6: Update your shell config"

# Detect the right rc file from $SHELL. Mac users mostly run zsh
# (Apple's default since macOS 10.15); Linux users mostly run bash.
# We deliberately do NOT fall through to .profile or .bash_profile
# without confirmation — those interact with login-shell semantics
# in ways that are easy to break.
RC_FILE=""
case "${SHELL:-}" in
    */zsh)  RC_FILE="$HOME/.zshrc" ;;
    */bash)
        if [ "$PLATFORM" = "mac" ] && [ -f "$HOME/.bash_profile" ]; then
            RC_FILE="$HOME/.bash_profile"
        else
            RC_FILE="$HOME/.bashrc"
        fi
        ;;
    */fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
    *) RC_FILE="" ;;
esac

# Marker the installer uses to recognise its own block on re-runs.
MARKER="# Added by DisSysLab installer"

# Build the list of export lines we want to append, depending on the
# backend the user chose. The list is rendered identically for the
# manual-instructions path and for the rc-file-append path so Pat
# sees the same lines in both cases.
build_export_lines_bash() {
    echo "export PATH=\"$DSL_HOME/venv/bin:\$PATH\""
    echo "export DSL_BACKEND=$BACKEND"
    case "$BACKEND" in
        ollama)
            # The daemon picks up OLLAMA_NUM_PARALLEL at start time,
            # not from arbitrary client shells. The final banner
            # tells the user how to restart the daemon.
            echo "export OLLAMA_NUM_PARALLEL=4"
            ;;
        openrouter)
            echo "export OPENROUTER_MODEL=$OPENROUTER_DEFAULT_MODEL"
            if [ -n "$API_KEY" ]; then
                echo "export OPENROUTER_API_KEY='$API_KEY'"
            fi
            ;;
        claude)
            if [ -n "$API_KEY" ]; then
                echo "export ANTHROPIC_API_KEY='$API_KEY'"
            fi
            ;;
    esac
}

build_export_lines_fish() {
    echo "set -gx PATH $DSL_HOME/venv/bin \$PATH"
    echo "set -gx DSL_BACKEND $BACKEND"
    case "$BACKEND" in
        ollama)
            echo "set -gx OLLAMA_NUM_PARALLEL 4"
            ;;
        openrouter)
            echo "set -gx OPENROUTER_MODEL $OPENROUTER_DEFAULT_MODEL"
            if [ -n "$API_KEY" ]; then
                echo "set -gx OPENROUTER_API_KEY '$API_KEY'"
            fi
            ;;
        claude)
            if [ -n "$API_KEY" ]; then
                echo "set -gx ANTHROPIC_API_KEY '$API_KEY'"
            fi
            ;;
    esac
}

print_manual_instructions() {
    echo
    yellow "Add these lines to your shell config and restart your terminal:"
    echo
    if [ "${RC_FILE##*/}" = "config.fish" ]; then
        build_export_lines_fish | while IFS= read -r line; do
            bold "       $line"
        done
    else
        build_export_lines_bash | while IFS= read -r line; do
            bold "       $line"
        done
    fi
    echo
}

if [ "$MODIFY_RC" -eq 0 ]; then
    yellow "Skipping shell config update (--no-modify-rc)."
    print_manual_instructions
elif [ -z "$RC_FILE" ]; then
    yellow "Couldn't detect your shell from \$SHELL=${SHELL:-(unset)}."
    print_manual_instructions
elif [ -f "$RC_FILE" ] && grep -qF "$MARKER" "$RC_FILE"; then
    yellow "Shell config already has a DisSysLab block — leaving it alone ($RC_FILE)."
    echo
    echo "If you want to switch backend, edit $RC_FILE manually or remove"
    echo "the DisSysLab block and re-run this installer."
elif [ "${RC_FILE##*/}" = "config.fish" ]; then
    if [ -f "$RC_FILE" ]; then
        cp "$RC_FILE" "$RC_FILE.dissyslab-backup"
        yellow "Backed up $RC_FILE to $RC_FILE.dissyslab-backup"
    fi
    {
        echo ""
        echo "$MARKER"
        build_export_lines_fish
    } >> "$RC_FILE"
    green "Appended DisSysLab block to $RC_FILE"
else
    if [ -f "$RC_FILE" ]; then
        cp "$RC_FILE" "$RC_FILE.dissyslab-backup"
        yellow "Backed up $RC_FILE to $RC_FILE.dissyslab-backup"
    fi
    {
        echo ""
        echo "$MARKER"
        build_export_lines_bash
    } >> "$RC_FILE"
    green "Appended DisSysLab block to $RC_FILE"
fi

# ── Done ─────────────────────────────────────────────────────────────

header "All set"

# A tiny banner emphasising the one step Pat is most likely to miss.
# The PATH change in ~/.zshrc does NOT apply to the terminal that
# just ran install.sh — only to terminals opened (or re-sourced)
# afterwards. Pat tends to try `dsl run` immediately and bounce on
# "command not found", so we shout this step.

if [ "$MODIFY_RC" -eq 1 ] && [ -n "${RC_FILE:-}" ] && \
   [ -f "$RC_FILE" ] && grep -qF "$MARKER" "$RC_FILE"; then
    echo
    yellow "──────────────────────────────────────────────────────────────"
    yellow "  ONE MORE STEP — pick either (A) or (B):"
    yellow ""
    yellow "  (A) Run this in THIS terminal:"
    bold   "        source $RC_FILE"
    yellow ""
    yellow "  (B) Or close this terminal and open a brand new one."
    yellow ""
    yellow "  Why: install.sh added PATH to $RC_FILE, but this"
    yellow "  terminal won't see it until you do (A) or (B)."
    yellow "──────────────────────────────────────────────────────────────"
    echo
fi

echo "Then try your first office:"
echo
if [ "$BACKEND" = "ollama" ]; then
    bold "       dsl run periodic_brief         # fast, no LLM calls, ~10 s"
    bold "       dsl run situation_room         # the headline, ~15–30 min on local Qwen"
else
    bold "       dsl run periodic_brief         # fast, no LLM calls, ~10 s"
    bold "       dsl run situation_room         # the headline, ~1–5 min on $BACKEND"
fi
echo
echo "Read the framework tour to see what an office is and how to make one your own:"
bold "       https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/apps/situation_room/README.md"
echo

if [ "$BACKEND" = "ollama" ] && [ "$MODIFY_RC" -eq 1 ] && [ "$PLATFORM" = "mac" ] && command -v brew >/dev/null 2>&1; then
    echo "Tip: to make OLLAMA_NUM_PARALLEL=4 reach the Ollama daemon, restart it:"
    bold "       brew services restart ollama"
    echo "If situation_room feels slow even after that, the bottleneck is your"
    echo "laptop's local inference speed. Re-run this installer and pick (2)"
    echo "OpenRouter for a much faster — and still cheap — path."
    echo
elif [ "$BACKEND" = "ollama" ] && [ "$MODIFY_RC" -eq 1 ] && [ "$PLATFORM" = "linux" ]; then
    echo "Tip: to make OLLAMA_NUM_PARALLEL=4 reach the Ollama daemon:"
    bold "       sudo systemctl restart ollama   # if Ollama runs under systemd"
    echo
fi

if [ "$BACKEND" != "ollama" ] && [ -z "$API_KEY" ]; then
    echo
    yellow "Reminder: you didn't paste an API key. Before you run an office,"
    if [ "$BACKEND" = "openrouter" ]; then
        yellow "export OPENROUTER_API_KEY in this terminal (or add it to $RC_FILE)."
    else
        yellow "export ANTHROPIC_API_KEY in this terminal (or add it to $RC_FILE)."
    fi
    echo
fi

echo "Welcome to DisSysLab — plain-English AI offices, your engine choice."
echo
